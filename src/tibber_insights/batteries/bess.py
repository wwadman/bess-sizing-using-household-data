from tibber_insights.quantities import BESS_PROPERTIES
import numpy as np

class Bess:
    def __init__(self, name, capacity, charging_rate, rte, price):
        self.name = name
        self.capacity = capacity
        self.charging_rate = charging_rate
        self.rte = rte  # Round-trip efficiency
        self.price = price

        # rte = efficiency_charging * efficiency_discharging, and we assume both are equal:
        self.efficiency_charging = self.efficiency_discharging = np.sqrt(self.rte)
        self.properties = [self.capacity, self.charging_rate, self.rte, self.price]

    def properties_to_long_string(self):
        properties = [f"{PROP} = {val}{PROP.unit}" for (val, PROP) in zip(self.properties, BESS_PROPERTIES)]
        return ", ".join(properties)

    def properties_to_short_string(self):
        properties = [f"{val}{PROP.unit}" for (val, PROP) in zip(self.properties, BESS_PROPERTIES)]
        return ", ".join(properties)

    def __str__(self):
        return self.name
