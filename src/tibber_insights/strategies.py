import numpy as np
import pandas as pd
from .constants import net_buy_price, net_sell_price, production, consumption_unit_price_eur


def strategy_arbitrage(row, future_df, current_soc, capacity_kwh, max_rate_kw):
    actual_solar = row[production] if pd.notna(row[production]) else 0.0
    charge_kwh = min(actual_solar, max_rate_kw)

    # Calculate effective prices including taxes and VAT
    if row[net_buy_price] <= future_df[net_buy_price].quantile(0.25):
        charge_kwh = max_rate_kw

    discharge_kwh = 0.0
    if current_soc > 0 and row[net_buy_price] >= future_df[net_buy_price].quantile(0.75):
        discharge_kwh = max_rate_kw

    return charge_kwh, discharge_kwh


def strategy_optimal_mpc(row, future_df, current_soc, capacity_kwh, max_rate_kw,
                         horizon_hours=24, round_trip_efficiency=0.90):
    """
    Model Predictive Control (MPC) strategy that optimizes battery usage over a future horizon.
    
    The algorithm performs two main steps:
    1. Initial Discharge: Planning to discharge the current stored energy (SOC) at the most 
       profitable future hours (highest sell prices).
    2. Arbitrage Optimization: Planning charge-discharge cycles by pairing low-price hours 
       with subsequent high-price hours, provided it's profitable after efficiency losses.
    """
    future_df = future_df.iloc[:horizon_hours]
    num_hours = len(future_df)

    # Extract buy and sell prices for the optimization horizon
    buy_prices = future_df[net_buy_price].values
    sell_prices = future_df[net_sell_price].values

    # Initialize charging and discharging plans for each hour in the horizon
    charge_plan = np.zeros(num_hours)
    discharge_plan = np.zeros(num_hours)

    # --- Step 1: Optimize discharge of the current SOC ---
    # We want to sell the energy we already have at the highest possible future prices.
    remaining_to_discharge = current_soc
    # Sort hours by sell price in descending order
    profitable_sell_hours = np.argsort(sell_prices)[::-1]
    
    for hour_idx in profitable_sell_hours:
        if remaining_to_discharge <= 0:
            break
        
        # Max energy we can get out of the battery (considering discharge rate and efficiency)
        # Note: 'd = remaining_soc * efficiency' means 'remaining_soc' is the energy 
        # in the battery, 'd' is what actually reaches the grid.
        can_discharge = min(max_rate_kw, remaining_to_discharge * round_trip_efficiency)
        discharge_plan[hour_idx] += can_discharge
        remaining_to_discharge -= can_discharge / round_trip_efficiency

    # Track available capacity and space in each hour after the initial plan
    # c_avail/d_avail is the remaining power bandwidth (kW) for additional charging/discharging
    charge_bandwidth_avail = max_rate_kw - charge_plan
    discharge_bandwidth_avail = max_rate_kw - discharge_plan
    # available_storage_space is the kWh we can still add to the battery
    available_storage_space = capacity_kwh - current_soc

    # --- Step 2: Optimize Arbitrage (Charge low, Sell high) ---
    # We look for pairs of (charge_hour, discharge_hour) where we can profit.
    # charge_hour must come before discharge_hour.
    
    # Hours sorted by buy price (lowest first)
    cheapest_buy_hours = np.argsort(buy_prices)
    # Hours sorted by sell price (highest first)
    expensive_sell_hours = np.argsort(sell_prices)[::-1]

    for h_dis in expensive_sell_hours:
        for h_ch in cheapest_buy_hours:
            # Only consider charging BEFORE discharging
            if h_ch >= h_dis:
                continue
            
            # Check if arbitrage is profitable considering efficiency losses
            if round_trip_efficiency * sell_prices[h_dis] - buy_prices[h_ch] <= 0:
                # Since we sorted by cheapest buy first, if this one isn't profitable, 
                # no subsequent (more expensive) buy hours will be profitable for this h_dis.
                break
            
            # Calculate how much we can move in this cycle.
            # Limited by: charge rate at h_ch, discharge rate at h_dis, and battery capacity.
            transfer_amount = min(
                charge_bandwidth_avail[h_ch], 
                discharge_bandwidth_avail[h_dis] / round_trip_efficiency, 
                available_storage_space
            )
            
            if transfer_amount <= 0:
                continue
            
            # Update plans and remaining capacities
            charge_plan[h_ch] += transfer_amount
            discharge_plan[h_dis] += transfer_amount * round_trip_efficiency
            
            charge_bandwidth_avail[h_ch] -= transfer_amount
            discharge_bandwidth_avail[h_dis] -= transfer_amount * round_trip_efficiency
            available_storage_space -= transfer_amount
            
        if available_storage_space <= 0:
            break

    # Return the planned action for the current hour (index 0)
    return float(charge_plan[0]), float(discharge_plan[0])


def strategy_greedy(row, future_df, current_soc, capacity_kwh, max_rate_kw):
    price = row[consumption_unit_price_eur]
    day_prices = future_df[consumption_unit_price_eur]

    low_threshold = day_prices.quantile(0.2)
    high_threshold = day_prices.quantile(0.8)

    if price <= low_threshold:
        charge_kwh = max_rate_kw
        discharge_kwh = 0
    elif price >= high_threshold:
        charge_kwh = 0
        discharge_kwh = current_soc
    else:
        charge_kwh = 0
        discharge_kwh = 0

    return charge_kwh, discharge_kwh


def strategy_solar_plus_low_price(row, future_df, current_soc, capacity_kwh, max_rate_kw):
    charge_kwh = row[production] if pd.notna(row[production]) else 0.0

    if row[consumption_unit_price_eur] < 0.05:
        charge_kwh = max_rate_kw

    future_price = future_df[consumption_unit_price_eur].max()
    discharge_kwh = current_soc if future_price > 0.25 else 0

    return charge_kwh, discharge_kwh
