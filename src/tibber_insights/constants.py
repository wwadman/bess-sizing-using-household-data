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

# Column names of original dataframe
time = "Timestamp"  # Does not have a unit, so it is not a Quantity
consumption = Quantity("Consumption", KWH)
consumption_unit_price_eur = Quantity("Consumption unit price", EUR_KWH)
consumption_cost_eur = Quantity("Consumption cost", EUR)
production = Quantity("Production", KWH)
production_unit_price_eur = Quantity("Production unit price", EUR_KWH)
production_profit_eur = Quantity("Production profit", EUR)
unit_price = Quantity("Unit price", EUR_KWH)

# Names of columns introduced when executing strategies
expected_consumption = Quantity("Expected consumption", KWH)
expected_production = Quantity("Expected production", KWH)
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
