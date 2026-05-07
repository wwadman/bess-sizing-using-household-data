import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .constants import (
    net_household, battery_charge, battery_discharge,
    soc, net_buy_price, net_sell_price, cost_no_battery, cost_with_battery
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
            "Battery State of Charge (SOC)", 
            "Power Flows (kW)", 
            "Market Net Price (€/kWh)",
            "Cost Comparison (€) - Line Chart"
        ),
        row_heights=[0.1, 0.2, 0.1, 0.2]
    )

    # Subplot 1: SOC
    fig.add_trace(
        go.Scatter(
            x=df3days['hour_starts_at'],
            y=df3days[soc],
            name=soc, 
            fill='tozeroy', 
            line=dict(color='royalblue'),
            hovertemplate=f"{soc}: %{{y:.2f}}<extra></extra>",
            legend='legend'
        ),
        row=1, col=1
    )

    # Subplot 2: Power Flows
    fig.add_trace(
        go.Scatter(
            x=df3days['hour_starts_at'],
            y=df3days[net_household],
            name=net_household, 
            line=dict(color='gray', dash='dash'),
            hovertemplate=f"{net_household}: %{{y:.2f}}<extra></extra>",
            legend='legend2'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df3days['hour_starts_at'],
            y=df3days[battery_charge],
            name=battery_charge, 
            marker_color='forestgreen',
            hovertemplate=f"{battery_charge}: %{{y:.2f}}<extra></extra>",
            legend='legend2'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df3days['hour_starts_at'],
            y=-df3days[battery_discharge],
            name=battery_discharge, 
            marker_color='firebrick',
            hovertemplate=f"{battery_discharge}: %{{y:.2f}}<extra></extra>",
            legend='legend2'
        ),
        row=2, col=1
    )

    # Subplot 3: Prices
    fig.add_trace(
        go.Scatter(
            x=df3days['hour_starts_at'],
            y=df3days[net_buy_price],
            name=net_buy_price,
            line=dict(color='orange'),
            hovertemplate=f"{net_buy_price}: €%{{y:.3f}}<extra></extra>",
            legend='legend3'
        ),
        row=3, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df3days['hour_starts_at'],
            y=df3days[net_sell_price],
            name=net_sell_price,
            line=dict(color='blue'),
            hovertemplate=f"{net_sell_price}: €%{{y:.3f}}<extra></extra>",
            legend='legend3'
        ),
        row=3, col=1
    )

    # Subplot 4: Cost Comparison (Line)
    fig.add_trace(
        go.Scatter(
            x=df3days['hour_starts_at'],
            y=df3days[cost_no_battery],
            name=cost_no_battery, 
            line=dict(color='gray', dash='dash'),
            hovertemplate=f"{cost_no_battery}: €%{{y:.3f}}<extra></extra>",
            legend='legend4'
        ),
        row=4, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df3days['hour_starts_at'],
            y=df3days[cost_with_battery],
            name=cost_with_battery, 
            line=dict(color='indigo'),
            hovertemplate=f"{cost_with_battery}: €%{{y:.3f}}<extra></extra>",
            legend='legend4'
        ),
        row=4, col=1
    )

    fig.update_layout(
        height=1000,
        title_text="Battery Simulation Sanity Check",
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=0.98, xanchor="right", x=1),
        legend2=dict(orientation="h", yanchor="top", y=0.74, xanchor="right", x=1),
        legend3=dict(orientation="h", yanchor="top", y=0.53, xanchor="right", x=1),
        legend4=dict(orientation="h", yanchor="top", y=0.36, xanchor="right", x=1),
        barmode='relative',
        hovermode='x'
    )

    fig.update_yaxes(title_text="kWh", row=1, col=1)
    fig.update_yaxes(title_text="kW", row=2, col=1)
    fig.update_yaxes(title_text="€/kWh", row=3, col=1)
    fig.update_yaxes(title_text="€", row=4, col=1)

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
            xaxis=dict(title='Rate (kW)', tickvals=rates),
            yaxis=dict(title='Capacity (kWh)', tickvals=capacities),
            zaxis_title='Savings (€)',
            camera_eye=dict(x=1.5, y=1.5, z=1.2),
        ),
        width=900,
        height=700,
    )

    fig.show()
