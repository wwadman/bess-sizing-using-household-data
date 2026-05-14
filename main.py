import pandas as pd
import plotly.express as px
from itertools import product
from tibber_insights.data_loader import load_monthly_files
from tibber_insights.constants import (
    net_household, battery_charge, battery_discharge,
    soc, net_buy_price, net_sell_price, cost_no_battery, cost_with_battery,
    EUR, KW, KWH, EUR_KWH
)
from tibber_insights.billing import forecast_2027_bill, calculate_net_price
from tibber_insights.simulation import (
    run_battery_simulation,
    strategy_arbitrage,
    strategy_optimal_mpc
)
from tibber_insights.visualization import (
    plot_battery_savings_surface,
    plot_battery_behavior
)

PLOT = False
SANITY_CHECK = True

def main():
    pd.set_option('display.max_rows', 15)
    pd.set_option('display.max_columns', 20)

    # set max number chars per row when pandas is printing
    pd.set_option('display.max_colwidth', 100)

    # -- Load data -----------------------------------------------------------------
    df = load_monthly_files("csv/data-*.csv")
    df = df.drop_duplicates(subset=['hour_starts_at']).sort_values('hour_starts_at')

    # Clean unit prices
    # Until start of 2026 Tibber df.consumption_unit_price_eur == df.production_unit_price_eur
    # From start of 2026 Tibber df.consumption_unit_price_eur == df.production_unit_price_eur + INKOOPVERGOEDING
    # This is super confusing, since we want to mimic 2027 onwards, which has IV for consumption only
    # So we will use only the production_unit_price_eur and add the IV (and EB and BTW) to obtain the consumption_unit_price_eur_net
    df['unit_price'] = df.production_unit_price_eur
    df[net_buy_price.label] = calculate_net_price(df['unit_price'], 'buy')
    df[net_sell_price.label] = calculate_net_price(df['unit_price'], 'sell')
    df.drop(columns=['consumption_unit_price_eur', 'production_unit_price_eur', 'unit_price'], inplace=True)

    # Focus all analysis on the very last 365 * 24 hours
    recent_hours = sorted(df['hour_starts_at'].unique())[-365 * 24:]
    df = df[df['hour_starts_at'].isin(recent_hours)].copy()

    # Calculate expected consumption and production as rolling averages of the past 4 weeks
    # (same hour of the day and day of the week)
    n_weeks_to_look_back = 4
    look_back_hours_for_rolling_mean = [24 * 7 * (i + 1) for i in range(n_weeks_to_look_back)]
    for col, exp_col in [('consumption_kwh', 'exp_cons'), ('production_kwh', 'exp_prod')]:
        df[exp_col] = df[col].shift(look_back_hours_for_rolling_mean).mean(1)

    df.to_csv("tibber_all_months_merged.csv", index=False)


    if PLOT:
        fig = px.line(df, x="hour_starts_at", y=net_household.label)
        fig.update_traces(hovertemplate=f"{net_household.label}: %{{y:.2f}}<extra></extra>")
        fig.update_layout(hovermode='x')
        fig.show()

    # -- 2027 bill forecast --------------------------------------------------------
    forecast = forecast_2027_bill(df)

    # -- Battery simulation --------------------------------------------------------
    capacities = [0, 20]   # [2, 5, 10, 20]
    rates = [2.4]       # [0.8, 1.2, 1.5, 2.4]

    baseline_bill = forecast['net_bill_2027_eur']

    strategies = {
        # "arbitrage": strategy_arbitrage,
        "optimal_mpc": strategy_optimal_mpc,
    }

    sim_results = []

    for capacity, rate in product(capacities, rates):
        for strategy_name, strategy_fn in strategies.items():
            savings, sim_df = run_battery_simulation(
                sim_df=df,
                capacity_kwh=capacity,
                rate_kw=rate,
                strategy_fn=strategy_fn,
            )

            if SANITY_CHECK and capacity == 20 and strategy_name == "optimal_mpc":
                print(f"\n--- Generating sanity check plot for {strategy_name} (20kWh) ---")
                plot_battery_behavior(sim_df)

            sim_results.append({
                'strategy': strategy_name,
                'capacity_kwh': capacity,
                'rate_kw': rate,
                'annual_savings_eur': savings,
                'net_bill_eur': baseline_bill - savings,
                'savings_pct': savings / baseline_bill * 100,
            })

    results_df = pd.DataFrame(sim_results)

    print("\n" + "╔" + "═" * 88 + "╗")
    print(f"║ {'BATTERY SIMULATION RESULTS (2027)':^86} ║")
    print("╠" + "═" * 88 + "╣")

    display_df = results_df.sort_values(
        ['strategy', 'annual_savings_eur'],
        ascending=[True, False],
    )[['strategy', 'capacity_kwh', 'rate_kw', 'annual_savings_eur', 'net_bill_eur', 'savings_pct']]

    # Rename columns for prettier display
    display_df.columns = ['Strategy', f'Cap ({soc.unit})', f'Rate ({net_household.unit})', f'Savings ({EUR})', f'Net Bill ({EUR})', 'Savings %']

    sim_table = display_df.to_string(index=False, justify='center', formatters={
        f'Cap ({soc.unit})': '{:.0f}'.format,
        f'Rate ({net_household.unit})': '{:.1f}'.format,
        f'Savings ({EUR})': '{:,.2f}'.format,
        f'Net Bill ({EUR})': '{:,.2f}'.format,
        'Savings %': '{:.1f}%'.format,
    })
    for line in sim_table.split('\n'):
        print(f"║ {line:^86} ║")
    print("╚" + "═" * 88 + "╝")

    if not results_df.empty:
        best_by_strategy = (
            results_df.loc[results_df.groupby('strategy')['annual_savings_eur'].idxmax()]
            .sort_values('annual_savings_eur', ascending=False)
        )

        print("\n" + "╔" + "═" * 88 + "╗")
        print(f"║ {'🏆 BEST CONFIGURATION PER STRATEGY':^86}║")
        print("╠" + "═" * 88 + "╣")

        best_display = best_by_strategy[['strategy', 'capacity_kwh', 'rate_kw', 'annual_savings_eur', 'savings_pct', 'net_bill_eur']]
        best_display.columns = ['Strategy', f'Cap ({soc.unit})', f'Rate ({net_household.unit})', f'Savings ({EUR})', 'Savings %', f'Net Bill ({EUR})']

        best_table = best_display.to_string(index=False, justify='center', formatters={
            f'Cap ({soc.unit})': '{:.0f}'.format,
            f'Rate ({net_household.unit})': '{:.1f}'.format,
            f'Savings ({EUR})': '{:,.2f}'.format,
            f'Net Bill ({EUR})': '{:,.2f}'.format,
            'Savings %': '{:.1f}%'.format,
        })
        for line in best_table.split('\n'):
            print(f"║ {line:^86} ║")
        print("╚" + "═" * 88 + "╝")

        # -- Surface plots per strategy ------------------------------------------------
        if PLOT:
            for strategy_name in strategies.keys():
                plot_battery_savings_surface(results_df, strategy_name, rates, capacities)

if __name__ == "__main__":
    main()
