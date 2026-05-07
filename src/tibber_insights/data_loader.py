import glob
import os
import pandas as pd

def load_monthly_files(pattern="csv/data-*.csv"):
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matched {pattern}")

    dfs = []
    for path in files:
        df = pd.read_csv(path)
        df["source_file"] = os.path.basename(path)
        df["hour_starts_at"] = pd.to_datetime(df["hour_starts_at"], utc=True).dt.tz_convert("Europe/Amsterdam")
        dfs.append(df)

    df = pd.concat(dfs, ignore_index=True)
    df = df.sort_values("hour_starts_at").reset_index(drop=True)

    df = df[df['hour_starts_at'] < '2026-04-23']
    assert not df.isna().any().any(), 'Assumption of complete data does not hold!'

    # -- consumption/production breakdown -------------------------------------
    some_consumption = df.consumption_kwh > 0
    no_consumption   = df.consumption_kwh == 0
    some_production  = df.production_kwh > 0
    no_production    = df.production_kwh == 0

    all_covered = (
          len(df[some_consumption & some_production])
        + len(df[some_consumption &   no_production])
        + len(df[  no_consumption &   no_production])
        + len(df[  no_consumption & some_production])
    ) == len(df)
    print("All hours covered:", all_covered)

    df['Net Household (kW)'] = df['consumption_kwh'] - df['production_kwh']

    return df
