import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .constants import (
    NET_HOUSEHOLD, CHARGE_FROM_HOUSE, CHARGE_FROM_GRID, DISCHARGE_TO_HOUSE, DISCHARGE_TO_GRID,
    SOC, NET_BUY_PRICE, NET_SELL_PRICE, COST_WO_BATTERY, COST_WITH_BATTERY,
    EUR, KW, KWH, TIME, SAVINGS_PER_DAY,
    NET_HOUSEHOLD_WITH_BATTERY,
    CAPACITY, CHARGING_RATE, STRATEGY, DROPDOWN_QUANTITIES
)

def plot_battery_behavior(sim_df, capacity, rate, strategy_name, days=3, show=True):
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

    if show:
        fig.show()
    return fig


def plot_interactive_battery_behavior(all_results, days=10):
    """
    Creates a single plot with dropdowns to switch between different
    capacities, rates, and strategies.
    
    all_results: List of dicts with keys:
                 ['sim_df'] + [CAPACITY, CHARGING_RATE, STRATEGY]
    """
    if not all_results:
        return

    # Extract unique values for dropdowns and map them to their constants
    dropdown_quantities = {q: sorted(list(set(r[q] for r in all_results))) for q in DROPDOWN_QUANTITIES}

    # We use the first result to get the base layout and shared traces (like prices)
    first_df = all_results[0]['sim_df']
    
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "State of Charge (SOC)",
            "Power Flows (Charging/Discharging)",
            "Buy/Sell Net Prices",
            "Cost Comparison"
        ),
        row_heights=[0.1, 0.2, 0.1, 0.1],
    )

    def add_interactive_trace(subplot_row, quantity, y_values, current_df, visible=True, trace_type=go.Scatter, **kwargs):
        trace = trace_type(
            x=current_df[TIME],
            y=y_values,
            name=quantity,
            legend=f'legend{subplot_row}',
            hovertemplate=f"{quantity}: %{{y:.3f}} {quantity.unit}<extra></extra>",
            visible=visible,
            **kwargs
        )
        fig.add_trace(trace, row=subplot_row, col=1)
        fig.update_yaxes(title_text=quantity.unit, row=subplot_row, col=1)
        return len(fig.data) - 1

    # Common traces (Prices, Household, Cost w/o battery)
    common_trace_indices = [
        add_interactive_trace(3, NET_BUY_PRICE, first_df[NET_BUY_PRICE], first_df, line=dict(color='orange')),
        add_interactive_trace(3, NET_SELL_PRICE, first_df[NET_SELL_PRICE], first_df, line=dict(color='blue')),
        add_interactive_trace(2, NET_HOUSEHOLD, first_df[NET_HOUSEHOLD], first_df, line=dict(color='grey', dash='dash')),
        add_interactive_trace(4, COST_WO_BATTERY, first_df[COST_WO_BATTERY], first_df, line=dict(color='gray', dash='dash')),
    ]
    
    # Add horizontal lines (static)
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="grey", row=2, col=1)
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="grey", row=4, col=1)

    trace_groups = [] # List of (capacity, rate, strategy, list_of_trace_indices)
    for res in all_results:
        df = res['sim_df']

        group_indices = [
            add_interactive_trace(1, SOC, df[SOC], df, visible=False, line=dict(color='royalblue'), fill='tozeroy', showlegend=False),
            add_interactive_trace(2, NET_HOUSEHOLD_WITH_BATTERY, df[NET_HOUSEHOLD_WITH_BATTERY], df, visible=False, line=dict(color='black')),
            add_interactive_trace(2, CHARGE_FROM_HOUSE, df[CHARGE_FROM_HOUSE], df, visible=False, trace_type=go.Bar, marker_color='forestgreen', legendgroup='charge'),
            add_interactive_trace(2, CHARGE_FROM_GRID, df[CHARGE_FROM_GRID], df, visible=False, trace_type=go.Bar, marker_color='lightgreen', legendgroup='charge'),
            add_interactive_trace(2, DISCHARGE_TO_HOUSE, -df[DISCHARGE_TO_HOUSE], df, visible=False, trace_type=go.Bar, marker_color='firebrick', legendgroup='discharge'),
            add_interactive_trace(2, DISCHARGE_TO_GRID, -df[DISCHARGE_TO_GRID], df, visible=False, trace_type=go.Bar, marker_color='salmon', legendgroup='discharge'),
            add_interactive_trace(4, COST_WITH_BATTERY, df[COST_WITH_BATTERY], df, visible=False, line=dict(color='indigo')),
            add_interactive_trace(4, SAVINGS_PER_DAY, df[SAVINGS_PER_DAY], df, visible=False, trace_type=go.Bar),
        ]
        
        trace_groups.append({
            CAPACITY: res[CAPACITY],
            CHARGING_RATE: res[CHARGING_RATE],
            STRATEGY: res[STRATEGY],
            'indices': group_indices
        })

    # Set initial visible
    for idx in common_trace_indices:
        fig.data[idx].visible = True
    
    # Show first group by default
    for idx in trace_groups[0]['indices']:
        fig.data[idx].visible = True

    # Dropdown menus
    # To have 3 independent dropdowns in pure Plotly, we can't easily do "AND" filtering
    # because each button must provide a complete visibility list for all traces.
    # However, we can provide 3 dropdowns that each control one dimension, 
    # but they will effectively reset the others, or we can use a more clever approach.
    # Given the constraint of pure Plotly, the most reliable way to have 3 buttons
    # is to have them filter by that specific dimension, showing all results that match.
    
    def get_visibility_filter(dim_key, value):
        vis = [False] * len(fig.data)
        for idx in common_trace_indices:
            vis[idx] = True
        for group in trace_groups:
            if group[dim_key] == value:
                for idx in group['indices']:
                    vis[idx] = True
        return vis

    # Generate buttons and updatemenus dynamically
    updatemenus = []
    x_positions = [0.35, 0.5, 0.65]
    
    for i, (quantity_to_filter, values) in enumerate(dropdown_quantities.items()):
        buttons = []
        for val in values:
            buttons.append(dict(
                method="update",
                label=f"{quantity_to_filter}: {val} {quantity_to_filter.unit}",
                args=[{"visible": get_visibility_filter(quantity_to_filter, val)},
                      {"title": f"Battery Behavior vzxcvzxcvxcv (Filtered by {quantity_to_filter}: {val})"}]
            ))
        
        updatemenus.append(dict(
            buttons=buttons,
            direction="down",
            showactive=True,
            x=x_positions[i], xanchor="center",
            y=1.15, yanchor="top",
            font=dict(size=14)
        ))

    fig.update_layout(
        updatemenus=updatemenus,
        height=1000,
        template="plotly_white",
        hovermode='x unified',
        showlegend=True,
        legend2=dict(orientation="h", yanchor="top", y=0.79, xanchor="right", x=1),
        legend3=dict(orientation="h", yanchor="top", y=0.41, xanchor="right", x=1),
        legend4=dict(orientation="h", yanchor="top", y=0.19, xanchor="right", x=1),
        barmode='relative'
    )

    fig.update_yaxes(fixedrange=True)

    if days:
        end_date = first_df[TIME].max()
        start_date = end_date - pd.Timedelta(days=days)
        fig.update_xaxes(range=[start_date, end_date])

    fig.show()


def plot_battery_savings_surface(results_df, strategy_name, rates, capacities):
    pivot = results_df[results_df[STRATEGY] == strategy_name] \
        .pivot(index=CAPACITY, columns=CHARGING_RATE, values='annual_savings_eur') \
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
