# BESS Compare

Compare any number of [Battery energy storage systems](https://en.wikipedia.org/wiki/Battery_energy_storage_system) (BESSs) by simulating their performance in _your_ household. 

By providing your own household load profile, this repo estimates 

Comparison websites like https://energienerds.nl/index.php/2025/08/26/stekkerbatterijen-de-startgids help finding your
optimal battery configuration, but first you should decide what capacity and max rate is right for you. This repo will
help with that, 



Analyze and simulate energy costs with historical data  and home batteries.



## Features

- **Energy Bill Forecasting**: Estimate your 2027 energy bill based on historical consumption and production.
- **Battery Simulation**: Compare different battery capacities and charging strategies (Arbitrage, MPC).
- **Visualization**: Detailed plots of battery behavior, State of Charge (SOC), and market prices.

## Project Structure

- `src/`: Core package containing logic for billing, simulation, and visualization.
- `main.py`: Entry point for running forecasts and simulations.
- `csv/`: Directory for input data (Tibber hourly exports).

## Setup

1. Install dependencies (requires `uv` or `pip`):
   ```bash
   pip install .
   ```
2. Place your Tibber data CSVs in the `csv/` folder.
3. Run the simulation:
   ```bash
   python main.py
   ```
## Notes
- 'net' means 'after potential taxes and fees' (not 'grid')

## Open issues
- Generalize usage to other Tibber users
- Generalize usage to other users with a dynamical contract
- Add DoD to model
- Lookup checklist for going open source in the way I want to.
  - finish this checklist
## Nice-to-haves
- Add a stupidly simple use-your-own-energy strategy (which indicates how much we can earn by optimizing bess operation)
- Add strategy to dropdown menu
