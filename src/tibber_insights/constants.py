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

# Round-trip efficiency is EFFICIENCY_CHARGING * EFFICIENCY_DISCHARGING:
EFFICIENCY_CHARGING = EFFICIENCY_DISCHARGING = 0.9

# Column names of original dataframe
TIME = "Timestamp"  # Does not have a unit, so it is not a Quantity
CONSUMPTION = Quantity("Consumption", KWH)
CONSUMPTION_UNIT_PRICE_EUR = Quantity("Consumption unit price", EUR_KWH)
CONSUMPTION_COST_EUR = Quantity("Consumption cost", EUR)
PRODUCTION = Quantity("Production", KWH)
PRODUCTION_UNIT_PRICE_EUR = Quantity("Production unit price", EUR_KWH)
PRODUCTION_PROFIT_EUR = Quantity("Production profit", EUR)
UNIT_PRICE = Quantity("Unit price", EUR_KWH)

# Names of columns introduced when executing strategies
EXPECTED_CONSUMPTION = Quantity("Expected consumption", KWH)
EXPECTED_PRODUCTION = Quantity("Expected production", KWH)
NET_HOUSEHOLD = Quantity("Net household", KWH)
CHARGE = Quantity("Charge", KWH)
CHARGE_FROM_HOUSE = Quantity("Charge from house", KWH)
CHARGE_FROM_GRID = Quantity("Charge from grid", KWH)
DISCHARGE = Quantity("Discharge", KWH)
DISCHARGE_TO_HOUSE = Quantity("Discharge to house", KWH)
DISCHARGE_TO_GRID = Quantity("Discharge to grid", KWH)
SOC = Quantity("SOC", KWH)
NET_BUY_PRICE = Quantity("Net buy price", EUR_KWH)
NET_SELL_PRICE = Quantity("Net sell price", EUR_KWH)
NET_HOUSEHOLD_WITH_BATTERY = Quantity("Net household incl. battery", KWH)
COST_WO_BATTERY = Quantity("Cost w/o battery", EUR)
COST_WITH_BATTERY = Quantity("Cost with battery", EUR)
SAVINGS = Quantity("Savings", EUR)
SAVINGS_PER_DAY = Quantity("Savings per day", EUR)
CUMULATIVE_SAVINGS = Quantity("Cumulative savings", EUR)
NET_VALUE = Quantity("Net value", EUR)
EXPECTED_MAX_CONSUMPTION = Quantity("Expected max consumption", KWH)


if __name__ == "__main__":
    print(f"{NET_HOUSEHOLD.l} ({NET_HOUSEHOLD.unit})")
    print(NET_HOUSEHOLD)
    print(NET_HOUSEHOLD.l)
    print(NET_HOUSEHOLD.unit)
