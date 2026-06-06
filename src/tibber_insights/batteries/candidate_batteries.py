from tibber_insights.batteries.battery import Battery

battery_types = [
    Battery('Marstek Venus A', capacity=10.6, charging_rate=1.2, rte=0.84, price=2575),
    Battery('Marstek Venus A small', capacity=2.1, charging_rate=1.2, rte=0.84, price=650),
]

MAX_CAPACITY_TO_CONSIDER = 5