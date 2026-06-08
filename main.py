import pandas as pd

from tibber_insights.batteries.bess_candidates import bess_candidates
from tibber_insights.data_loader import load_monthly_files
from tibber_insights.quantities import NET_HOUSEHOLD, SOC, EUR, CAPACITY, CHARGING_RATE, BESS, ANNUAL_SAVINGS, \
    PAYBACK_PERIOD, PROFIT_AFTER_10_YEARS, RTE
from tibber_insights.billing import forecast_2027_bill
from tibber_insights.simulation import simulate, compute_savings_stats
from tibber_insights.visualization import plot_bess_savings_surface, plot_interactive_bess_behavior


PLOT = False
DEBUG = True

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
        print(bess, " | ", bess.properties_to_long_string(), " | ", bess.strategy)

    # -- BESS simulation --------------------------------------------------------
    sim_results = []
    bess_behavior = {}
    savings_stats = {}
    for bess in bess_candidates:
        sim_df = simulate(sim_df=df, bess=bess, strategy_fn=bess.strategy)

        bess_behavior[bess] = sim_df
        stats = compute_savings_stats(sim_df, bess.price)
        savings_stats[bess] = stats

        sim_results.append({
            BESS: bess,
            **stats,
        })

    plot_interactive_bess_behavior(bess_behavior, savings_stats, days=10)

    results_df = pd.DataFrame(sim_results)

    print("\n" + "╔" + "═" * 88 + "╗")
    print(f"║ {'BESS SIMULATION RESULTS (2027)':^86} ║")
    print("╠" + "═" * 88 + "╣")

    display_df = results_df.sort_values(ANNUAL_SAVINGS, ascending=False)
    display_df[CAPACITY] = display_df[BESS].apply(lambda b: b.capacity)
    display_df[CHARGING_RATE] = display_df[BESS].apply(lambda b: b.charging_rate)
    display_df[RTE] = display_df[BESS].apply(lambda b: b.rte)
    display_df[BESS] = display_df[BESS].apply(lambda b: b.name)


    display_df = display_df[[BESS, CAPACITY, CHARGING_RATE, RTE,
                             ANNUAL_SAVINGS, PAYBACK_PERIOD, PROFIT_AFTER_10_YEARS]]

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
        best_bess = results_df.loc[results_df[ANNUAL_SAVINGS].idxmax()]
        
        # -- Surface plots ------------------------------------------------
        if PLOT:
            rates = sorted(list(set(res[BESS].charging_rate for res in sim_results)))
            capacities = sorted(list(set(res[BESS].capacity for res in sim_results)))
            
            plot_df = results_df.copy()
            plot_df[CAPACITY] = plot_df[BESS].apply(lambda b: b.capacity)
            plot_df[CHARGING_RATE] = plot_df[BESS].apply(lambda b: b.charging_rate)
            plot_bess_savings_surface(plot_df, rates, capacities)

if __name__ == "__main__":
    # Print simulation start time
    print(f"Simulation started at {pd.Timestamp.now()}")
    main()
    # Print simulation end time
    print(f"Simulation ended at {pd.Timestamp.now()}")
