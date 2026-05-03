import numpy as np
import pandas as pd
from .constants import EFFICIENCY
from .billing import calculate_gross_buy_price, calculate_gross_sell_price

def run_battery_simulation(profile_df, capacity_kwh, rate_kw, strategy_fn):
    df = profile_df.copy()
    df['hour'] = df['hour_starts_at'].dt.hour

    hourly_stats = df.groupby('hour').agg({
        'consumption_kwh': 'mean',
        'production_kwh': 'mean',
    }).rename(columns={'consumption_kwh': 'exp_cons', 'production_kwh': 'exp_prod'})

    df = df.merge(hourly_stats, on='hour', how='left')

    soc = 0.0
    total_savings = 0.0
    
    simulation_logs = []

    for i in range(len(df)):
        row = df.iloc[i]
        future_df = df.iloc[i:i + 24]

        charge_kwh, discharge_kwh = strategy_fn(
            row=row,
            future_df=future_df,
            soc=soc,
            capacity_kwh=capacity_kwh,
            rate_kw=rate_kw,
            hourly_stats=hourly_stats,
        )

        charge_kwh = max(0, min(charge_kwh, rate_kw, capacity_kwh - soc))
        soc += charge_kwh * EFFICIENCY

        discharge_kwh = max(0, min(discharge_kwh, rate_kw, soc * EFFICIENCY))
        soc -= discharge_kwh / EFFICIENCY

        # Savings calculation: discharging from battery avoids buying at the current gross price.
        current_gross_buy_price = calculate_gross_buy_price(row['consumption_unit_price_eur'])
        current_gross_sell_price = calculate_gross_sell_price(row['production_unit_price_eur'])
        
        # Cost without battery: net buy * buy_price (if positive) or net sell * sell_price (if negative)
        if row['net_kwh'] > 0:
            cost_no_batt = row['net_kwh'] * current_gross_buy_price
        else:
            cost_no_batt = row['net_kwh'] * current_gross_sell_price
            
        # Cost with battery: (net_kwh + charge - discharge) * relevant_price
        new_net_kwh = row['net_kwh'] + charge_kwh - discharge_kwh
        if new_net_kwh > 0:
            cost_with_batt = new_net_kwh * current_gross_buy_price
        else:
            cost_with_batt = new_net_kwh * current_gross_sell_price

        total_savings += discharge_kwh * current_gross_buy_price

        simulation_logs.append({
            'hour_starts_at': row['hour_starts_at'],
            'soc_kwh': soc,
            'charge_kwh': charge_kwh,
            'discharge_kwh': discharge_kwh,
            'net_kwh': row['net_kwh'],
            'consumption_unit_price_eur': row['consumption_unit_price_eur'],
            'cost_no_batt_eur': cost_no_batt,
            'cost_with_batt_eur': cost_with_batt
        })

    return total_savings, pd.DataFrame(simulation_logs)


def strategy_arbitrage(row, future_df, soc, capacity_kwh, rate_kw, hourly_stats):
    actual_solar = row['production_kwh'] if pd.notna(row['production_kwh']) else 0.0
    charge_kwh = min(actual_solar, rate_kw)

    # Calculate effective prices including taxes and VAT
    buy_prices = calculate_gross_buy_price(future_df['consumption_unit_price_eur'])
    current_buy_price = calculate_gross_buy_price(row['consumption_unit_price_eur'])

    if current_buy_price <= buy_prices.quantile(0.25):
        charge_kwh = rate_kw

    discharge_kwh = 0.0
    if soc > 0 and current_buy_price >= buy_prices.quantile(0.75):
        discharge_kwh = rate_kw

    return charge_kwh, discharge_kwh


def strategy_greedy(row, future_df, soc, capacity_kwh, rate_kw, hourly_stats):
    price = row['consumption_unit_price_eur']
    day_prices = future_df['consumption_unit_price_eur']

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


def strategy_solar_plus_low_price(row, future_df, soc, capacity_kwh, rate_kw, hourly_stats):
    charge_kwh = row['production_kwh'] if pd.notna(row['production_kwh']) else 0.0

    if row['consumption_unit_price_eur'] < 0.05:
        charge_kwh = rate_kw

    future_price = future_df['consumption_unit_price_eur'].max()
    discharge_kwh = soc if future_price > 0.25 else 0

    return charge_kwh, discharge_kwh


def strategy_optimal_mpc(row, future_df, soc, capacity_kwh, rate_kw, hourly_stats,
                         horizon_hours=24, eta=0.90):
    future_df = future_df.iloc[:horizon_hours]
    n = len(future_df)
    
    # Calculate effective buy and sell prices including taxes and VAT
    buy = calculate_gross_buy_price(future_df['consumption_unit_price_eur'].values)
    sell = calculate_gross_sell_price(future_df['production_unit_price_eur'].values)

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
