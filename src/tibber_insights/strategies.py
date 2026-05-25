import numpy as np
import pandas as pd
import pulp
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

    return charge_kwh, 0.0, 0.0, discharge_kwh


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

    # Return the planned actions: (charge_from_house, charge_from_grid, discharge_to_house, discharge_to_grid)
    # Since this strategy does not distinguish, we'll return totals as from/to grid
    return 0.0, float(charge_plan[0]), 0.0, float(discharge_plan[0])


def strategy_optimal_mpc2(row, future_df, current_soc, capacity_kwh, max_rate_kw,
                         horizon_hours=24, round_trip_efficiency=0.90):
    """Similar to strategy_optimal_mpc but collecting discharge slots
    (pluss all other series that have all hour slots cross-joined with [Grid, Household])
     in 1 dataframe net_discharge_values for better understanding"""

    net_discharge_values = _get_net_discharge_values(future_df)
    net_discharge_values['charge_bandwidth_avail'] = float(max_rate_kw)
    net_discharge_values['discharge_bandwidth_avail'] = float(max_rate_kw)

    current_soc_after_discharge = current_soc
    current_time = future_df[TIME].iloc[0]
    net_discharge_values['Discharge plan'] = 0.0
    for idx, slot in net_discharge_values.iterrows():
        # Discharge is limited by remaining SOC and available bandwidth for that hour
        h = idx[1]
        h_bw_info = net_discharge_values.loc[(slice(None), h), 'discharge_bandwidth_avail']
        avail_bw = h_bw_info.iloc[0] if not h_bw_info.empty else 0.0

        can_discharge = min(slot[EXPECTED_MAX_CONSUMPTION], current_soc_after_discharge * round_trip_efficiency, avail_bw)
        
        net_discharge_values.at[idx, 'Discharge plan'] = can_discharge
        
        # Update bandwidth: discharging reduces available bandwidth for both charging and discharging
        h_mask = net_discharge_values.index.get_level_values(TIME) == h
        net_discharge_values.loc[h_mask, 'discharge_bandwidth_avail'] -= can_discharge
        net_discharge_values.loc[h_mask, 'charge_bandwidth_avail'] -= can_discharge
        
        current_soc_after_discharge -= can_discharge / round_trip_efficiency

    # Arbitrage logic: collecting potential charge events
    # Charge from household production (solar) has cost = NET_SELL_PRICE (opportunity cost)
    charge_household = (future_df[[TIME, NET_SELL_PRICE, EXPECTED_PRODUCTION]]
                        .rename(columns={NET_SELL_PRICE: 'Cost', EXPECTED_PRODUCTION: 'Available amount'}))
    
    # Charge from grid has cost = NET_BUY_PRICE
    charge_grid = (future_df[[TIME, NET_BUY_PRICE]]
                   .rename(columns={NET_BUY_PRICE: 'Cost'}))
    charge_household.insert(0, 'Charge from', 'Household')
    charge_grid.insert(0, 'Charge from', 'Grid')
    charge_grid.insert(3, 'Available amount', np.inf)

    charge_slots = (pd.concat([charge_household, charge_grid])
                    .sort_values(by='Cost', ascending=True)
                    .set_index(['Charge from', TIME]))

    net_discharge_values['Arbitrage discharge plan'] = 0.0
    charge_slots['Charge plan'] = 0.0
    available_storage_space = capacity_kwh - current_soc
    current_time = future_df[TIME].iloc[0]

    for d_idx, d_slot in net_discharge_values.iterrows():
        for c_idx, c_slot in charge_slots.iterrows():
            h_dis = d_idx[1]
            h_ch = c_idx[1]

            if h_ch >= h_dis:
                continue

            if round_trip_efficiency * d_slot[NET_VALUE] <= c_slot['Cost']:
                break

            # Re-calculate transfer_amount based on CURRENT bandwidth for BOTH hours
            # This is key: if h_ch or h_dis already used bandwidth for something else
            # (including each other!), they must share the remaining pool.
            # We also ensure that we don't charge in an hour that is already discharging
            # (and vice versa) to avoid simultaneous actions.
            h_ch_bw_info = net_discharge_values.loc[(slice(None), h_ch), 'charge_bandwidth_avail']
            ch_bw = h_ch_bw_info.iloc[0] if not h_ch_bw_info.empty else 0.0
            
            h_dis_bw_info = net_discharge_values.loc[(slice(None), h_dis), 'discharge_bandwidth_avail']
            dis_bw = h_dis_bw_info.iloc[0] if not h_dis_bw_info.empty else 0.0

            # Special check to avoid simultaneous charge/discharge:
            # If h_ch already has a DISCHARGE plan, its available charging bandwidth 
            # is 0 for this simple MPC (to avoid netting).
            h_ch_total_dis = (net_discharge_values.xs(h_ch, level=TIME)['Discharge plan'].sum() +
                              net_discharge_values.xs(h_ch, level=TIME)['Arbitrage discharge plan'].sum())
            if h_ch_total_dis > 0:
                ch_bw = 0.0

            # Similarly for h_dis: if it already has a CHARGE plan
            h_dis_total_ch = charge_slots.xs(h_dis, level=TIME)['Charge plan'].sum()
            if h_dis_total_ch > 0:
                dis_bw = 0.0

            transfer_amount = min(
                c_slot['Available amount'],
                dis_bw / round_trip_efficiency,
                available_storage_space,
                ch_bw
            )

            if transfer_amount <= 0.0001:
                continue

            charge_slots.at[c_idx, 'Charge plan'] += transfer_amount
            net_discharge_values.at[d_idx, 'Arbitrage discharge plan'] += transfer_amount * round_trip_efficiency
            
            charge_slots.at[c_idx, 'Available amount'] -= transfer_amount

            # Update bandwidth for both hours across all slots
            # If we charge at h_ch, it uses bandwidth at h_ch.
            # If we discharge at h_dis, it uses bandwidth at h_dis.
            # Simultaneous charging and discharging in the same hour is now impossible
            # because they share the same bandwidth pool.
            h_ch_mask = net_discharge_values.index.get_level_values(TIME) == h_ch
            net_discharge_values.loc[h_ch_mask, 'charge_bandwidth_avail'] -= transfer_amount
            net_discharge_values.loc[h_ch_mask, 'discharge_bandwidth_avail'] -= transfer_amount

            h_dis_mask = net_discharge_values.index.get_level_values(TIME) == h_dis
            net_discharge_values.loc[h_dis_mask, 'charge_bandwidth_avail'] -= transfer_amount * round_trip_efficiency
            net_discharge_values.loc[h_dis_mask, 'discharge_bandwidth_avail'] -= transfer_amount * round_trip_efficiency

            available_storage_space -= transfer_amount
            if available_storage_space <= 0.0001:
                break
        if available_storage_space <= 0.0001:
            break

    current_time = future_df[TIME].iloc[0]
    charge_now = charge_slots.xs(current_time, level=TIME)['Charge plan'].sum()
    discharge_now = (net_discharge_values.xs(current_time, level=TIME)['Discharge plan'].sum() +
                     net_discharge_values.xs(current_time, level=TIME)['Arbitrage discharge plan'].sum())

    # Return the planned actions: (charge_from_house, charge_from_grid, discharge_to_house, discharge_to_grid)
    # Since this strategy does not distinguish, we'll return totals as from/to grid
    return 0.0, float(charge_now), 0.0, float(discharge_now)


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

    return 0.0, float(charge_kwh), 0.0, float(discharge_kwh)


def strategy_solar_plus_low_price(row, future_df, current_soc, capacity_kwh, max_rate_kw):
    charge_kwh = row[PRODUCTION] if pd.notna(row[PRODUCTION]) else 0.0

    if row[CONSUMPTION_UNIT_PRICE_EUR] < 0.05:
        charge_kwh = max_rate_kw

    future_price = future_df[CONSUMPTION_UNIT_PRICE_EUR].max()
    discharge_kwh = current_soc if future_price > 0.25 else 0

    return 0.0, float(charge_kwh), 0.0, float(discharge_kwh)


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


def strategy_linear_programming(row, future_df, current_soc, capacity_kwh, max_rate_kw,
                                 round_trip_efficiency=0.90):
    """
    Optimizes battery behavior using Linear Programming (LP).
    
    The problem is modeled as a maximization of net benefit over a future horizon.
    We split energy flows into four variables to handle different values of energy:
    - ch_h: Charge from House (solar) -> Opportunity cost: p_sell
    - ch_g: Charge from Grid -> Cost: p_buy
    - dis_h: Discharge to House -> Value: p_buy (avoided cost)
    - dis_g: Discharge to Grid -> Value: p_sell (revenue)
    """
    T = len(future_df)
    
    # 1. Initialize the LP Problem
    # We use a maximization objective to maximize 'savings' or 'net benefit'
    prob = pulp.LpProblem("Battery_Optimization", pulp.LpMaximize)
    
    # 2. Parameters (Inputs)
    p_buy = future_df[NET_BUY_PRICE].values
    p_sell = future_df[NET_SELL_PRICE].values
    e_cons = future_df[EXPECTED_CONSUMPTION].values
    e_prod = future_df[EXPECTED_PRODUCTION].values
    rte = round_trip_efficiency
    
    # 3. Decision Variables
    # All are continuous and non-negative
    ch_h = [pulp.LpVariable(f"ch_h_{t}", lowBound=0) for t in range(T)]
    ch_g = [pulp.LpVariable(f"ch_g_{t}", lowBound=0) for t in range(T)]
    dis_h = [pulp.LpVariable(f"dis_h_{t}", lowBound=0) for t in range(T)]
    dis_g = [pulp.LpVariable(f"dis_g_{t}", lowBound=0) for t in range(T)]
    # Binary variables to prevent simultaneous charging and discharging
    is_charging = [pulp.LpVariable(f"is_charging_{t}", cat=pulp.LpBinary) for t in range(T)]
    
    soc = [pulp.LpVariable(f"soc_{t}", lowBound=0, upBound=capacity_kwh) for t in range(T)]
    
    # 4. Objective Function
    # Maximize: sum(dis_h*p_buy + dis_g*p_sell - ch_h*p_sell - ch_g*p_buy)
    benefit_terms = [
        dis_h[t] * p_buy[t] + dis_g[t] * p_sell[t] - ch_h[t] * p_sell[t] - ch_g[t] * p_buy[t]
        for t in range(T)
    ]
    prob += pulp.lpSum(benefit_terms)
    
    # 5. Constraints
    for t in range(T):
        # State of Charge Dynamics
        prev_soc = current_soc if t == 0 else soc[t-1]
        # soc_t = soc_{t-1} + η*(ch_h + ch_g) - (1/η)*(dis_h + dis_g)
        prob += soc[t] == prev_soc + rte * (ch_h[t] + ch_g[t]) - (1 / rte) * (dis_h[t] + dis_g[t])
        
        # Power Bandwidth (Rate) Constraints with Binary switch
        # ch_h + ch_g <= max_rate_kw * is_charging
        # dis_h + dis_g <= max_rate_kw * (1 - is_charging)
        prob += ch_h[t] + ch_g[t] <= max_rate_kw * is_charging[t]
        prob += dis_h[t] + dis_g[t] <= max_rate_kw * (1 - is_charging[t])
        
        # Household Flow Boundaries
        prob += ch_h[t] <= e_prod[t]
        prob += dis_h[t] <= e_cons[t]
        
    # 6. Solve the problem
    # PULP_CBC_CMD is the default solver. We suppress output for speed.
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    # 7. Extract the planned actions for the current hour (t=0)
    # If the solver failed to find a solution (shouldn't happen here), return all zeros
    if pulp.LpStatus[prob.status] != 'Optimal':
        return 0.0, 0.0, 0.0, 0.0
        
    ch_h_now = pulp.value(ch_h[0])
    ch_g_now = pulp.value(ch_g[0])
    dis_h_now = pulp.value(dis_h[0])
    dis_g_now = pulp.value(dis_g[0])

    return float(ch_h_now), float(ch_g_now), float(dis_h_now), float(dis_g_now)
