# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from src.quantities import EUR, KWH, NET_BUY_PRICE, NET_SELL_PRICE, CONSUMPTION, PRODUCTION


def forecast_2027_bill(df):
    """Calculate the 2027 bill using the last 365-day profile."""
    annual_consumed = df[CONSUMPTION].sum()
    annual_exported = df[PRODUCTION].sum()

    cons_net = (df[NET_BUY_PRICE] * df[CONSUMPTION]).sum()
    export_net = (df[NET_SELL_PRICE] * df[PRODUCTION]).sum()

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
    print(f"║ {'2027 ENERGY BILL FORECAST (no bess)':^{header_width - 4}} ║")
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