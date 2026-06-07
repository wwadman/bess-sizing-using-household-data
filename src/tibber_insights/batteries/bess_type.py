from tibber_insights.batteries.bess import Bess

class BessType():
    def __init__(self,
                 name: str,
                 extension_name: str,
                 capacities: list,
                 charging_rates: list,
                 rtes: list,
                 prices: list):
        self.name = name
        self.extension_name = extension_name
        assert len(capacities) == len(charging_rates) == len(rtes) == len(prices), \
            "Capacities, charging rates, RTE's and prices must have the same length"
        self.capacities = capacities
        self.charging_rate = charging_rates
        self.rtes = rtes
        self.prices = prices

    def get_all_possible_besses_of_this_type(self):
        names = [f"{self.name} + {i}x {self.extension_name}" for i in range(len(self.capacities))]
        return [Bess(name=name, capacity=capacity, charging_rate=charging_rate, rte=rte, price=price)
                for name, capacity, charging_rate, rte, price in zip(names, self.capacities, self.charging_rate, self.rtes, self.prices)]


if __name__ == "__main__":
    anker_solix = BessType(
        name=f'Anker SOLIX Solarbank Max AC',
        extension_name='BP7000 module',
        capacities=[7 * (i + 1) for i in range(6)],
        charging_rates=[3.5 * (i + 1) for i in range(6)],
        rtes=[.835] * 6,
        prices=[2499 + 1699 * i for i in range(6)])
    besses = anker_solix.get_all_possible_besses_of_this_type()
    for bess in besses:
        print(bess, " --- ", bess.properties_to_long_string())