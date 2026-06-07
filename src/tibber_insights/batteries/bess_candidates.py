from tibber_insights.batteries.bess_type import BessType
from tibber_insights.batteries.bess import Bess

bess_candidates = BessType(
        name=f'Anker SOLIX Solarbank Max AC',
        extension_name='BP7000 module',
        capacities=[7 * (i + 1) for i in range(6)],
        charging_rates=[3.5 * (i + 1) for i in range(6)],
        rtes=[.835] * 6,
        prices=[2499 + 1699 * i for i in range(6)]
    ).get_all_possible_besses_of_this_type()

# bess_candidates += [
#     Bess(name='Zendure SolarFlow 2400 AC+',
#          capacity=,
#          charging_rate=,
#          rte=.8815,
#          price=1089)
# ]
# battery_packs =
# MAX_CAPACITY_TO_CONSIDER = 30