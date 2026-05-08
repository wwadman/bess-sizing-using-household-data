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
            "Market Net Price",
            "Cost Comparison"
        ),
        row_heights=[0.1, 0.2, 0.1, 0.2]
    )

    def add_trace_to_fig(name, y_values, subplot_row, trace_type=go.Scatter, **kwargs):
        if "hovertemplate" not in kwargs:
            unit = getattr(name, 'unit', '')
            if str(unit) == EUR:
                kwargs["hovertemplate"] = f"{name.label}: {EUR}%{{y:.3f}}<extra></extra>"
            else:
                kwargs["hovertemplate"] = f"{name.label}: %{{y:.2f}}<extra></extra>"
        
        fig.add_trace(
            trace_type(
                x=df3days['hour_starts_at'],
                y=y_values,
                name=name.label,
                legend=f'legend{subplot_row}',
                **kwargs
            ),
            row=subplot_row, col=1
        )

    # Subplot 1: SOC
    add_trace_to_fig(
        name=soc,
        y_values=df3days[soc.label],
        subplot_row=1,
        fill='tozeroy',
        line=dict(color='royalblue'),
        showlegend=False
    )

    # Subplot 2: Power Flows
    add_trace_to_fig(
        name=net_household,
        y_values=df3days[net_household.label],
        subplot_row=2,
        line=dict(color='gray', dash='dash')
    )
    
    add_trace_to_fig(
        name=battery_charge,
        y_values=df3days[battery_charge.label],
        subplot_row=2,
        trace_type=go.Bar,
        marker_color='forestgreen'
    )
    
    add_trace_to_fig(
        name=battery_discharge,
        y_values=-df3days[battery_discharge.label],
        subplot_row=2,
        trace_type=go.Bar,
        marker_color='firebrick'
    )

    # Subplot 3: Prices
    add_trace_to_fig(
        name=net_buy_price,
        y_values=df3days[net_buy_price.label],
        subplot_row=3,
        line=dict(color='orange')
    )

    add_trace_to_fig(
        name=net_sell_price,
        y_values=df3days[net_sell_price.label],
        subplot_row=3,
        line=dict(color='blue')
    )

    # Subplot 4: Cost Comparison (Line)
    add_trace_to_fig(
        name=cost_no_battery,
        y_values=df3days[cost_no_battery.label],
        subplot_row=4,
        line=dict(color='gray', dash='dash')
    )
    
    add_trace_to_fig(
        name=cost_with_battery,
        y_values=df3days[cost_with_battery.label],
        subplot_row=4,
        line=dict(color='indigo')
    )

    fig.update_layout(
        height=1000,
        title_text="Battery Simulation Sanity Check",
        showlegend=True,
        legend2=dict(orientation="h", yanchor="top", y=0.74, xanchor="right", x=1),
        legend3=dict(orientation="h", yanchor="top", y=0.53, xanchor="right", x=1),
        legend4=dict(orientation="h", yanchor="top", y=0.36, xanchor="right", x=1),
        barmode='relative',
        hovermode='x'
    )

    fig.update_yaxes(title_text=str(soc.unit), row=1, col=1)
    fig.update_yaxes(title_text=str(net_household.unit), row=2, col=1)
    fig.update_yaxes(title_text=str(net_buy_price.unit), row=3, col=1)
    fig.update_yaxes(title_text=str(cost_no_battery.unit), row=4, col=1)

    fig.show()
    # fig.write_image("battery_sanity_check.png")


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
