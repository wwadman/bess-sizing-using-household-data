from .constants import ENERGIEBELASTING, INKOOPVERGOEDING, VAT_RATE, EUR, KWH, net_buy_price, net_sell_price, \
    consumption, production


def forecast_2027_bill(df):
    """Calculate the 2027 bill using the last 365-day profile."""
    annual_consumed = df[consumption].sum()
    annual_exported = df[production].sum()

    cons_net = (df[net_buy_price] * df[consumption]).sum()
    export_net = (df[net_sell_price] * df[production]).sum()

    net_bill = cons_net - export_net

    forecast = {
        'period_days': len(df) // 24,
        'annual_consumed_kwh': annual_consumed,
        'annual_exported_kwh': annual_exported,
        'cons_net_eur': cons_net,
        'export_net_eur': export_net,
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
    print(f"║   Annual volume:    {forecast['annual_consumed_kwh']:8.0f} {KWH}               ║")
    print(f"║   Annual cost:      {EUR} {forecast['cons_net_eur']:10.2f}               ║")
    print(f"║                                                ║")
    print(f"║ EXPORT                                         ║")
    print(f"║   Annual volume:    {forecast['annual_exported_kwh']:8.0f} {KWH}               ║")
    print(f"║   Annual revenue:   {EUR} {forecast['export_net_eur']:10.2f}               ║")
    print("╠" + "═" * (header_width - 2) + "╣")
    print(f"║ NET ANNUAL BILL:    {EUR} {forecast['net_bill_2027_eur']:10.2f}               ║")
    print(f"║ Monthly average:    {EUR} {forecast['monthly_eur']:10.2f}               ║")
    print("╚" + "═" * (header_width - 2) + "╝")

    return forecast