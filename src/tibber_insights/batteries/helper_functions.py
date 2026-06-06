from tibber_insights.batteries.models import Battery, BatteryPack
from tibber_insights.batteries.candidate_batteries import battery_types


def get_available_battery_packages(max_capacity_to_consider):
    battery_packs = []
    for base_bat in battery_types:
        max_units = int(max_capacity_to_consider // base_bat.capacity)
        for n in range(1, max_units + 1):
            battery_packs.append(BatteryPack(base_bat, n))

    for b in battery_packs:
        print(b, b.properties_to_long_string())

    return battery_packs


if __name__ == "__main__":
    bat = Battery("Test battery", 5, 1.2, 0.81, 100)
    print(bat)
    print(bat.properties_to_long_string())
    print(bat.properties_to_short_string())

