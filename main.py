import pandas as pd
from tibber_insights.data_loader import load_monthly_files
from tibber_insights.constants import NET_HOUSEHOLD, SOC, EUR, CAPACITY, CHARGING_RATE, STRATEGY, BATTERY
from tibber_insights.battery import Battery
from tibber_insights.billing import forecast_2027_bill
from tibber_insights.simulation import run_battery_simulation
from tibber_insights.strategies import strategy_daily_lp
from tibber_insights.visualization import plot_battery_savings_surface, plot_interactive_battery_behavior


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
    # capacities = [5, 10, 20]
    # rates = [0.8, 1.2, 2.4, 4]

    batteries = [
        Battery('Marstek Venus A', capacity=10.6, charging_rate=1.2, rte=0.84, price=2575),
        Battery('Marstek Venus A small', capacity=2.1, charging_rate=1.2, rte=0.84, price=650),
    ]

    baseline_bill = forecast['net_bill_2027_eur']

    strategies = {"Daily linear optimization": strategy_daily_lp}

    sim_results = []
    battery_behavior = {}

    for battery in batteries:
        battery_behavior[battery] = {}
        for strategy_name, strategy_fn in strategies.items():
            sim_df = run_battery_simulation(sim_df=df, battery=battery, strategy_fn=strategy_fn)
            savings = sim_df.Savings.sum()

            if SANITY_CHECK:
                battery_behavior[battery][strategy_name] = sim_df

            sim_results.append({
                BATTERY: battery,
                STRATEGY: strategy_name,
                'annual_savings_eur': savings,
                'net_bill_eur': baseline_bill - savings,
                'savings_pct': savings / baseline_bill * 100,
            })

    plot_interactive_battery_behavior(battery_behavior, days=10)

    results_df = pd.DataFrame(sim_results)

    print("\n" + "╔" + "═" * 88 + "╗")
    print(f"║ {'BATTERY SIMULATION RESULTS (2027)':^86} ║")
    print("╠" + "═" * 88 + "╣")

    display_df = results_df.sort_values([STRATEGY, 'annual_savings_eur'], ascending=[True, False])
    display_df[CAPACITY] = display_df[BATTERY].apply(lambda b: b.capacity)
    display_df[CHARGING_RATE] = display_df[BATTERY].apply(lambda b: b.charging_rate)
    display_df[BATTERY] = display_df[BATTERY].apply(lambda b: b.name)

    display_df = display_df[[BATTERY, STRATEGY, CAPACITY, CHARGING_RATE, 'annual_savings_eur', 'net_bill_eur', 'savings_pct']]

    # Rename columns for prettier display
    # display_df.columns = ['Strategy', f'Cap ({SOC.unit})', f'Rate ({NET_HOUSEHOLD.unit})', f'Savings ({EUR})', f'Net Bill ({EUR})', 'Savings %']

    sim_table = display_df.to_string(index=False, justify='center', formatters={
        f'Cap ({SOC.unit})': '{:.1f}'.format,
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
            results_df.loc[results_df.groupby(STRATEGY)['annual_savings_eur'].idxmax()]
            .sort_values('annual_savings_eur', ascending=False)
        )
        best_by_strategy[CAPACITY] = best_by_strategy[BATTERY].apply(lambda b: b.capacity)
        best_by_strategy[CHARGING_RATE] = best_by_strategy[BATTERY].apply(lambda b: b.charging_rate)

        print("\n" + "╔" + "═" * 88 + "╗")
        print(f"║ {'🏆 BEST CONFIGURATION PER STRATEGY':^86}║")
        print("╠" + "═" * 88 + "╣")

        best_display = best_by_strategy[[STRATEGY, CAPACITY, CHARGING_RATE, 'annual_savings_eur', 'savings_pct', 'net_bill_eur']]
        best_display.columns = ['Strategy', f'Cap ({SOC.unit})', f'Rate ({NET_HOUSEHOLD.unit})', f'Savings ({EUR})', 'Savings %', f'Net Bill ({EUR})']

        best_table = best_display.to_string(index=False, justify='center', formatters={
            f'Cap ({SOC.unit})': '{:.1f}'.format,
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
            rates = sorted(list(set(res[BATTERY].charging_rate for res in sim_results)))
            capacities = sorted(list(set(res[BATTERY].capacity for res in sim_results)))
            for strategy_name in strategies.keys():
                # We need to adapt results_df for plot_battery_savings_surface if it expects CAPACITY/CHARGING_RATE columns
                plot_df = results_df.copy()
                plot_df[CAPACITY] = plot_df[BATTERY].apply(lambda b: b.capacity)
                plot_df[CHARGING_RATE] = plot_df[BATTERY].apply(lambda b: b.charging_rate)
                plot_battery_savings_surface(plot_df, strategy_name, rates, capacities)

if __name__ == "__main__":
    main()
