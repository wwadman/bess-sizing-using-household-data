import pandas as pd

from tibber_insights.batteries.bess_candidates import bess_candidates
from tibber_insights.data_loader import load_monthly_files
from tibber_insights.billing import forecast_2027_bill
from tibber_insights.simulation import simulate, compute_savings_stats
from tibber_insights.visualization import plot_interactive_bess_behavior

USE_SAVED_DATA = False

def main():
    pd.set_option(
        'display.max_rows', 15,
        'display.max_columns', 20,
        'display.max_colwidth', 100,
        'display.width', 200
    )

    if USE_SAVED_DATA:
        bess_behavior = pd.read_pickle("bess_behavior.pkl")
        savings_stats = pd.read_pickle("savings_stats.pkl")
    else:
        # -- Load data -----------------------------------------------------------------
        df = load_monthly_files("csv/data-*.csv")
        df.to_csv("tibber_all_months_merged.csv", index=False)

        # -- 2027 bill forecast --------------------------------------------------------
        forecast = forecast_2027_bill(df)
        baseline_bill = forecast['net_bill_2027_eur']

        print("We will run the bess simulation with the following candidate besses:")
        for bess in bess_candidates:
            print(bess, " | ", bess.properties_to_long_string(), " | ", bess.strategy.__name__)

        # -- BESS simulation --------------------------------------------------------
        bess_behavior = {}
        savings_stats = {}
        for bess in bess_candidates:
            sim_df = simulate(sim_df=df, bess=bess, strategy_fn=bess.strategy)
            bess_behavior[bess] = sim_df
            savings_stats[bess] = compute_savings_stats(sim_df, bess.price)

        # save results
        pd.to_pickle(bess_behavior, "bess_behavior.pkl")
        pd.to_pickle(savings_stats, "savings_stats.pkl")

    plot_interactive_bess_behavior(bess_behavior, savings_stats, days=10)

if __name__ == "__main__":
    # Print simulation start time
    print(f"Simulation started at {pd.Timestamp.now()}")
    main()
    # Print simulation end time
    print(f"Simulation ended at {pd.Timestamp.now()}")
