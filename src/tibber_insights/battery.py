from tibber_insights.constants import CAPACITY, CHARGING_RATE, RTE


class Battery:
    def __init__(self, name, capacity, charging_rate, rte, price):
        self.name = name
        self.capacity = capacity
        self.charging_rate = charging_rate
        self.rte = rte
        self.price = price

    def __repr__(self):
        return (f"{self.name} ("
                f"{self.capacity} {CAPACITY.unit}, "
                f"{self.charging_rate} {CHARGING_RATE.unit}, "
                f"{RTE}={self.rte}"
                f")")
