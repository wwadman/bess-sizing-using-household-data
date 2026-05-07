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


## Open issues
- Make the statistically expected consumption/production a rolling average so it better captures seasonality.
- Fix the apparent issue that export cost seems to be miscalculated, namely the export kWh times the consumption_unit_price_eur, it should be production_unit_price_eur.
- 