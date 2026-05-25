import numpy as np
import pandas as pd
import pulp
from .constants import (NET_BUY_PRICE, NET_SELL_PRICE, PRODUCTION, CONSUMPTION_UNIT_PRICE_EUR, EXPECTED_CONSUMPTION,
                        EXPECTED_PRODUCTION, TIME, NET_VALUE, EXPECTED_MAX_CONSUMPTION,
                        EFFICIENCY_DISCHARGING, EFFICIENCY_CHARGING)


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


def strategy_linear_programming(row, future_df, current_soc, capacity_kwh, max_rate_kw):
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
        dis_h[t] * p_buy[t]
        + dis_g[t] * p_sell[t]
        - ch_h[t] * p_sell[t]
        - ch_g[t] * p_buy[t]
        for t in range(T)
    ]
    prob += pulp.lpSum(benefit_terms)
    
    # 5. Constraints
    for t in range(T):
        # State of Charge Dynamics
        prev_soc = current_soc if t == 0 else soc[t-1]
        prob += (soc[t] == prev_soc
                 + (ch_h[t] + ch_g[t]) * EFFICIENCY_CHARGING
                 - (dis_h[t] + dis_g[t]) / EFFICIENCY_DISCHARGING)
        
        # Rate of (dis)charge constraints with binary switch
        prob += ch_h[t] + ch_g[t] <= max_rate_kw * is_charging[t]
        prob += dis_h[t] + dis_g[t] <= max_rate_kw * (1 - is_charging[t])
        
        # Household Flow Boundaries
        prob += ch_h[t] <= e_prod[t]
        prob += dis_h[t] <= e_cons[t]

        # SOC limits
        prob += (ch_h[t] + ch_g[t]) * EFFICIENCY_CHARGING <= capacity_kwh - prev_soc
        prob += (dis_h[t] + dis_g[t]) / EFFICIENCY_DISCHARGING <= prev_soc
        
    # 6. Solve the problem
    # PULP_CBC_CMD is the default solver. We suppress output for speed.
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    # 7. Extract the planned actions for the current hour (t=0)
    # If the solver failed to find a solution (shouldn't happen here), return all zeros
    from pandas import Timestamp
    if pulp.LpStatus[prob.status] != 'Optimal':
        return 0.0, 0.0, 0.0, 0.0
        
    ch_h_now = pulp.value(ch_h[0])
    ch_g_now = pulp.value(ch_g[0])
    dis_h_now = pulp.value(dis_h[0])
    dis_g_now = pulp.value(dis_g[0])

    return float(ch_h_now), float(ch_g_now), float(dis_h_now), float(dis_g_now)
