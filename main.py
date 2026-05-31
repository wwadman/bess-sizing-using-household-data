import pandas as pd
from itertools import product
from tibber_insights.data_loader import load_monthly_files
from tibber_insights.constants import NET_HOUSEHOLD, SOC, EUR
from tibber_insights.billing import forecast_2027_bill
from tibber_insights.simulation import run_battery_simulation
from tibber_insights.strategies import strategy_daily_lp
from tibber_insights.visualization import plot_battery_savings_surface, plot_battery_behavior


PLOT = False
SANITY_CHECK = True

def main():
    pd.set_option(
        'display.max_rows', 15,
        'display.max_columns', 20,
        'display.max_colwidth', 100,
        'display.width', 200
    )

    # -- Load data -----------------------------------------------------------------
    df = load_monthly_files("csv/data-*.csv")
    df.to_csv("tibber_all_months_merged.csv", index=False)

    # -- 2027 bill forecast --------------------------------------------------------
    forecast = forecast_2027_bill(df)

    # -- Battery simulation --------------------------------------------------------
    capacities = [2, 5, 10, 20]
    rates = [0.8, 1.2, 2.4, 4]
    # capacities = [20]
    # rates = [4]

    baseline_bill = forecast['net_bill_2027_eur']

    strategies = {
        # "arbitrage": strategy_arbitrage,
        # "optimal_mpc": strategy_optimal_mpc,
        # "optimal_mpc2": strategy_optimal_mpc2,
        "strategy_daily_lp": strategy_daily_lp,
    }

    sim_results = []

    for capacity, rate in product(capacities, rates):
        for strategy_name, strategy_fn in strategies.items():
            sim_df = run_battery_simulation(
                sim_df=df,
                capacity_kwh=capacity,
                max_rate_kw=rate,
                strategy_fn=strategy_fn,
            )
            savings = sim_df.Savings.sum()

            if SANITY_CHECK:
                plot_battery_behavior(sim_df, capacity, rate, strategy_name, days=10)

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
    display_df.columns = ['Strategy', f'Cap ({SOC.unit})', f'Rate ({NET_HOUSEHOLD.unit})', f'Savings ({EUR})', f'Net Bill ({EUR})', 'Savings %']

    sim_table = display_df.to_string(index=False, justify='center', formatters={
        f'Cap ({SOC.unit})': '{:.0f}'.format,
        f'Rate ({NET_HOUSEHOLD.unit})': '{:.1f}'.format,
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
        best_display.columns = ['Strategy', f'Cap ({SOC.unit})', f'Rate ({NET_HOUSEHOLD.unit})', f'Savings ({EUR})', 'Savings %', f'Net Bill ({EUR})']

        best_table = best_display.to_string(index=False, justify='center', formatters={
            f'Cap ({SOC.unit})': '{:.0f}'.format,
            f'Rate ({NET_HOUSEHOLD.unit})': '{:.1f}'.format,
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
