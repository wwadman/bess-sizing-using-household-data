import glob
import pandas as pd
from .constants import net_household, ENERGIEBELASTING, INKOOPVERGOEDING, VAT_RATE, net_buy_price, net_sell_price, time, \
    consumption, production


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
        "hour_starts_at": time,
        "consumption_kwh": consumption,
        "production_kwh": production
        }, inplace=True)

    df[time] = pd.to_datetime(df[time], utc=True).dt.tz_convert("Europe/Amsterdam")
    df = df.sort_values(time).reset_index(drop=True)
    df = df[df[time] < '2026-04-23']  # Just to remove last, incomplete day
    assert not df.isna().any().any(), 'Data is not complete!'


    check_hour_coverage(df)

    df[net_household] = df[consumption] - df[production]
    df = df.drop_duplicates(subset=[time]).sort_values(time)

    df = clean_unit_prices(df, net_buy_price, net_sell_price)

    df = add_expected_consumption_production(df)

    # Focus all analysis on the very last 365 * 24 hours
    recent_hours = sorted(df[time].unique())[-365 * 24:]
    df = df[df[time].isin(recent_hours)].copy()

    return df


def check_hour_coverage(df):
    # -- consumption/production breakdown -------------------------------------
    some_consumption = df[consumption] > 0
    no_consumption   = df[consumption] == 0
    some_production  = df[production] > 0
    no_production    = df[production] == 0

    all_covered = (
          len(df[some_consumption & some_production])
        + len(df[some_consumption &   no_production])
        + len(df[  no_consumption &   no_production])
        + len(df[  no_consumption & some_production])
    ) == len(df)
    assert all_covered, "Not all hours are covered!"

def clean_unit_prices(df, net_buy_price, net_sell_price):
    """Calculate net price based on unit price and side (buy/sell).

    Args:
        df (pd.DataFrame): DataFrame containing unit prices.
        net_buy_price (Price): Price object for net buy price.
        net_sell_price (Price): Price object for net sell price.

    Returns:
        pd.Series: Net price series.

    Note:
    Until start of 2026 Tibber df.consumption_unit_price_eur == df.production_unit_price_eur
    From start of 2026 Tibber df.consumption_unit_price_eur == df.production_unit_price_eur + INKOOPVERGOEDING
    This is superconfusing, since we want to mimic 2027 onwards, which has IV for consumption only,
    so we will use only the production_unit_price_eur and add the IV (and EB and BTW) to get the consumption_unit_price_eur_net
    """
    df['unit_price'] = df.production_unit_price_eur
    df[net_buy_price] = calculate_net_price(df['unit_price'], 'buy')
    df[net_sell_price] = calculate_net_price(df['unit_price'], 'sell')
    df.drop(columns=['consumption_unit_price_eur', 'production_unit_price_eur', 'unit_price'], inplace=True)

    return df


def calculate_net_price(unit_price, buy_or_sell):
    """Calculates net buy or sell price including VAT."""
    assert buy_or_sell in ['buy', 'sell'], f"Invalid buy_or_sell value: {buy_or_sell}. Must be 'buy' or 'sell'."
    if buy_or_sell == 'buy':
        unit_price = unit_price + ENERGIEBELASTING + INKOOPVERGOEDING
    return unit_price * (1 + VAT_RATE)

def add_expected_consumption_production(df):
    """Calculate expected consumption and production as rolling averages of the past 4 weeks
    (same hour of the day and day of the week)
    """
    n_weeks_to_look_back = 4
    look_back_hours_for_rolling_mean = [24 * 7 * (i + 1) for i in range(n_weeks_to_look_back)]
    for col, exp_col in [(consumption, 'exp_cons'), (production, 'exp_prod')]:
        df[exp_col] = df[col].shift(look_back_hours_for_rolling_mean).mean(axis=1)

    return df