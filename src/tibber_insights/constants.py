from types import SimpleNamespace

# Units
EUR = "€"
KW = "kW"
KWH = "kWh"
EUR_KWH = f"{EUR}/{KWH}"


def quantity(label, unit):
    return SimpleNamespace(label=label, unit=unit)


# 2027 Netherlands rates
ENERGIEBELASTING = 0.09161  # €/kWh only when consuming
INKOOPVERGOEDING = 0.0242  # €/kWh only when consuming
VAT_RATE = 0.21  # 21% BTW

EFFICIENCY = 0.90  # Round-trip

# Column Names / Plot Labels
net_household = quantity("Net Household", KW)
battery_charge = quantity("Charge", KW)
battery_discharge = quantity("Discharge", KW)
soc = quantity("SOC", KWH)
net_buy_price = quantity("Net buy price", EUR_KWH)
net_sell_price = quantity("Net sell price", EUR_KWH)
cost_no_battery = quantity("Cost w/o Battery", EUR)
cost_with_battery = quantity("Cost with Battery", EUR)

if __name__ == "__main__":
    print(f"{net_household.label} ({net_household.unit})")
    print(net_household)
    print(net_household.label)
    print(net_household.unit)
