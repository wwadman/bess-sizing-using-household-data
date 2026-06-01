
class Battery:
    def __init__(self, name, capacity, rate, efficiency, price):
        self.name = name
        self.capacity = capacity
        self.rate = rate
        self.efficiency = efficiency
        self.price = price

    def __repr__(self):
        return f"Battery(name='{self.name}', capacity={self.capacity}, rate={self.rate})"
