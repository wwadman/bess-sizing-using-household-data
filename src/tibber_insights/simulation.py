import pandas as pd
from .constants import (
    NET_HOUSEHOLD, CHARGE_FROM_HOUSE, CHARGE_FROM_GRID,
    DISCHARGE_TO_HOUSE, DISCHARGE_TO_GRID,
    SOC, COST_WO_BATTERY, COST_WITH_BATTERY, NET_BUY_PRICE, NET_SELL_PRICE, TIME,
    SAVINGS, SAVINGS_PER_DAY, NET_HOUSEHOLD_WITH_BATTERY, EFFICIENCY_CHARGING,
    EFFICIENCY_DISCHARGING, CONSUMPTION, PRODUCTION
)

def run_battery_simulation(sim_df, capacity_kwh, max_rate_kw, strategy_fn):
    sim_df = sim_df.copy()  # To avoid adding columns to the original DataFrame, for every strategy, rate and capacity

    current_soc = capacity_kwh/2  # Just to enable sanity-checking/debugging during the first TIME steps of the simulation

    simulation_logs = []

    # Find all indices where the hour is 14:00
    # Use reset_index to ensure we have a continuous range of integer indices if sim_df doesn't
    sim_df_indexed = sim_df.reset_index(drop=True)
    indices_14h = sim_df_indexed.index[sim_df_indexed[TIME].dt.hour == 14].tolist()
    
    for i in indices_14h:
        # Add a waitbar that fills up every n steps.
        print(f"\rSimulation progress: {i}/{len(sim_df_indexed)}", end='', flush=True)

        now, future_df = get_now_and_known_future(i, sim_df_indexed)

        # strategy_daily_lp now returns a DataFrame containing the plan
        plan_df = strategy_fn(
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
            
            # Check if plan has enough steps
            if t >= len(plan_df):
                break
            
            ch_h = plan_df.iloc[t][CHARGE_FROM_HOUSE]
            ch_g = plan_df.iloc[t][CHARGE_FROM_GRID]
            dis_h = plan_df.iloc[t][DISCHARGE_TO_HOUSE]
            dis_g = plan_df.iloc[t][DISCHARGE_TO_GRID]

            # Check all physical limits and battery constraints
            charge = ch_h + ch_g
            soc_charge_bump = charge * EFFICIENCY_CHARGING
            discharge = dis_h + dis_g
            soc_discharge_dip = discharge / EFFICIENCY_DISCHARGING

            # 1. Total (dis)charge cannot exceed the max rate
            eps = 1e-4  # some margin to counter numerical errors
            assert -eps <= soc_charge_bump <= max_rate_kw + eps, \
                f"Total charge {soc_charge_bump} should be between 0 and max rate {max_rate_kw}"
            assert -eps <= soc_discharge_dip <= max_rate_kw + eps, \
                f"Total discharge {soc_discharge_dip} should be between 0 and max rate {max_rate_kw}"

            # Update SOC for next time step and check if SOC is within limits
            current_soc = current_soc + soc_charge_bump - soc_discharge_dip
            assert -eps <= current_soc <= capacity_kwh + eps, \
                f"Current SOC {current_soc} should be within [0, {capacity_kwh}]."

            cost_wo_batt = row_now[CONSUMPTION] * row_now[NET_BUY_PRICE] - row_now[PRODUCTION] * row_now[NET_SELL_PRICE]

            new_net_kwh = row_now[NET_HOUSEHOLD] + charge - discharge
            battery_savings = (dis_h - ch_g) * row_now[NET_BUY_PRICE] + (dis_g - ch_h) * row_now[NET_SELL_PRICE]
            cost_with_batt = cost_wo_batt - battery_savings

            simulation_logs.append({
                TIME: row_now[TIME],
                SOC: current_soc,
                CHARGE_FROM_HOUSE: ch_h,
                CHARGE_FROM_GRID: ch_g,
                DISCHARGE_TO_HOUSE: dis_h,
                DISCHARGE_TO_GRID: dis_g,
                NET_HOUSEHOLD_WITH_BATTERY: new_net_kwh,
                COST_WO_BATTERY: cost_wo_batt,
                COST_WITH_BATTERY: cost_with_batt
            })

    df_logs = pd.DataFrame(simulation_logs)
    df_logs = df_logs.drop_duplicates(subset=[TIME], keep='first') # If 24h blocks overlap (they shouldn't if we step correctly, but just in case)
    df_logs[SAVINGS] = df_logs[COST_WO_BATTERY] - df_logs[COST_WITH_BATTERY]
    df_logs[SAVINGS_PER_DAY] = df_logs.groupby(df_logs[TIME].dt.date)[SAVINGS].transform('sum')
    sim_df = sim_df.merge(df_logs, on=TIME, how="left", suffixes=("", "_logged"))
    return sim_df


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
