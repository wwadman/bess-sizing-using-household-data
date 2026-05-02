import pandas as pd
from .constants import ENERGIEBELASTING, INKOOPVERGOEDING, VAT_RATE

def calculate_gross_buy_price(unit_price_eur):
    """Calculates gross buy price including taxes and VAT."""
    return (unit_price_eur + ENERGIEBELASTING + INKOOPVERGOEDING) * (1 + VAT_RATE)

def calculate_gross_sell_price(unit_price_eur):
    """Calculates gross sell price including VAT."""
    return unit_price_eur * (1 + VAT_RATE)

def forecast_2027_bill(df):
    """Calculate 2027 bill using last 365 days profile."""
    df = df.copy()

    df['date'] = df['hour_starts_at'].dt.date
    recent_days = sorted(df['date'].unique())[-365:]
    profile_df = df[df['date'].isin(recent_days)].copy()

    annual_consumed = profile_df['consumption_kwh'].sum()
    annual_exported = profile_df['production_kwh'].sum()
    
    cons_gross = (calculate_gross_buy_price(profile_df['consumption_unit_price_eur']) * profile_df['consumption_kwh']).sum()
    export_gross = (calculate_gross_sell_price(profile_df['production_unit_price_eur']) * profile_df['production_kwh']).sum()

    net_bill = cons_gross - export_gross

    forecast = {
        'period_days': len(recent_days),
        'annual_consumed_kwh': annual_consumed,
        'annual_exported_kwh': annual_exported,
        'cons_gross_eur': cons_gross,
        'export_gross_eur': export_gross,
        'net_bill_2027_eur': net_bill,
        'monthly_eur': net_bill / 12,
    }

    header_width = 50
    print("\n" + "╔" + "═" * (header_width - 2) + "╗")
    print(f"║ {'2027 ENERGY BILL FORECAST (no battery)':^{header_width - 4}} ║")
    print("╠" + "═" * (header_width - 2) + "╣")
    print(f"║ Period: {forecast['period_days']:3d} days profile extrapolated to year  ║")
    print("╟" + "─" * (header_width - 2) + "╢")

    print(f"║ CONSUMPTION                                    ║")
    print(f"║   Annual volume:    {forecast['annual_consumed_kwh']:8.0f} kWh               ║")
    print(f"║   Annual cost:      € {forecast['cons_gross_eur']:10.2f}               ║")
    print(f"║                                                ║")
    print(f"║ EXPORT                                         ║")
    print(f"║   Annual volume:    {forecast['annual_exported_kwh']:8.0f} kWh               ║")
    print(f"║   Annual revenue:   € {forecast['export_gross_eur']:10.2f}               ║")
    print("╠" + "═" * (header_width - 2) + "╣")
    print(f"║ NET ANNUAL BILL:    € {forecast['net_bill_2027_eur']:10.2f}               ║")
    print(f"║ Monthly average:    € {forecast['monthly_eur']:10.2f}               ║")
    print("╚" + "═" * (header_width - 2) + "╝")

    return forecast