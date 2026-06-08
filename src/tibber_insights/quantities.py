class Quantity(str):
    def __new__(cls, label, unit):
        obj = super().__new__(cls, label)
        obj.unit = unit
        return obj

    def __reduce__(self):
        return (self.__class__, (str(self), self.unit))

# Units
EUR = "€"
KW = "kW"
KWH = "kWh"
EUR_KWH = f"{EUR}/{KWH}"

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
CHARGE_FROM_HOUSE = Quantity("Charge from house", KWH)
CHARGE_FROM_GRID = Quantity("Charge from grid", KWH)
DISCHARGE_TO_HOUSE = Quantity("Discharge to house", KWH)
DISCHARGE_TO_GRID = Quantity("Discharge to grid", KWH)
SOC = Quantity("SOC", KWH)
NET_BUY_PRICE = Quantity("Net buy price", EUR_KWH)
NET_SELL_PRICE = Quantity("Net sell price", EUR_KWH)
NET_HOUSEHOLD_WITH_BESS = Quantity("Net household incl. bess", KWH)
COST_WO_BESS = Quantity("Cost w/o bess", EUR)
COST_WITH_BESS = Quantity("Cost with bess", EUR)
SAVINGS = Quantity("Savings", EUR)
CUMULATIVE_SAVINGS_DAILY = Quantity("Cumulative savings (reset every midnight)", EUR)
DAILY_SAVINGS_TOTAL = Quantity("Daily savings (plotted at 23:00)", EUR)
NET_VALUE = Quantity("Net value", EUR)
EXPECTED_MAX_CONSUMPTION = Quantity("Expected max consumption", KWH)

# Quantities to filter above plots in dropdown menu
BESS = Quantity("Bess", "")
DROPDOWN_QUANTITIES = [BESS]

# BESS properties
CAPACITY = Quantity("Capacity", KWH)
CHARGING_RATE = Quantity("Charging rate", KW)
RTE = Quantity("RTE", "")
PRICE = Quantity("Price", EUR)
BESS_PROPERTIES = [CAPACITY, CHARGING_RATE, RTE, PRICE]

# Savings stats:
ANNUAL_SAVINGS = Quantity("Annual savings", EUR)
PROFIT_AFTER_10_YEARS = Quantity("10y profit", EUR)
PAYBACK_PERIOD = Quantity("Payback period", "y")
SAVINGS_STATS = [ANNUAL_SAVINGS, PROFIT_AFTER_10_YEARS, PAYBACK_PERIOD]


if __name__ == "__main__":
    print(f"{NET_HOUSEHOLD.l} ({NET_HOUSEHOLD.unit})")
    print(NET_HOUSEHOLD)
    print(NET_HOUSEHOLD.l)
    print(NET_HOUSEHOLD.unit)
