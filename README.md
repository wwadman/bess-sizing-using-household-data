# BESS Compare

Compare any number of [Battery energy storage systems](https://en.wikipedia.org/wiki/Battery_energy_storage_system) (BESSs) by simulating their expected savings for _your_ household. 

By providing your own household load profile and some battery configurations that you are interested in, 
this tool shows 
1. how those batteries would ideally have behaved in your household in that time period
2. how much money they would have saved in that way

[TODO: insert image of plots here]

Finally, the tool lists some stats like payback period for each battery, _assuming your household load profile will stay the same in upcoming years_. 
This will give you a good idea of which battery is the best fit for your household and your expected savings.

## FAQ
#### Why not just use the tool on https://jeroen.nl/energie/opslaan/thuisbatterij/capaciteit-berekenen?
Jeroen's tool serves as a great first step for finding the battery capacity that's roughly ideal for your household. 
In contrast, this tool serves as a great second step for picking from some specific battery configurations with such capacity.

## Setup and usage

1. Install dependencies with uv:
   ```bash
   uv sync
   ```
2. Place your Tibber data CSVs in the `csv/` folder. TODO: add instructions for obtaining tibber data
3. Run the simulation:
   ```bash
   python main.py
   ```

## Notes
- 'net' means 'after potential taxes and fees' (not 'grid')

### Assumptions
- A household load profile under a dynamical electricity contract with hourly/quarterly prices. 
  - Currently Tibber is supported, but other providers can be added.
  - At least one year of household load profile data is required to accurately estimate your future energy bill.
- The Dutch salderingsregeling is abolished.
- The battery minimizes the household's energy bill every day right after 13:00 (when tomorrow's prices are known) by scheduling charging and discharging for the next 24 hours.
  - It uses linear programming to optimize this schedule.
  - To estimate the expected household load profile for the next 24 hours, it uses a moving average of the last 4 weeks (same hour of the week, so each average is over 4 data points).