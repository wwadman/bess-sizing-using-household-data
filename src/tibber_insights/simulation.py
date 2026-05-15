import numpy as np
import pandas as pd
from .constants import (
    EFFICIENCY, net_household, charge, discharge,
    soc, cost_wo_battery, cost_with_battery, net_buy_price, net_sell_price, time,
    production, cumulative_savings
)

def run_battery_simulation(sim_df, capacity_kwh, rate_kw, strategy_fn):
    sim_df = sim_df.copy()  # To avoid adding columns to the original DataFrame, for every strategy, rate and capacity

    current_soc = 0.0
    total_savings = 0.0
    
    simulation_logs = []

    for i in range(len(sim_df)):
        now, future_df = get_now_and_known_future(i, sim_df)

        charge_kwh, discharge_kwh = strategy_fn(
            row=now,
            future_df=future_df,
            soc=current_soc,
            capacity_kwh=capacity_kwh,
            rate_kw=rate_kw,
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
    df_logs[cumulative_savings] = np.cumsum(df_logs[cost_wo_battery] - df_logs[cost_with_battery])
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


def strategy_arbitrage(row, future_df, soc, capacity_kwh, rate_kw):
    actual_solar = row[production] if pd.notna(row[production]) else 0.0
    charge_kwh = min(actual_solar, rate_kw)

    # Calculate effective prices including taxes and VAT
    if row[net_buy_price] <= future_df[net_buy_price].quantile(0.25):
        charge_kwh = rate_kw

    discharge_kwh = 0.0
    if soc > 0 and row[net_buy_price] >= future_df[net_buy_price].quantile(0.75):
        discharge_kwh = rate_kw

    return charge_kwh, discharge_kwh


def strategy_optimal_mpc(row, future_df, soc, capacity_kwh, rate_kw,
                         horizon_hours=24, eta=0.90):
    future_df = future_df.iloc[:horizon_hours]
    n = len(future_df)
    
    # Calculate effective buy and sell prices including taxes and VAT
    buy = future_df[net_buy_price].values
    sell = future_df[net_sell_price].values

    plan_c = np.zeros(n)
    plan_d = np.zeros(n)

    remaining_soc = soc
    for h in np.argsort(sell)[::-1]:
        if remaining_soc <= 0:
            break
        d = min(rate_kw, remaining_soc * eta)
        plan_d[h] += d
        remaining_soc -= d / eta

    c_avail = rate_kw - plan_c
    d_avail = rate_kw - plan_d
    space = capacity_kwh - soc

    c_order = np.argsort(buy)
    d_order = np.argsort(sell)[::-1]

    for h_dis in d_order:
        for h_ch in c_order:
            if h_ch >= h_dis:
                continue
            if eta * sell[h_dis] - buy[h_ch] <= 0:
                break
            x = min(c_avail[h_ch], d_avail[h_dis] / eta, space)
            if x <= 0:
                continue
            plan_c[h_ch] += x
            plan_d[h_dis] += x * eta
            c_avail[h_ch] -= x
            d_avail[h_dis] -= x * eta
            space -= x
        if space <= 0:
            break

    return float(plan_c[0]), float(plan_d[0])

#
# def strategy_greedy(row, future_df, soc, capacity_kwh, rate_kw):
#     price = row[consumption_unit_price_eur]
#     day_prices = future_df[consumption_unit_price_eur]
#
#     low_threshold = day_prices.quantile(0.2)
#     high_threshold = day_prices.quantile(0.8)
#
#     if price <= low_threshold:
#         charge_kwh = rate_kw
#         discharge_kwh = 0
#     elif price >= high_threshold:
#         charge_kwh = 0
#         discharge_kwh = soc
#     else:
#         charge_kwh = 0
#         discharge_kwh = 0
#
#     return charge_kwh, discharge_kwh
#
#
# def strategy_solar_plus_low_price(row, future_df, soc, capacity_kwh, rate_kw):
#     charge_kwh = row[production] if pd.notna(row[production]) else 0.0
#
#     if row[consumption_unit_price_eur] < 0.05:
#         charge_kwh = rate_kw
#
#     future_price = future_df[consumption_unit_price_eur].max()
#     discharge_kwh = soc if future_price > 0.25 else 0
#
#     return charge_kwh, discharge_kwh