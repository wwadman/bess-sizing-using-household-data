import pandas as pd
from .quantities import (
    NET_HOUSEHOLD, CHARGE_FROM_HOUSE, CHARGE_FROM_GRID,
    DISCHARGE_TO_HOUSE, DISCHARGE_TO_GRID,
    SOC, COST_WO_BESS, COST_WITH_BESS, NET_BUY_PRICE, NET_SELL_PRICE, TIME,
    SAVINGS, CUMULATIVE_SAVINGS_DAILY, DAILY_SAVINGS_TOTAL,
    NET_HOUSEHOLD_WITH_BESS, CONSUMPTION, PRODUCTION, ANNUAL_SAVINGS, PROFIT_AFTER_10_YEARS, PAYBACK_PERIOD
)

def simulate(sim_df, bess, strategy_fn):
    sim_df = sim_df.copy()  # To avoid adding columns to the original DataFrame, for every strategy, rate and capacity
    current_soc = bess.capacity/2  # Just to enable sanity-checking/debugging during the first TIME steps of the simulation

    simulation_logs = []

    # Find all indices where the hour is 14:00
    # Use reset_index to ensure we have a continuous range of integer indices if sim_df doesn't
    sim_df_indexed = sim_df.reset_index(drop=True)
    indices_14h = sim_df_indexed.index[sim_df_indexed[TIME].dt.hour == 14].tolist()
    hours_from_2pm_till_next_midnight = 10 + 24
    
    for i in indices_14h:
        # Add a waitbar that fills up every n steps.
        print(f"\rSimulating {bess}: {i}/{len(sim_df_indexed)}", end='', flush=True)
        future_df = sim_df.iloc[i:i + hours_from_2pm_till_next_midnight]
        plan_df = strategy_fn(future_df=future_df, current_soc=current_soc, bess=bess)

        # Execute 24 hours (or less if at the end of sim_df_indexed)
        steps_to_execute = min(24, len(sim_df_indexed) - i)
        
        for t in range(steps_to_execute):
            idx = i + t
            row_now = sim_df_indexed.iloc[idx]
            
            # Check if plan has enough steps
            if t >= len(plan_df):
                break
            
            ch_h = plan_df.iloc[t][CHARGE_FROM_HOUSE]
            ch_g = plan_df.iloc[t][CHARGE_FROM_GRID]
            dis_h = plan_df.iloc[t][DISCHARGE_TO_HOUSE]
            dis_g = plan_df.iloc[t][DISCHARGE_TO_GRID]

            # Check all physical limits and bess constraints
            charge = ch_h + ch_g
            soc_charge_bump = charge * bess.efficiency_charging
            discharge = dis_h + dis_g
            soc_discharge_dip = discharge / bess.efficiency_discharging

            # 1. Total (dis)charge cannot exceed the max rate
            eps = 1e-4  # some margin to counter numerical errors
            assert -eps <= soc_charge_bump <= bess.charging_rate + eps, \
                f"Total charge {soc_charge_bump} should be between 0 and max rate {bess.charging_rate}"
            assert -eps <= soc_discharge_dip <= bess.charging_rate + eps, \
                f"Total discharge {soc_discharge_dip} should be between 0 and max rate {bess.charging_rate}"

            # Update SOC for next time step and check if SOC is within limits
            current_soc = current_soc + soc_charge_bump - soc_discharge_dip
            assert -eps <= current_soc <= bess.capacity + eps, \
                f"Current SOC {current_soc} should be within [0, {bess.capacity}]."

            cost_wo_batt = row_now[CONSUMPTION] * row_now[NET_BUY_PRICE] - row_now[PRODUCTION] * row_now[NET_SELL_PRICE]

            new_net_kwh = row_now[NET_HOUSEHOLD] + charge - discharge
            bess_savings = (dis_h - ch_g) * row_now[NET_BUY_PRICE] + (dis_g - ch_h) * row_now[NET_SELL_PRICE]
            cost_with_batt = cost_wo_batt - bess_savings

            simulation_logs.append({
                TIME: row_now[TIME],
                SOC: current_soc,
                CHARGE_FROM_HOUSE: ch_h,
                CHARGE_FROM_GRID: ch_g,
                DISCHARGE_TO_HOUSE: dis_h,
                DISCHARGE_TO_GRID: dis_g,
                NET_HOUSEHOLD_WITH_BESS: new_net_kwh,
                COST_WO_BESS: cost_wo_batt,
                COST_WITH_BESS: cost_with_batt
            })

    df_logs = pd.DataFrame(simulation_logs)
    df_logs = df_logs.drop_duplicates(subset=[TIME], keep='first') # If 24h blocks overlap (they shouldn't if we step correctly, but just in case)
    df_logs[SAVINGS] = df_logs[COST_WO_BESS] - df_logs[COST_WITH_BESS]

    # Calculate cumulative savings per day
    df_logs[CUMULATIVE_SAVINGS_DAILY] = df_logs.groupby(df_logs[TIME].dt.date)[SAVINGS].cumsum()

    # Split cumulative savings into hourly growth (0-22h) and daily total (23h)
    is_hour_23 = df_logs[TIME].dt.hour == 23
    df_logs[DAILY_SAVINGS_TOTAL] = df_logs[CUMULATIVE_SAVINGS_DAILY].where(is_hour_23)
    df_logs[CUMULATIVE_SAVINGS_DAILY] = df_logs[CUMULATIVE_SAVINGS_DAILY].where(~is_hour_23)

    sim_df = sim_df.merge(df_logs, on=TIME, how="left", suffixes=("", "_logged"))
    return sim_df


def compute_savings_stats(sim_df, bess_price):
    savings = sim_df.Savings.sum()
    n_steps_with_savings_simulated = sim_df.Savings.notna().sum()
    n_years_with_savings_simulated = n_steps_with_savings_simulated / 24 / 365  # Assuming hourly time steps
    if 0.05 < n_years_with_savings_simulated % 1 < 0.95:
        print(f'WARNING: period of simulated savings ({n_years_with_savings_simulated:.2f} years) '
              f'is not close to a whole number of years. '
              f'Therefore seasonality might significantly affect the payback period estimate...!')
    annual_savings = savings / n_years_with_savings_simulated
    payback_period = bess_price / annual_savings
    profit_after_10_years = annual_savings * 10 - bess_price

    stats = {ANNUAL_SAVINGS: annual_savings,
             PROFIT_AFTER_10_YEARS: profit_after_10_years,
             PAYBACK_PERIOD: payback_period,
             }
    return stats
