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
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "Battery State of Charge (SOC)", 
            "Power Flows (kW)", 
            "Market Price (€/kWh)",
            "Cost Comparison (€) - Line Chart"
        ),
        row_heights=[0.2, 0.2, 0.15, 0.2, 0.25]
    )

    # Subplot 1: SOC
    fig.add_trace(
        go.Scatter(
            x=df['hour_starts_at'], 
            y=df['soc_kwh'], 
            name="SOC (kWh)", 
            fill='tozeroy', 
            line=dict(color='royalblue'),
            legend='legend'
        ),
        row=1, col=1
    )

    # Subplot 2: Power Flows
    fig.add_trace(
        go.Scatter(
            x=df['hour_starts_at'], 
            y=df['Net Household (kW)'], 
            name="Net Household (kW)", 
            line=dict(color='gray', dash='dash'),
            legend='legend2'
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Bar(
            x=df['hour_starts_at'], 
            y=df['Battery Charge (kW)'], 
            name="Battery Charge (kW)", 
            marker_color='forestgreen',
            legend='legend2'
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Bar(
            x=df['hour_starts_at'], 
            y=-df['Battery Discharge (kW)'], 
            name="Battery Discharge (kW)", 
            marker_color='firebrick',
            legend='legend2'
        ),
        row=2, col=1
    )

    # Subplot 3: Prices
    fig.add_trace(
        go.Scatter(
            x=df['hour_starts_at'], 
            y=df['consumption_unit_price_eur'], 
            name="Price (€/kWh)", 
            line=dict(color='orange'),
            legend='legend3'
        ),
        row=3, col=1
    )

    # Subplot 4: Cost Comparison (Line)
    fig.add_trace(
        go.Scatter(
            x=df['hour_starts_at'], 
            y=df['cost_no_batt_eur'], 
            name="Cost (No Battery)", 
            line=dict(color='gray', dash='dash'),
            hovertemplate="Baseline Cost: €%{y:.3f}<extra></extra>",
            legend='legend4'
        ),
        row=4, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df['hour_starts_at'], 
            y=df['cost_with_batt_eur'], 
            name="Cost (With Battery)", 
            line=dict(color='indigo'),
            hovertemplate="Cost with Battery: €%{y:.3f}",
            legend='legend4'
        ),
        row=4, col=1
    )

    fig.update_layout(
        height=1200,
        title_text="Battery Simulation Sanity Check",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        legend2=dict(orientation="h", yanchor="bottom", y=0.80, xanchor="right", x=1),
        legend3=dict(orientation="h", yanchor="bottom", y=0.59, xanchor="right", x=1),
        legend4=dict(orientation="h", yanchor="bottom", y=0.42, xanchor="right", x=1),
        # legend5=dict(orientation="h", yanchor="bottom", y=0.21, xanchor="right", x=1),
        barmode='relative'
    )

    fig.update_yaxes(title_text="kWh", row=1, col=1)
    fig.update_yaxes(title_text="kW", row=2, col=1)
    fig.update_yaxes(title_text="€/kWh", row=3, col=1)
    fig.update_yaxes(title_text="€", row=4, col=1)
    # fig.update_yaxes(title_text="€", row=5, col=1)

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
