import numpy as np
import pandas as pd
from .constants import (
    EFFICIENCY, NET_HOUSEHOLD, CHARGE, CHARGE_FROM_HOUSE, CHARGE_FROM_GRID,
    DISCHARGE, DISCHARGE_TO_HOUSE, DISCHARGE_TO_GRID,
    SOC, COST_WO_BATTERY, COST_WITH_BATTERY, NET_BUY_PRICE, NET_SELL_PRICE, TIME,
    CUMULATIVE_SAVINGS, SAVINGS, SAVINGS_PER_DAY, NET_HOUSEHOLD_WITH_BATTERY
)

def run_battery_simulation(sim_df, capacity_kwh, rate_kw, strategy_fn):
    sim_df = sim_df.copy()  # To avoid adding columns to the original DataFrame, for every strategy, rate and capacity

    current_soc = capacity_kwh/2  # Just to enable sanity-checking/debugging during the first TIME steps of the simulation
    total_savings = 0.0
    
    simulation_logs = []

    for i in range(len(sim_df)):
        # Add a waitbar that fills up every n steps. It replaces previous print everytime:
        n = 100
        if i % n == 0:
            print(f"\rSimulation progress: {i}/{len(sim_df)}", end='', flush=True)

        now, future_df = get_now_and_known_future(i, sim_df)

        ch_h, ch_g, dis_h, dis_g = strategy_fn(
            row=now,
            future_df=future_df,
            current_soc=current_soc,
            capacity_kwh=capacity_kwh,
            max_rate_kw=rate_kw,
        )

        # Enforce physical limits and battery constraints
        # 1. Total (dis)charge cannot exceed max rate or battery limits
        charge_kwh = max(0, min(ch_h + ch_g, rate_kw, capacity_kwh - current_soc))
        
        # Split back to house/grid proportionally if we had to cap it
        total_requested_charge = ch_h + ch_g
        if total_requested_charge > 1e-6:
            ratio = charge_kwh / total_requested_charge
            ch_h *= ratio
            ch_g *= ratio
        else:
            ch_h, ch_g = 0.0, 0.0

        current_soc += charge_kwh * EFFICIENCY

        discharge_kwh = max(0, min(dis_h + dis_g, rate_kw, current_soc * EFFICIENCY))
        
        total_requested_discharge = dis_h + dis_g
        if total_requested_discharge > 1e-6:
            ratio = discharge_kwh / total_requested_discharge
            dis_h *= ratio
            dis_g *= ratio
        else:
            dis_h, dis_g = 0.0, 0.0

        current_soc -= discharge_kwh / EFFICIENCY

        # Cost without battery: net buy * buy_price (if positive) or net sell * sell_price (if negative)
        price_this_hour = now[NET_BUY_PRICE] if now[NET_HOUSEHOLD] > 0 else now[NET_SELL_PRICE]
        cost_no_batt = now[NET_HOUSEHOLD] * price_this_hour

        # Cost with battery: (net_kwh + charge - discharge) * relevant_price
        new_net_kwh = now[NET_HOUSEHOLD] + charge_kwh - discharge_kwh
        price_this_hour = now[NET_BUY_PRICE] if new_net_kwh > 0 else now[NET_SELL_PRICE]
        cost_with_batt = new_net_kwh * price_this_hour

        total_savings += cost_no_batt - cost_with_batt

        simulation_logs.append({
            TIME: now[TIME],
            SOC: current_soc,
            CHARGE: charge_kwh,
            CHARGE_FROM_HOUSE: ch_h,
            CHARGE_FROM_GRID: ch_g,
            DISCHARGE: discharge_kwh,
            DISCHARGE_TO_HOUSE: dis_h,
            DISCHARGE_TO_GRID: dis_g,
            NET_HOUSEHOLD_WITH_BATTERY: new_net_kwh,
            COST_WO_BATTERY: cost_no_batt,
            COST_WITH_BATTERY: cost_with_batt
        })

    df_logs = pd.DataFrame(simulation_logs)
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
