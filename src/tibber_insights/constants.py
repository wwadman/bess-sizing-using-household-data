from itertools import product
from types import SimpleNamespace

# Units
EUR = "€"
KW = "kW"
KWH = "kWh"
EUR_KWH = f"{EUR}/{KWH}"


class Quantity(str):
    def __new__(cls, label, unit):
        obj = super().__new__(cls, label)
        obj.unit = unit
        return obj

    def __reduce__(self):
        return (self.__class__, (str(self), self.unit))


# 2027 Netherlands rates
ENERGIEBELASTING = 0.09161  # €/kWh only when consuming
INKOOPVERGOEDING = 0.0242  # €/kWh only when consuming
VAT_RATE = 0.21  # 21% BTW

EFFICIENCY = 0.90  # Round-trip

# Column Names / Plot Labels
time = "Timestamp"  # Does not have a unit so it is not a Quantity
consumption = Quantity("Consumption", KWH)
production = Quantity("Production", KWH)
net_household = Quantity("Net Household", KWH)
charge = Quantity("Charge", KWH)
discharge = Quantity("Discharge", KWH)
soc = Quantity("SOC", KWH)
net_buy_price = Quantity("Net buy price", EUR_KWH)
net_sell_price = Quantity("Net sell price", EUR_KWH)
cost_wo_battery = Quantity("Cost w/o Battery", EUR)
cost_with_battery = Quantity("Cost with Battery", EUR)

if __name__ == "__main__":
    print(f"{net_household.l} ({net_household.unit})")
    print(net_household)
    print(net_household.l)
    print(net_household.unit)
