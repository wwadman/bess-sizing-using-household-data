from tibber_insights.quantities import BESS_PROPERTIES
import numpy as np

from tibber_insights.strategies import maximize_profit_daily


class Bess:
    def __init__(
            self,
            name,
            capacity,
            charging_rate,
            rte,
            price,
            strategy):
        self.name = name
        self.capacity = capacity
        self.charging_rate = charging_rate
        self.rte = rte  # Round-trip efficiency
        self.price = price
        self.properties = [self.capacity, self.charging_rate, self.rte, self.price]

        # rte = efficiency_charging * efficiency_discharging, and we assume both are equal:
        self.efficiency_charging = self.efficiency_discharging = np.sqrt(self.rte)
        self.strategy = strategy

    def properties_to_long_string(self):
        properties = [f"{PROP} = {val}{PROP.unit}" for (val, PROP) in zip(self.properties, BESS_PROPERTIES)]
        return ", ".join(properties)

    def properties_to_short_string(self):
        properties = [f"{val}{PROP.unit}" for (val, PROP) in zip(self.properties, BESS_PROPERTIES)]
        return ", ".join(properties)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Bess(name='{self.name}', capacity={self.capacity}, charging_rate={self.charging_rate}, rte={self.rte}, price={self.price}, strategy={self.strategy.__name__})"

    def __eq__(self, other):  # Just to enable pickling of dicts of Bess, which smoothens visualization.py development
        if not isinstance(other, Bess):
            return NotImplemented
        return (self.name == other.name and
                self.capacity == other.capacity and
                self.charging_rate == other.charging_rate and
                self.rte == other.rte and
                self.price == other.price and
                self.strategy == other.strategy)

    def __hash__(self):
        return hash((self.name, self.capacity, self.charging_rate, self.rte, self.price, self.strategy))
