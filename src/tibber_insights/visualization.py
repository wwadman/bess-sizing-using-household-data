import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .constants import (
    net_household, battery_charge, battery_discharge,
    soc, net_buy_price, net_sell_price, cost_no_battery, cost_with_battery,
    EUR, KW, KWH, EUR_KWH
)

def plot_battery_behavior(sim_df, days=3):
    """
    Plots battery behavior (SOC, Charge/Discharge) alongside net consumption and prices.
    Zooms in on the last `days` days by default.
    """
    df3days = sim_df.copy()
    if days:
        end_date = df3days['hour_starts_at'].max()
        start_date = end_date - pd.Timedelta(days=days)
        df3days = df3days[df3days['hour_starts_at'] >= start_date]

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "Battery SOC at end of time step",
            "Power Flows",
            "Buy/Sell Net Prices",
            "Cost Comparison"
        ),
        row_heights=[0.1, 0.2, 0.1, 0.1]
    )

    def add_trace_to_fig(subplot_row, quantity, y_values=df3days, trace_type=go.Scatter, **kwargs):
        fig.add_trace(
            trace_type(
                x=df3days['hour_starts_at'],
                y=y_values[quantity.label],
                name=quantity.label,
                legend=f'legend{subplot_row}',
                hovertemplate=f"{quantity.label}: %{{y:.3f}} {quantity.unit}<extra></extra>",
                **kwargs
            ),
            row=subplot_row, col=1
        )
        fig.update_yaxes(title_text=quantity.unit, row=subplot_row, col=1)

    # Subplot 1: SOC
    add_trace_to_fig(1, soc, line=dict(color='royalblue'), fill='tozeroy', showlegend=False)

    # Subplot 2: Power Flows
    add_trace_to_fig(2, net_household, line=dict(color='gray', dash='dash'))
    add_trace_to_fig(2, battery_charge, trace_type=go.Bar, marker_color='forestgreen')
    add_trace_to_fig(2, battery_discharge, trace_type=go.Bar,marker_color='firebrick',
        y_values=-df3days[[battery_discharge.label]])  # minus 1 to plot discharge negatively

    # Subplot 3: Prices
    add_trace_to_fig(3, net_buy_price, line=dict(color='orange'))
    add_trace_to_fig(3, net_sell_price, line=dict(color='blue'))

    # Subplot 4: Cost Comparison (Line)
    add_trace_to_fig(4, cost_no_battery, line=dict(color='gray', dash='dash'))
    add_trace_to_fig(4, cost_with_battery, line=dict(color='indigo'))

    fig.update_layout(
        height=900,
        title_text="Battery Simulation Sanity Check",
        showlegend=True,
        legend2=dict(orientation="h", yanchor="top", y=0.79, xanchor="right", x=1),
        legend3=dict(orientation="h", yanchor="top", y=0.41, xanchor="right", x=1),
        legend4=dict(orientation="h", yanchor="top", y=0.19, xanchor="right", x=1),
        barmode='relative',
        hovermode='x'
    )
    fig.show()


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
            xaxis=dict(title=f'Rate ({KW})', tickvals=rates),
            yaxis=dict(title=f'Capacity ({KWH})', tickvals=capacities),
            zaxis_title=f'Savings ({EUR})',
            camera_eye=dict(x=1.5, y=1.5, z=1.2),
        ),
        width=900,
        height=700,
    )

    fig.show()
