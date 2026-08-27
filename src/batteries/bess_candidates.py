# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from src import BessType

bess_candidates = []
bess_candidates += BessType(
    name='Zendure SolarFlow 2400 AC+',
    extension_name="AB3000L",
    capacities=[2.4, 5.3, 8.2, 11.0, 13.9, 16.8],
    charging_rates=[2.4] * 6,
    rtes=[.8815] * 6,  # Could not find info on rte of additional modules, so assuming equal
    prices=[1089, 1818, 2547, 3276, 4005, 4734]
).get_all_possible_besses_of_this_type()
# Based on https://energienerds.nl/index.php/2026/02/10/zendure-solarflow-2400-ac-review-de-ultieme-ac-stekkerbatterij-voor-salderingsvrij-zelfverbruik#prijs
# Consulted June 7, 2026

bess_candidates += BessType(
    name=f'Anker SOLIX Solarbank Max AC',
    extension_name='BP7000 module',
    capacities=[7 * (i + 1) for i in range(6)],
    charging_rates=[3.5] * 6,
    rtes=[.835] * 6,  # Could not find info on rte of additional modules, so assuming equal
    prices=[2499 + 1699 * i for i in range(6)]
).get_all_possible_besses_of_this_type()
# Based on https://energienerds.nl/index.php/2026/05/16/anker-solix-solarbank-max-ac-review#prijs
# Consulted June 7, 2026

bess_candidates += BessType(
    name='Zendure SolarFlow 4000 Mix AC+',
    extension_name="",  # 7kWh extensions until 50kWH (!!) available in 26Q4...
    capacities=[8],
    charging_rates=[4],
    rtes=[.87],
    prices=[2399]
).get_all_possible_besses_of_this_type()
# Based on https://energienerds.nl/index.php/2026/05/08/zendure-solarflow-mix-review#prijs
# Consulted June 7, 2026

# # Something simple for debugging (nonsense values)
# bess_candidates = BessType(name=f'TEST TEST Awesome battery', extension_name='Android 17',
#                             capacities=[7 * (i + 1) for i in range(2)], charging_rates=[3.5] * 2, rtes=[.835] * 2,
#                             prices=[2499 + 1699 * i for i in range(2)]).get_all_possible_besses_of_this_type()
