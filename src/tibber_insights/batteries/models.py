from tibber_insights.constants import BATTERY_PROPERTIES
import numpy as np

class Battery:
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
        properties = [f"{PROP} = {val}{PROP.unit}" for (val, PROP) in zip(self.properties, BATTERY_PROPERTIES)]
        return ", ".join(properties)

    def properties_to_short_string(self):
        properties = [f"{val}{PROP.unit}" for (val, PROP) in zip(self.properties, BATTERY_PROPERTIES)]
        return ", ".join(properties)

    def __str__(self):
        return self.name


class BatteryPack(Battery):
    def __init__(self, base_battery, count):
        name = f"{count}x {base_battery.name}"
        capacity = round(count * base_battery.capacity, 3)
        charging_rate = round(count * base_battery.charging_rate, 3)
        price = count * base_battery.price
        super().__init__(name, capacity, charging_rate, base_battery.rte, price)
        self.base_battery = base_battery
        self.count = count
