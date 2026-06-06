from tibber_insights.batteries.battery import Battery
from tibber_insights.batteries.candidate_batteries import battery_types

class BatteryPack(Battery):
    def __init__(self, base_battery, count):
        name = f"{count}x {base_battery.name}"
        capacity = round(count * base_battery.capacity, 3)
        charging_rate = round(count * base_battery.charging_rate, 3)
        price = count * base_battery.price
        super().__init__(name, capacity, charging_rate, base_battery.rte, price)
        self.base_battery = base_battery
        self.count = count

def get_available_battery_packages(max_capacity_to_consider):
    battery_packs = []
    for base_bat in battery_types:
        max_units = int(max_capacity_to_consider // base_bat.capacity)
        for n in range(1, max_units + 1):
            battery_packs.append(BatteryPack(base_bat, n))

    for b in battery_packs:
        print(b, b.properties_to_long_string())

    return battery_packs
