# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pandas as pd

from src.batteries.bess_candidates import bess_candidates
from src.data_loader import load_monthly_files
from src.billing import forecast_2027_bill
from src.simulation import simulate, compute_savings_stats
from src.visualization import plot_interactive_bess_behavior, OUTPUT_DIR

def main(csv_folder: str):
    pd.set_option(
        'display.max_rows', 15,
        'display.max_columns', 20,
        'display.max_colwidth', 100,
        'display.width', 200
    )

    # -- Load data -----------------------------------------------------------------
    df = load_monthly_files(f"{csv_folder}/data-*.csv*")
    df.to_csv(f"{csv_folder}/tibber_all_months_merged.csv", index=False)

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
    pd.to_pickle(bess_behavior, OUTPUT_DIR + "/bess_behavior_last_run.pkl")
    pd.to_pickle(savings_stats, OUTPUT_DIR + "/savings_stats_last_run.pkl")

    plot_interactive_bess_behavior(bess_behavior, savings_stats, days=10)

if __name__ == "__main__":
    # Print simulation start time
    print(f"Simulation started at {pd.Timestamp.now()}")
    main(csv_folder="example_household_load_profile_csvs")
    # main(csv_folder="your_household_load_profile_csvs") # Point to your own households csv
    # Print simulation end time
    print(f"Simulation ended at {pd.Timestamp.now()}")
