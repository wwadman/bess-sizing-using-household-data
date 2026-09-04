# For contributors

## Project Structure
- `src/`: Core package containing logic for billing, simulation, and visualization.
- `main.py`: Entry point for running forecasts and simulations.
- `csv/`: Directory for input data (Tibber hourly exports).

## Open issues / To Do's
- Generalize usage to other Tibber users
- Generalize usage to other users with a dynamical contract
- Improve model:
  - [DoD](https://en.wikipedia.org/wiki/Depth_of_discharge)
  - Idle consumption of the battery
  - Imperfect coverage of self-consumption within each timestep (the battery's reaction on realtime usage has some lag)
  - Add tests
## Nice-to-haves
- Add a stupidly simple use-your-own-energy strategy (which indicates how much we can earn by properly optimizing bess operation)
  - Add strategy to dropdown menu
