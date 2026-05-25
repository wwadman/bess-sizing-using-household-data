# Tibber Insights

Analyze and simulate energy costs with Tibber and home batteries.

## Features

- **Energy Bill Forecasting**: Estimate your 2027 energy bill based on historical consumption and production.
- **Battery Simulation**: Compare different battery capacities and charging strategies (Arbitrage, MPC).
- **Visualization**: Detailed plots of battery behavior, State of Charge (SOC), and market prices.

## Project Structure

- `src/tibber_insights/`: Core package containing logic for billing, simulation, and visualization.
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
- Also plot Net Household incl Battery to check if optimal strategy indeed fully exploits "own usage".
- Replace weird (if total_requested_(dis)charge > 1e-6) by assertions

## Nice-to-haves 
- Remove all strategies except linear programming
- Add a stupidly simple use-your-own-energy strategy