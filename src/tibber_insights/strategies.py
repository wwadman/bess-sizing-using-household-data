import numpy as np
import pandas as pd
from .constants import net_buy_price, net_sell_price, production, consumption_unit_price_eur


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


def strategy_greedy(row, future_df, soc, capacity_kwh, rate_kw):
    price = row[consumption_unit_price_eur]
    day_prices = future_df[consumption_unit_price_eur]

    low_threshold = day_prices.quantile(0.2)
    high_threshold = day_prices.quantile(0.8)

    if price <= low_threshold:
        charge_kwh = rate_kw
        discharge_kwh = 0
    elif price >= high_threshold:
        charge_kwh = 0
        discharge_kwh = soc
    else:
        charge_kwh = 0
        discharge_kwh = 0

    return charge_kwh, discharge_kwh


def strategy_solar_plus_low_price(row, future_df, soc, capacity_kwh, rate_kw):
    charge_kwh = row[production] if pd.notna(row[production]) else 0.0

    if row[consumption_unit_price_eur] < 0.05:
        charge_kwh = rate_kw

    future_price = future_df[consumption_unit_price_eur].max()
    discharge_kwh = soc if future_price > 0.25 else 0

    return charge_kwh, discharge_kwh
