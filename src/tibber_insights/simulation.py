import numpy as np
import pandas as pd
from .constants import (
    EFFICIENCY, net_household, battery_charge, battery_discharge,
    soc, cost_no_battery, cost_with_battery, net_buy_price, net_sell_price
)

def run_battery_simulation(sim_df, capacity_kwh, rate_kw, strategy_fn):
    sim_df = sim_df.copy()  # To avoid adding columns to the original DataFrame, for every strategy, rate and capacity

    current_soc = 0.0
    total_savings = 0.0
    
    simulation_logs = []

    for i in range(len(sim_df)):
        this_hour = sim_df.iloc[i]
        future_df = sim_df.iloc[i:i + 24]

        charge_kwh, discharge_kwh = strategy_fn(
            row=this_hour,
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
        price_this_hour = this_hour[net_buy_price.l] if this_hour[net_household.l] > 0 else this_hour[net_sell_price.l]
        cost_no_batt = this_hour[net_household.l] * price_this_hour

        # Cost with battery: (net_kwh + charge - discharge) * relevant_price
        new_net_kwh = this_hour[net_household.l] + charge_kwh - discharge_kwh
        price_this_hour = this_hour[net_buy_price.l] if new_net_kwh > 0 else this_hour[net_sell_price.l]
        cost_with_batt = new_net_kwh * price_this_hour

        total_savings += cost_no_batt - cost_with_batt

        simulation_logs.append({
            'hour_starts_at': this_hour['hour_starts_at'],
            soc.l: current_soc,
            battery_charge.l: charge_kwh,
            battery_discharge.l: discharge_kwh,
            cost_no_battery.l: cost_no_batt,
            cost_with_battery.l: cost_with_batt
        })

    df_logs = pd.DataFrame(simulation_logs)
    sim_df = sim_df.merge(df_logs, on="hour_starts_at", how="left", suffixes=("", "_logged"))
    return total_savings, sim_df


def strategy_arbitrage(row, future_df, soc, capacity_kwh, rate_kw):
    actual_solar = row['production_kwh'] if pd.notna(row['production_kwh']) else 0.0
    charge_kwh = min(actual_solar, rate_kw)

    # Calculate effective prices including taxes and VAT
    if row['net_buy_price'] <= future_df['net_buy_price'].quantile(0.25):
        charge_kwh = rate_kw

    discharge_kwh = 0.0
    if soc > 0 and row['net_buy_price'] >= future_df['net_buy_price'].quantile(0.75):
        discharge_kwh = rate_kw

    return charge_kwh, discharge_kwh

#
# def strategy_greedy(row, future_df, soc, capacity_kwh, rate_kw):
#     price = row['consumption_unit_price_eur']
#     day_prices = future_df['consumption_unit_price_eur']
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
#     charge_kwh = row['production_kwh'] if pd.notna(row['production_kwh']) else 0.0
#
#     if row['consumption_unit_price_eur'] < 0.05:
#         charge_kwh = rate_kw
#
#     future_price = future_df['consumption_unit_price_eur'].max()
#     discharge_kwh = soc if future_price > 0.25 else 0
#
#     return charge_kwh, discharge_kwh


def strategy_optimal_mpc(row, future_df, soc, capacity_kwh, rate_kw,
                         horizon_hours=24, eta=0.90):
    future_df = future_df.iloc[:horizon_hours]
    n = len(future_df)
    
    # Calculate effective buy and sell prices including taxes and VAT
    buy = future_df[net_buy_price.l].values
    sell = future_df[net_sell_price.l].values

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
