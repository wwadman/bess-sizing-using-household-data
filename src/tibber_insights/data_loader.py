import glob
import pandas as pd
from .quantities import NET_HOUSEHOLD, NET_BUY_PRICE, NET_SELL_PRICE, TIME, \
    CONSUMPTION, PRODUCTION, UNIT_PRICE, CONSUMPTION_UNIT_PRICE_EUR, PRODUCTION_UNIT_PRICE_EUR, EXPECTED_CONSUMPTION, \
    EXPECTED_PRODUCTION, CONSUMPTION_COST_EUR, PRODUCTION_PROFIT_EUR

ENERGIEBELASTING = 0.09161  # €/kWh only when consuming
INKOOPVERGOEDING = 0.0242  # €/kWh only when consuming
VAT_RATE = 0.21  # 21% BTW

def load_monthly_files(pattern="csv/data-*.csv"):
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matched {pattern}")

    dfs = []
    for path in files:
        df = pd.read_csv(path)
        # df["source_file"] = os.path.basename(path)  # Only needed for debugging
        dfs.append(df)

    df = pd.concat(dfs, ignore_index=True)

    df.rename(columns={
        "hour_starts_at": TIME,
        "consumption_kwh": CONSUMPTION,
        "production_kwh": PRODUCTION,
        "consumption_unit_price_eur": CONSUMPTION_UNIT_PRICE_EUR,
        "production_unit_price_eur": PRODUCTION_UNIT_PRICE_EUR,
        "consumption_cost_eur": CONSUMPTION_COST_EUR,
        "production_profit_eur": PRODUCTION_PROFIT_EUR
        }, inplace=True)

    df[TIME] = pd.to_datetime(df[TIME], utc=True).dt.tz_convert("Europe/Amsterdam")
    df = df.sort_values(TIME).reset_index(drop=True)
    df = df[df[TIME] < '2026-04-23']  # Just to remove last, incomplete day
    assert not df.isna().any().any(), 'Data is not complete!'

    check_hour_coverage(df)

    df[NET_HOUSEHOLD] = df[CONSUMPTION] - df[PRODUCTION]
    df = df.drop_duplicates(subset=[TIME]).sort_values(TIME)

    df = clean_unit_prices(df)

    df = add_expected_consumption_production(df)

    # Focus all analysis on the very last 365 * 24 hours
    recent_hours = sorted(df[TIME].unique())[-365 * 24:]
    recent_hours = sorted(df[TIME].unique())[-300 * 24: -250 * 24]  # for debugging
    df = df[df[TIME].isin(recent_hours)].copy()

    return df


def check_hour_coverage(df):
    # -- consumption/production breakdown -------------------------------------
    some_consumption = df[CONSUMPTION] > 0
    no_consumption   = df[CONSUMPTION] == 0
    some_production  = df[PRODUCTION] > 0
    no_production    = df[PRODUCTION] == 0

    all_covered = (
          len(df[some_consumption & some_production])
        + len(df[some_consumption &   no_production])
        + len(df[  no_consumption &   no_production])
        + len(df[  no_consumption & some_production])
    ) == len(df)
    assert all_covered, "Not all hours are covered!"

def clean_unit_prices(df):
    """Calculate net price based on unit price and side (buy/sell).

    Args:
        df (pd.DataFrame): DataFrame containing unit prices.

    Returns:
        pd.Series: Net price series.

    Note:
    Until start of 2026 Tibber df[CONSUMPTION_UNIT_PRICE_EUR] == df[PRODUCTION_UNIT_PRICE_EUR]
    From start of 2026 Tibber df[CONSUMPTION_UNIT_PRICE_EUR] == df[PRODUCTION_UNIT_PRICE_EUR] + INKOOPVERGOEDING
    This is super confusing, since we want to mimic 2027 onwards, which has IV for consumption only,
    so we will use only the PRODUCTION_UNIT_PRICE_EUR and add the IV (and EB and BTW) to get the consumption_unit_price_eur_net
    """
    df[UNIT_PRICE] = df[PRODUCTION_UNIT_PRICE_EUR]
    df[NET_BUY_PRICE] = calculate_net_price(df[UNIT_PRICE], 'buy')
    df[NET_SELL_PRICE] = calculate_net_price(df[UNIT_PRICE], 'sell')
    df.drop(columns=[CONSUMPTION_UNIT_PRICE_EUR, PRODUCTION_UNIT_PRICE_EUR, UNIT_PRICE], inplace=True)

    return df


def calculate_net_price(price_per_unit, buy_or_sell):
    """Calculates net buy or sell price including VAT."""
    assert buy_or_sell in ['buy', 'sell'], f"Invalid buy_or_sell value: {buy_or_sell}. Must be 'buy' or 'sell'."
    if buy_or_sell == 'buy':
        price_per_unit = price_per_unit + ENERGIEBELASTING + INKOOPVERGOEDING
    return price_per_unit * (1 + VAT_RATE)

def add_expected_consumption_production(df):
    """Calculate expected consumption and production as rolling averages of the past 4 weeks
    (same hour of the day and day of the week)
    """
    n_weeks_to_look_back = 4
    look_back_hours_for_rolling_mean = [24 * 7 * (i + 1) for i in range(n_weeks_to_look_back)]
    for col, exp_col in [(CONSUMPTION, EXPECTED_CONSUMPTION), (PRODUCTION, EXPECTED_PRODUCTION)]:
        df[exp_col] = df[col].shift(look_back_hours_for_rolling_mean).mean(axis=1)

    return df