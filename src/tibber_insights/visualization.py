import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .constants import (
    net_household, battery_charge, battery_discharge, 
    soc, price, cost_no_battery, cost_with_battery
)

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
        rows=5, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "Battery State of Charge (SOC)", 
            "Power Flows (kW)", 
            "Market Price (€/kWh)",
            "Cost Comparison (€) - Line Chart",
            "Cost Comparison (€) - Bar Chart"
        ),
        row_heights=[0.18, 0.18, 0.14, 0.18, 0.18]
    )

    # Subplot 1: SOC
    fig.add_trace(
        go.Scatter(
            x=df['hour_starts_at'], 
            y=df[soc], 
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
            x=df['hour_starts_at'], 
            y=df[net_household], 
            name=net_household, 
            line=dict(color='gray', dash='dash'),
            hovertemplate=f"{net_household}: %{{y:.2f}}<extra></extra>",
            legend='legend2'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df['hour_starts_at'], 
            y=df[battery_charge], 
            name=battery_charge, 
            marker_color='forestgreen',
            hovertemplate=f"{battery_charge}: %{{y:.2f}}<extra></extra>",
            legend='legend2'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df['hour_starts_at'], 
            y=-df[battery_discharge], 
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
            x=df['hour_starts_at'], 
            y=df[price], 
            name=price, 
            line=dict(color='orange'),
            hovertemplate=f"{price}: €%{{y:.3f}}<extra></extra>",
            legend='legend3'
        ),
        row=3, col=1
    )

    # Subplot 4: Cost Comparison (Line)
    fig.add_trace(
        go.Scatter(
            x=df['hour_starts_at'], 
            y=df[cost_no_battery], 
            name=cost_no_battery, 
            line=dict(color='gray', dash='dash'),
            hovertemplate=f"{cost_no_battery}: €%{{y:.3f}}<extra></extra>",
            legend='legend4'
        ),
        row=4, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['hour_starts_at'], 
            y=df[cost_with_battery], 
            name=cost_with_battery, 
            line=dict(color='indigo'),
            hovertemplate=f"{cost_with_battery}: €%{{y:.3f}}<extra></extra>",
            legend='legend4'
        ),
        row=4, col=1
    )

    # Subplot 5: Cost Comparison (Bar)
    fig.add_trace(
        go.Bar(
            x=df['hour_starts_at'], 
            y=df[cost_no_battery], 
            name=cost_no_battery, 
            marker_color='rgba(200, 200, 200, 0.5)',
            hovertemplate=f"{cost_no_battery}: €%{{y:.3f}}<extra></extra>",
            legend='legend5',
            offsetgroup=1
        ),
        row=5, col=1
    )
    fig.add_trace(
        go.Bar(
            x=df['hour_starts_at'], 
            y=df[cost_with_battery], 
            name=cost_with_battery, 
            marker_color='indigo',
            hovertemplate=f"{cost_with_battery}: €%{{y:.3f}}<extra></extra>",
            legend='legend5',
            offsetgroup=2
        ),
        row=5, col=1
    )

    fig.update_layout(
        height=1400,
        title_text="Battery Simulation Sanity Check",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        legend2=dict(orientation="h", yanchor="bottom", y=0.81, xanchor="right", x=1),
        legend3=dict(orientation="h", yanchor="bottom", y=0.62, xanchor="right", x=1),
        legend4=dict(orientation="h", yanchor="bottom", y=0.45, xanchor="right", x=1),
        legend5=dict(orientation="h", yanchor="bottom", y=0.23, xanchor="right", x=1),
        barmode='relative'
    )

    fig.update_yaxes(title_text="kWh", row=1, col=1)
    fig.update_yaxes(title_text="kW", row=2, col=1)
    fig.update_yaxes(title_text="€/kWh", row=3, col=1)
    fig.update_yaxes(title_text="€", row=4, col=1)
    fig.update_yaxes(title_text="€", row=5, col=1)

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
