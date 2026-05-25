import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .constants import (
    NET_HOUSEHOLD, CHARGE, CHARGE_FROM_HOUSE, CHARGE_FROM_GRID,
    DISCHARGE, DISCHARGE_TO_HOUSE, DISCHARGE_TO_GRID,
    SOC, NET_BUY_PRICE, NET_SELL_PRICE, COST_WO_BATTERY, COST_WITH_BATTERY,
    EUR, KW, KWH, TIME, CUMULATIVE_SAVINGS, SAVINGS, SAVINGS_PER_DAY,
    NET_HOUSEHOLD_WITH_BATTERY
)

def plot_battery_behavior(sim_df, capacity, rate, strategy_name, days=3):
    """
    Plots battery behavior (SOC, Charge/Discharge) alongside net CONSUMPTION and prices.
    Zooms in on the last `days` days by default.
    """

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            f"SOC of battery ({capacity} {KWH}, {rate} {KW}) at end of the time step",
            f"Charging strategy: {strategy_name}",
            "Buy/Sell Net Prices",
            "Cost Comparison"
        ),
        row_heights=[0.1, 0.2, 0.1, 0.1],
        # specs=[[{}], [{}], [{}], [{"secondary_y": True}]]
    )

    def add_trace_to_fig(subplot_row, quantity, y_values=sim_df, trace_type=go.Scatter, **kwargs):
        fig.add_trace(
            trace_type(
                x=sim_df[TIME],
                y=y_values[quantity],
                name=quantity,
                legend=f'legend{subplot_row}',
                hovertemplate=f"{quantity}: %{{y:.3f}} {quantity.unit}<extra></extra>",
                **kwargs
            ),
            row=subplot_row, col=1,
        )
        fig.update_yaxes(title_text=quantity.unit, fixedrange=True, row=subplot_row, col=1)

    # Subplot 1: SOC
    add_trace_to_fig(1, SOC, line=dict(color='royalblue'), fill='tozeroy', showlegend=False)
    fig.add_hline(y=capacity, line_width=2, line_dash="solid", line_color="blue", row=1, col=1)

    # Subplot 2: Power Flows
    add_trace_to_fig(2, NET_HOUSEHOLD, line=dict(color='grey', dash='dash'))
    add_trace_to_fig(2, NET_HOUSEHOLD_WITH_BATTERY, line=dict(color='black'))

    # Charging split
    add_trace_to_fig(2, CHARGE_FROM_HOUSE, trace_type=go.Bar, marker_color='forestgreen',
                     legendgroup='charge')
    add_trace_to_fig(2, CHARGE_FROM_GRID, trace_type=go.Bar, marker_color='lightgreen',
                     legendgroup='charge')

    # Discharging split (negative values)
    add_trace_to_fig(2, DISCHARGE_TO_HOUSE, trace_type=go.Bar, marker_color='firebrick',
                     y_values=-sim_df[[DISCHARGE_TO_HOUSE]], legendgroup='discharge')
    add_trace_to_fig(2, DISCHARGE_TO_GRID, trace_type=go.Bar, marker_color='salmon',
                     y_values=-sim_df[[DISCHARGE_TO_GRID]], legendgroup='discharge')

    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="grey", row=2, col=1)

    # Subplot 3: Prices
    add_trace_to_fig(3, NET_BUY_PRICE, line=dict(color='orange'))
    add_trace_to_fig(3, NET_SELL_PRICE, line=dict(color='blue'))

    # Subplot 4: Cost Comparison (Line)
    add_trace_to_fig(4, COST_WO_BATTERY, line=dict(color='gray', dash='dash'))
    add_trace_to_fig(4, COST_WITH_BATTERY, line=dict(color='indigo'))
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="grey", row=4, col=1)
    add_trace_to_fig(4, SAVINGS_PER_DAY, trace_type=go.Bar)


    fig.update_layout(
        height=900,
        title_text="Battery Simulation Sanity Check",
        title_x=0.5,
        title_xanchor="center",
        showlegend=True,
        legend2=dict(orientation="h", yanchor="top", y=0.79, xanchor="right", x=1),
        legend3=dict(orientation="h", yanchor="top", y=0.41, xanchor="right", x=1),
        legend4=dict(orientation="h", yanchor="top", y=0.19, xanchor="right", x=1),
        barmode='relative',
        hovermode='x'
    )

    # Set initial zoom to the last n days, but allow panning
    if days:
        end_date = sim_df[TIME].max()
        start_date = end_date - pd.Timedelta(days=days)
        fig.update_xaxes(range=[start_date, end_date])

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
