import pandas as pd

from tibber_insights.batteries.bess_candidates import bess_candidates
from tibber_insights.data_loader import load_monthly_files
from tibber_insights.quantities import NET_HOUSEHOLD, SOC, EUR, CAPACITY, CHARGING_RATE, STRATEGY, BESS
from tibber_insights.billing import forecast_2027_bill
from tibber_insights.simulation import run_bess_simulation
from tibber_insights.strategies import strategy_daily_lp
from tibber_insights.visualization import plot_bess_savings_surface, plot_interactive_bess_behavior


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
    baseline_bill = forecast['net_bill_2027_eur']

    print("We will run the bess simulation with the following candidate besses:")
    for bess in bess_candidates:
        print(bess, " --- ", bess.properties_to_long_string())

    strategies = {"Daily cost optimization": strategy_daily_lp}

    # -- BESS simulation --------------------------------------------------------
    sim_results = []
    bess_behavior = {}
    for bess in bess_candidates:
        bess_behavior[bess] = {}
        for strategy_name, strategy_fn in strategies.items():
            sim_df = run_bess_simulation(sim_df=df, bess=bess, strategy_fn=strategy_fn)
            savings = sim_df.Savings.sum()

            if SANITY_CHECK:
                bess_behavior[bess][strategy_name] = sim_df

            sim_results.append({
                BESS: bess,
                STRATEGY: strategy_name,
                'annual_savings_eur': savings,
                'net_bill_eur': baseline_bill - savings,
                'savings_pct': savings / baseline_bill * 100,
            })

    plot_interactive_bess_behavior(bess_behavior, strategies, days=10)

    results_df = pd.DataFrame(sim_results)

    print("\n" + "╔" + "═" * 88 + "╗")
    print(f"║ {'BESS SIMULATION RESULTS (2027)':^86} ║")
    print("╠" + "═" * 88 + "╣")

    display_df = results_df.sort_values([STRATEGY, 'annual_savings_eur'], ascending=[True, False])
    display_df[CAPACITY] = display_df[BESS].apply(lambda b: b.capacity)
    display_df[CHARGING_RATE] = display_df[BESS].apply(lambda b: b.charging_rate)
    display_df[BESS] = display_df[BESS].apply(lambda b: b.name)

    display_df = display_df[[BESS, STRATEGY, CAPACITY, CHARGING_RATE, 'annual_savings_eur', 'net_bill_eur', 'savings_pct']]

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
        best_by_strategy[CAPACITY] = best_by_strategy[BESS].apply(lambda b: b.capacity)
        best_by_strategy[CHARGING_RATE] = best_by_strategy[BESS].apply(lambda b: b.charging_rate)

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
            rates = sorted(list(set(res[BESS].charging_rate for res in sim_results)))
            capacities = sorted(list(set(res[BESS].capacity for res in sim_results)))
            for strategy_name in strategies.keys():
                # We need to adapt results_df for plot_bess_savings_surface if it expects CAPACITY/CHARGING_RATE columns
                plot_df = results_df.copy()
                plot_df[CAPACITY] = plot_df[BESS].apply(lambda b: b.capacity)
                plot_df[CHARGING_RATE] = plot_df[BESS].apply(lambda b: b.charging_rate)
                plot_bess_savings_surface(plot_df, strategy_name, rates, capacities)

if __name__ == "__main__":
    # Print simulation start time
    print(f"Simulation started at {pd.Timestamp.now()}")
    main()
    # Print simulation end time
    print(f"Simulation ended at {pd.Timestamp.now()}")
