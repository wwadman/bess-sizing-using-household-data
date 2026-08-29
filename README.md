# BESS Compare

Compare any number of [Battery energy storage systems](https://en.wikipedia.org/wiki/Battery_energy_storage_system) (BESSs) by simulating their performance in _your_ household. 

By providing your own household load profile and some battery configurations that you are interested in, 
this repo shows 
1. how those batteries would ideally have behaved in your household in that time period
2. how much money they would have saved in that way

[TODO: insert image of plots here]

Finally, the tool lists some stats like payback period for each battery, _assuming your household load profile will stay the same in upcoming years_. 
This will give you a rough idea of which battery is the best fit for your household and your expected savings.


### Assumptions
- A household load profile under a dynamical electricity contract with hourly/quarterly prices. 
  - Currently only Tibber is supported, but other providers can be added.
  - At least one year of historical data is required to accurately estimate your future energy bill.
- Obviously, the model assumes the Dutch salderingsregeling to be abolished.
- TODO: complete this list

## Features
- **Energy Bill Forecasting**: Estimate your future-year energy bill based on historical consumption and production.
- **Battery Simulation**: Compare different battery capacities and charging strategies (Arbitrage, MPC).
- **Visualization**: Detailed plots of battery behavior, State of Charge (SOC), and market prices:
  - Battery SOC over time
  - Energy bought/sold from/to the grid
  - Market prices and household consumption

## FAQ
**Why not just use the tool on https://jeroen.nl/energie/opslaan/thuisbatterij/capaciteit-berekenen?**
The tool on that website is a great first step for estimating the battery capacity that will be roughly ideal for your household. 
In contrast, the tool in this repo serves as a great second step to compare specific battery configurations in the market.

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