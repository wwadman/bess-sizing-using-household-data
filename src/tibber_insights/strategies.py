import pulp
from .constants import (NET_BUY_PRICE, NET_SELL_PRICE, PRODUCTION, CONSUMPTION_UNIT_PRICE_EUR, EXPECTED_CONSUMPTION,
                        EXPECTED_PRODUCTION, TIME, NET_VALUE, EXPECTED_MAX_CONSUMPTION,
                        EFFICIENCY_DISCHARGING, EFFICIENCY_CHARGING,
                        CHARGE_FROM_HOUSE, CHARGE_FROM_GRID, DISCHARGE_TO_HOUSE, DISCHARGE_TO_GRID)


def strategy_daily_lp(row, future_df, current_soc, capacity_kwh, max_rate_kw):
    """
    Optimizes battery behavior using Linear Programming (LP).

    It maximizes net benefit over a future horizon, by modeling 4 different ways of battery monetization:
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

    # Aggregate variables for total (dis)charge
    ch = [ch_h[t] + ch_g[t] for t in range(T)]
    dis = [dis_h[t] + dis_g[t] for t in range(T)]

    # Binary variables to prevent simultaneous charging and discharging
    is_charging = [pulp.LpVariable(f"is_charging_{t}", cat=pulp.LpBinary) for t in range(T)]

    soc = [pulp.LpVariable(f"soc_{t}", lowBound=0, upBound=capacity_kwh) for t in range(T)]

    # 4. Objective Function
    benefit_terms = [
          dis_h[t] * p_buy[t]
        + dis_g[t] * p_sell[t]
        -  ch_h[t] * p_sell[t]
        -  ch_g[t] * p_buy[t]
        for t in range(T)
    ]
    prob += pulp.lpSum(benefit_terms)

    # 5. Constraints
    for t in range(T):
        # State of Charge Dynamics
        prev_soc = current_soc if t == 0 else soc[t-1]
        prob += (soc[t] == prev_soc
                 + ch[t] * EFFICIENCY_CHARGING
                 - dis[t] / EFFICIENCY_DISCHARGING)

        # Rate of (dis)charge constraints with binary switch
        prob += ch[t] * EFFICIENCY_CHARGING <= max_rate_kw * is_charging[t]
        prob += dis[t] / EFFICIENCY_DISCHARGING <= max_rate_kw * (1 - is_charging[t])

        # Household Flow Boundaries
        prob += ch_h[t] <= e_prod[t]
        prob += dis_h[t] <= e_cons[t]

        # SOC limits
        prob += ch[t] * EFFICIENCY_CHARGING <= capacity_kwh - prev_soc
        prob += dis[t] / EFFICIENCY_DISCHARGING <= prev_soc

    # 6. Solve the problem
    # PULP_CBC_CMD is the default solver. We suppress output for speed.
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    # 7. Add planned actions as columns to future_df
    future_df = future_df.copy()
    future_df[CHARGE_FROM_HOUSE] = [float(pulp.value(ch_h[t])) for t in range(T)]
    future_df[CHARGE_FROM_GRID] = [float(pulp.value(ch_g[t])) for t in range(T)]
    future_df[DISCHARGE_TO_HOUSE] = [float(pulp.value(dis_h[t])) for t in range(T)]
    future_df[DISCHARGE_TO_GRID] = [float(pulp.value(dis_g[t])) for t in range(T)]

    return future_df