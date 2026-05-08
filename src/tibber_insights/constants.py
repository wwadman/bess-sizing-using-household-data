import pint
from types import SimpleNamespace

# Initialize Unit Registry
ureg = pint.UnitRegistry()

# Units
EUR = "€"
KW = ureg.kW
KWH = ureg.kWh
EUR_KWH = f"{EUR}/{KWH:~}"

def Quantity(label, unit):
    return SimpleNamespace(label=label, unit=unit)

# 2027 Netherlands rates
ENERGIEBELASTING = 0.09161  # €/kWh only when consuming
INKOOPVERGOEDING = 0.0242   # €/kWh only when consuming
VAT_RATE = 0.21             # 21% BTW

EFFICIENCY = 0.90  # Round-trip

# Column Names / Plot Labels
net_household = Quantity("Net Household", KW)
battery_charge = Quantity("Battery Charge", KW)
battery_discharge = Quantity("Battery Discharge", KW)
soc = Quantity("SOC", KWH)
net_buy_price = Quantity("Net buy price: incl. EB, IV and VAT", EUR_KWH)
net_sell_price = Quantity("Net sell price: incl. VAT", EUR_KWH)
cost_no_battery = Quantity("Cost w/o Battery", EUR)
cost_with_battery = Quantity("Cost with Battery", EUR)

if __name__ == "__main__":
    print(f"{net_household.label} ({net_household.unit})")
    print(net_household)
    print(net_household.label)
    print(net_household.unit)