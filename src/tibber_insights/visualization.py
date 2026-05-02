import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_battery_behavior(sim_df, days=3):
    """
    Plots battery behavior (SOC, Charge/Discharge) alongside net consumption and prices.
    Zooms in on the last `days` days by default.
    """
    df = sim_df.copy()
    if days:
        end_date = df['hour_starts_at'].max()
        start_date = end_date - pd.Timedelta(days=days)
        df = df[df['hour_starts_at'] >= start_date]

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("Battery State of Charge (SOC)", "Power Flows (kW)", "Market Price (€/kWh)"),
        row_heights=[0.4, 0.4, 0.2]
    )

    # Subplot 1: SOC
    fig.add_trace(
        go.Scatter(x=df['hour_starts_at'], y=df['soc_kwh'], name="SOC (kWh)", fill='tozeroy', line=dict(color='royalblue')),
        row=1, col=1
    )

    # Subplot 2: Power Flows
    fig.add_trace(
        go.Scatter(x=df['hour_starts_at'], y=df['net_kwh'], name="Net Household (kW)", line=dict(color='gray', dash='dash')),
        row=2, col=1
    )
    fig.add_trace(
        go.Bar(x=df['hour_starts_at'], y=df['charge_kwh'], name="Battery Charge (kW)", marker_color='forestgreen'),
        row=2, col=1
    )
    fig.add_trace(
        go.Bar(x=df['hour_starts_at'], y=-df['discharge_kwh'], name="Battery Discharge (kW)", marker_color='firebrick'),
        row=2, col=1
    )

    # Subplot 3: Prices
    fig.add_trace(
        go.Scatter(x=df['hour_starts_at'], y=df['consumption_unit_price_eur'], name="Price (€/kWh)", line=dict(color='orange')),
        row=3, col=1
    )

    fig.update_layout(
        height=800,
        title_text="Battery Simulation Sanity Check",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text="kWh", row=1, col=1)
    fig.update_yaxes(title_text="kW", row=2, col=1)
    fig.update_yaxes(title_text="€/kWh", row=3, col=1)

    fig.show()
    fig.write_image("battery_sanity_check.png")


def plot_battery_savings_surface(results_df, strategy_name, rates, capacities):
    pivot = results_df[results_df['strategy'] == strategy_name] \
        .pivot(index='capacity_kwh', columns='rate_kw', values='annual_savings_eur') \
        .fillna(0)

    fig = go.Figure(data=[go.Surface(
        z=pivot.values,
        x=pivot.columns.values,
        y=pivot.index.values,
        colorscale='Viridis',
    )])

    fig.update_layout(
        title=f'Annual Savings vs Capacity & Rate (Strategy: {strategy_name})',
        scene=dict(
            xaxis=dict(title='Rate (kW)', tickvals=rates),
            yaxis=dict(title='Capacity (kWh)', tickvals=capacities),
            zaxis_title='Savings (€)',
            camera_eye=dict(x=1.5, y=1.5, z=1.2),
        ),
        width=900,
        height=700,
    )

    fig.show()
