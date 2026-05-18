import numpy as np
import pandas as pd
from .constants import (NET_BUY_PRICE, NET_SELL_PRICE, PRODUCTION, CONSUMPTION_UNIT_PRICE_EUR, EXPECTED_CONSUMPTION,
                        EXPECTED_PRODUCTION, TIME, NET_VALUE, EXPECTED_MAX_CONSUMPTION)


def strategy_arbitrage(row, future_df, current_soc, capacity_kwh, max_rate_kw):
    actual_solar = row[PRODUCTION] if pd.notna(row[PRODUCTION]) else 0.0
    charge_kwh = min(actual_solar, max_rate_kw)

    # Calculate effective prices including taxes and VAT
    if row[NET_BUY_PRICE] <= future_df[NET_BUY_PRICE].quantile(0.25):
        charge_kwh = max_rate_kw

    discharge_kwh = 0.0
    if current_soc > 0 and row[NET_BUY_PRICE] >= future_df[NET_BUY_PRICE].quantile(0.75):
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
       with later high-price hours, provided it's profitable after efficiency losses.
    """

    num_hours = len(future_df)

    # Extract prices and household expectations for the optimization horizon
    buy_prices = future_df[NET_BUY_PRICE].values
    sell_prices = future_df[NET_SELL_PRICE].values
    exp_cons = future_df[EXPECTED_CONSUMPTION].values
    exp_prod = future_df[EXPECTED_PRODUCTION].values

    # Determine the marginal value of discharging and marginal cost of charging.
    # Discharging saves buy_price if it offsets CONSUMPTION, else it earns sell_price.
    # Charging costs buy_price if it comes from the grid, else it reduces export earnings (sell_price).
    # Since we don't know the exact split for arbitrary amounts, we'll use expectations
    # to rank the value of an action at each hour.

    # Initialize charging and discharging plans for each hour in the horizon
    charge_plan = np.zeros(num_hours)
    discharge_plan = np.zeros(num_hours)

    # --- Step 1: Optimize discharge of the current SOC ---
    # We want to use the energy we already have to offset the most expensive costs.
    remaining_to_discharge = current_soc
    # Use granular slots for Step 1 as well to prioritize offsetting CONSUMPTION.
    initial_discharge_data = []
    for i in range(num_hours):
        offset_amt = min(max_rate_kw, exp_cons[i])
        if offset_amt > 0:
            initial_discharge_data.append({'h': i, 'amt': offset_amt, 'val': buy_prices[i], 'type': 'offset buying'})
        export_amt = max_rate_kw - offset_amt
        if export_amt > 0:
            initial_discharge_data.append({'h': i, 'amt': export_amt, 'val': sell_prices[i], 'type': 'sell to grid'})

    initial_discharge_slots = pd.DataFrame(initial_discharge_data).sort_values(by='val', ascending=False)

    for i, slot in initial_discharge_slots.iterrows():
        if remaining_to_discharge <= 0.0001:
            break
        # How much can we DISCHARGE in this slot (limited by slot capacity and what reaches the grid)
        can_discharge = min(slot['amt'], remaining_to_discharge * round_trip_efficiency)
        discharge_plan[int(slot['h'])] += can_discharge
        remaining_to_discharge -= can_discharge / round_trip_efficiency

    # Track available capacity and space in each hour after the initial plan
    charge_bandwidth_avail = max_rate_kw - charge_plan  # Todo: set this later, as charge_plan is always np.zeros here??
    discharge_bandwidth_avail = max_rate_kw - discharge_plan

    available_storage_space = capacity_kwh - current_soc

    # Step 2: Optimize Arbitrage (Charge low, Sell/Offset high)
    # We look for pairs of (h_ch, h_dis) where we can profit.
    # h_ch must come before h_dis.
    
    # For a more granular optimization, we split each hour into two "slots":
    # 1. Household-offsetting slot (limited by exp_cons/exp_prod)
    # 2. Grid-trading slot (the remainder of the bandwidth)

    # Discharge slots: (hour_idx, amount_available, value)
    discharge_data = []
    for i in range(num_hours):
        # Slot 1: Offsetting household CONSUMPTION
        offset_amt = min(discharge_bandwidth_avail[i], exp_cons[i])
        if offset_amt > 0:
            discharge_data.append({'h': i, 'amt': offset_amt, 'val': buy_prices[i]})
        # Slot 2: Exporting to grid
        export_amt = discharge_bandwidth_avail[i] - offset_amt
        if export_amt > 0:
            discharge_data.append({'h': i, 'amt': export_amt, 'val': sell_prices[i]})
    
    discharge_slots = pd.DataFrame(discharge_data).sort_values(by='val', ascending=False)

    # Charge slots: (hour_idx, amount_available, cost)
    charge_data = []
    for i in range(num_hours):
        # Slot 1: Using household PRODUCTION
        solar_amt = min(charge_bandwidth_avail[i], exp_prod[i])
        if solar_amt > 0:
            charge_data.append({'h': i, 'amt': solar_amt, 'cost': sell_prices[i]})
        # Slot 2: Buying from grid
        grid_amt = charge_bandwidth_avail[i] - solar_amt
        if grid_amt > 0:
            charge_data.append({'h': i, 'amt': grid_amt, 'cost': buy_prices[i]})

    charge_slots = pd.DataFrame(charge_data).sort_values(by='cost')

    for d_idx, d_slot in discharge_slots.iterrows():
        for c_idx, c_slot in charge_slots.iterrows():
            h_dis = int(d_slot['h'])
            h_ch = int(c_slot['h'])

            if h_ch >= h_dis:  # Only consider charging BEFORE discharging (h_ch < h_dis)
                continue

            # Check profitability
            if round_trip_efficiency * d_slot['val'] <= c_slot['cost']:
                break
            
            # Amount we can move
            transfer_amount = min(
                c_slot['amt'], 
                d_slot['amt'] / round_trip_efficiency, 
                available_storage_space
            )
            
            if transfer_amount <= 0.0001:
                continue
            
            # Update plans
            charge_plan[h_ch] += transfer_amount
            discharge_plan[h_dis] += transfer_amount * round_trip_efficiency
            
            # Update slot amounts and storage
            charge_slots.at[c_idx, 'amt'] -= transfer_amount
            discharge_slots.at[d_idx, 'amt'] -= transfer_amount * round_trip_efficiency
            available_storage_space -= transfer_amount
            
            if available_storage_space <= 0.0001:
                break
        if available_storage_space <= 0.0001:
            break

    # Return the planned action for the current hour (index 0)
    return float(charge_plan[0]), float(discharge_plan[0])


def strategy_optimal_mpc2(row, future_df, current_soc, capacity_kwh, max_rate_kw,
                         horizon_hours=24, round_trip_efficiency=0.90):
    """Similar to strategy_optimal_mpc but collecting discharge slots
    (pluss all other series that have all hour slots cross-joined with [Grid, Household])
     in 1 dataframe net_discharge_values for better understanding"""

    net_discharge_values = _get_net_discharge_values(future_df)
    remaining_to_discharge = current_soc
    for i, slot in net_discharge_values.iterrows():
        can_discharge = min(slot[EXPECTED_MAX_CONSUMPTION], remaining_to_discharge * round_trip_efficiency)
        net_discharge_values.at[i, 'Discharge plan'] = can_discharge
        remaining_to_discharge -= can_discharge / round_trip_efficiency

    net_discharge_values['charge_bandwidth_avail'] = max_rate_kw
    net_discharge_values['discharge_bandwidth_avail'] = max_rate_kw - net_discharge_values['Discharge plan']

    pass


def strategy_greedy(row, future_df, current_soc, capacity_kwh, max_rate_kw):
    price = row[CONSUMPTION_UNIT_PRICE_EUR]
    day_prices = future_df[CONSUMPTION_UNIT_PRICE_EUR]

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
    charge_kwh = row[PRODUCTION] if pd.notna(row[PRODUCTION]) else 0.0

    if row[CONSUMPTION_UNIT_PRICE_EUR] < 0.05:
        charge_kwh = max_rate_kw

    future_price = future_df[CONSUMPTION_UNIT_PRICE_EUR].max()
    discharge_kwh = current_soc if future_price > 0.25 else 0

    return charge_kwh, discharge_kwh


def _get_net_discharge_values(future_df):
    """
    Even smaller version without set_index(TIME), returning a flat DataFrame.
    """
    household = (future_df
                 [[TIME, NET_BUY_PRICE, EXPECTED_CONSUMPTION]]
                 .rename(columns={NET_BUY_PRICE: NET_VALUE, EXPECTED_CONSUMPTION: EXPECTED_MAX_CONSUMPTION}))
    grid = future_df[[TIME, NET_SELL_PRICE]].rename(columns={NET_SELL_PRICE: NET_VALUE})

    household.insert(0, 'Discharge to', 'Household')
    grid.insert(0, 'Discharge to', 'Grid')
    grid.insert(3, EXPECTED_MAX_CONSUMPTION, np.inf)

    net_discharge_values = (pd.concat([household, grid])
                            .sort_values(by=NET_VALUE, ascending=False)
                            .set_index(['Discharge to', TIME])
                            )

    return net_discharge_values
