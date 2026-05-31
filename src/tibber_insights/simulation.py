import numpy as np
import pandas as pd
from .constants import (
    NET_HOUSEHOLD, CHARGE, CHARGE_FROM_HOUSE, CHARGE_FROM_GRID,
    DISCHARGE, DISCHARGE_TO_HOUSE, DISCHARGE_TO_GRID,
    SOC, COST_WO_BATTERY, COST_WITH_BATTERY, NET_BUY_PRICE, NET_SELL_PRICE, TIME,
    CUMULATIVE_SAVINGS, SAVINGS, SAVINGS_PER_DAY, NET_HOUSEHOLD_WITH_BATTERY, EFFICIENCY_CHARGING,
    EFFICIENCY_DISCHARGING
)

def run_battery_simulation(sim_df, capacity_kwh, max_rate_kw, strategy_fn):
    sim_df = sim_df.copy()  # To avoid adding columns to the original DataFrame, for every strategy, rate and capacity

    current_soc = capacity_kwh/2  # Just to enable sanity-checking/debugging during the first TIME steps of the simulation
    total_savings = 0.0
    
    simulation_logs = []

    # Find all indices where the hour is 14:00
    # Use reset_index to ensure we have a continuous range of integer indices if sim_df doesn't
    sim_df_indexed = sim_df.reset_index(drop=True)
    indices_14h = sim_df_indexed.index[sim_df_indexed[TIME].dt.hour == 14].tolist()
    
    for i in indices_14h:
        # Add a waitbar that fills up every n steps.
        print(f"\rSimulation progress: {i}/{len(sim_df_indexed)}", end='', flush=True)

        now, future_df = get_now_and_known_future(i, sim_df_indexed)

        # strategy_daily_lp now returns a dict of 24h plans
        plan = strategy_fn(
            row=now,
            future_df=future_df,
            current_soc=current_soc,
            capacity_kwh=capacity_kwh,
            max_rate_kw=max_rate_kw,
        )

        # Execute 24 hours (or less if at the end of sim_df_indexed)
        steps_to_execute = min(24, len(sim_df_indexed) - i)
        
        for t in range(steps_to_execute):
            idx = i + t
            row_now = sim_df_indexed.iloc[idx]
            
            # Check if plan has enough steps (it should if future_df was large enough)
            if t >= len(plan['ch_h']):
                break
            
            ch_h = plan['ch_h'][t]
            ch_g = plan['ch_g'][t]
            dis_h = plan['dis_h'][t]
            dis_g = plan['dis_g'][t]

            # Check all physical limits and battery constraints
            charge = ch_h + ch_g
            soc_charge_bump = charge * EFFICIENCY_CHARGING
            discharge = dis_h + dis_g
            soc_discharge_dip = discharge / EFFICIENCY_DISCHARGING
            
            # 1. Total (dis)charge cannot exceed the max rate
            assert 0 <= charge <= max_rate_kw + 1e-6, f"Total charge {charge} should be between 0 and max rate {max_rate_kw}"
            assert 0 <= discharge <= max_rate_kw + 1e-6, f"Total discharge {discharge} should be between 0 and max rate {max_rate_kw}"

            # Update SOC for next time step and check if SOC is within limits
            current_soc = round(current_soc + soc_charge_bump - soc_discharge_dip, 6)
            
            # Numerical safety
            if current_soc < 0 and current_soc > -1e-4:
                current_soc = 0.0
            if current_soc > capacity_kwh and current_soc < capacity_kwh + 1e-4:
                current_soc = float(capacity_kwh)
            
            current_soc = round(current_soc, 3)
            assert 0 <= current_soc <= capacity_kwh, f"Current SOC {current_soc} should be between 0 and battery capacity {capacity_kwh}"

            # Cost without battery: net buy * buy_price (if positive) or net sell * sell_price (if negative)
            price_this_hour = row_now[NET_BUY_PRICE] if row_now[NET_HOUSEHOLD] > 0 else row_now[NET_SELL_PRICE]
            cost_no_batt = row_now[NET_HOUSEHOLD] * price_this_hour

            # Cost with battery: (net_kwh + charge - discharge) * relevant_price
            new_net_kwh = row_now[NET_HOUSEHOLD] + charge - discharge
            price_this_hour = row_now[NET_BUY_PRICE] if new_net_kwh > 0 else row_now[NET_SELL_PRICE]
            cost_with_batt = new_net_kwh * price_this_hour

            total_savings += cost_no_batt - cost_with_batt

            simulation_logs.append({
                TIME: row_now[TIME],
                SOC: current_soc,
                CHARGE: charge,
                CHARGE_FROM_HOUSE: ch_h,
                CHARGE_FROM_GRID: ch_g,
                DISCHARGE: discharge,
                DISCHARGE_TO_HOUSE: dis_h,
                DISCHARGE_TO_GRID: dis_g,
                NET_HOUSEHOLD_WITH_BATTERY: new_net_kwh,
                COST_WO_BATTERY: cost_no_batt,
                COST_WITH_BATTERY: cost_with_batt
            })

    df_logs = pd.DataFrame(simulation_logs)
    df_logs = df_logs.drop_duplicates(subset=[TIME], keep='first') # If 24h blocks overlap (they shouldn't if we step correctly, but just in case)
    df_logs[SAVINGS] = df_logs[COST_WO_BATTERY] - df_logs[COST_WITH_BATTERY]
    df_logs[SAVINGS_PER_DAY] = df_logs.groupby(df_logs[TIME].dt.date)[SAVINGS].transform('sum')
    df_logs[CUMULATIVE_SAVINGS] = np.cumsum(df_logs[SAVINGS])
    sim_df = sim_df.merge(df_logs, on=TIME, how="left", suffixes=("", "_logged"))
    return total_savings, sim_df


def get_now_and_known_future(i, sim_df):
    now = sim_df.iloc[i]  # now denotes current hour in the simulation

    # Dynamic horizon: rest of today + (if past 1pm) tomorrow
    current_hour = now[TIME].hour
    hours_until_midnight = 24 - current_hour
    horizon = hours_until_midnight
    if current_hour >= 13:
        horizon += 24
    future_df = sim_df.iloc[i:i + horizon]
    return now, future_df
