# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from src.batteries.bess import Bess
from strategies import maximize_profit_daily


class BessType():
    def __init__(self,
                 name: str,
                 extension_name: str,
                 capacities: list,
                 charging_rates: list,
                 rtes: list,
                 prices: list,
                 strategy=maximize_profit_daily):
        self.name = name
        self.extension_name = extension_name
        assert len(capacities) == len(charging_rates) == len(rtes) == len(prices), \
            "Capacities, charging rates, RTE's and prices must have the same length"
        self.capacities = capacities
        self.charging_rate = charging_rates
        self.rtes = rtes
        self.prices = prices
        if not type(strategy) is list:
            self.strategy = [strategy] * len(capacities)

    def get_all_possible_besses_of_this_type(self):
        names = [f"{self.name} + {i}x {self.extension_name}" for i in range(len(self.capacities))]
        return [Bess(name, capacity, charging_rate, rte, price, strategy)
                for name, capacity, charging_rate, rte, price, strategy
                in zip(names, self.capacities, self.charging_rate, self.rtes, self.prices, self.strategy)]


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