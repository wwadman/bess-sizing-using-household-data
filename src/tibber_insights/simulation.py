import numpy as np
import pandas as pd
from .constants import (
    EFFICIENCY, net_household, charge, discharge,
    soc, cost_wo_battery, cost_with_battery, net_buy_price, net_sell_price, time,
    cumulative_savings, savings, savings_per_day
)

def run_battery_simulation(sim_df, capacity_kwh, rate_kw, strategy_fn):
    sim_df = sim_df.copy()  # To avoid adding columns to the original DataFrame, for every strategy, rate and capacity

    current_soc = 0
    total_savings = 0.0
    
    simulation_logs = []

    for i in range(len(sim_df)):
        now, future_df = get_now_and_known_future(i, sim_df)

        charge_kwh, discharge_kwh = strategy_fn(
            row=now,
            future_df=future_df,
            current_soc=current_soc,
            capacity_kwh=capacity_kwh,
            max_rate_kw=rate_kw,
        )

        charge_kwh = max(0, min(charge_kwh, rate_kw, capacity_kwh - current_soc))
        current_soc += charge_kwh * EFFICIENCY

        discharge_kwh = max(0, min(discharge_kwh, rate_kw, current_soc * EFFICIENCY))
        current_soc -= discharge_kwh / EFFICIENCY

        # Cost without battery: net buy * buy_price (if positive) or net sell * sell_price (if negative)
        price_this_hour = now[net_buy_price] if now[net_household] > 0 else now[net_sell_price]
        cost_no_batt = now[net_household] * price_this_hour

        # Cost with battery: (net_kwh + charge - discharge) * relevant_price
        new_net_kwh = now[net_household] + charge_kwh - discharge_kwh
        price_this_hour = now[net_buy_price] if new_net_kwh > 0 else now[net_sell_price]
        cost_with_batt = new_net_kwh * price_this_hour

        total_savings += cost_no_batt - cost_with_batt

        simulation_logs.append({
            time: now[time],
            soc: current_soc,
            charge: charge_kwh,
            discharge: discharge_kwh,
            cost_wo_battery: cost_no_batt,
            cost_with_battery: cost_with_batt
        })

    df_logs = pd.DataFrame(simulation_logs)
    df_logs[savings] = df_logs[cost_wo_battery] - df_logs[cost_with_battery]
    df_logs[savings_per_day] = df_logs.groupby(df_logs[time].dt.date)[savings].transform('sum')
    df_logs[cumulative_savings] = np.cumsum(df_logs[savings])
    sim_df = sim_df.merge(df_logs, on=time, how="left", suffixes=("", "_logged"))
    return total_savings, sim_df


def get_now_and_known_future(i, sim_df):
    now = sim_df.iloc[i]  # now denotes current hour in the simulation

    # Dynamic horizon: rest of today + (if past 1pm) tomorrow
    current_hour = now[time].hour
    hours_until_midnight = 24 - current_hour
    horizon = hours_until_midnight
    if current_hour >= 13:
        horizon += 24
    future_df = sim_df.iloc[i:i + horizon]
    return now, future_df
