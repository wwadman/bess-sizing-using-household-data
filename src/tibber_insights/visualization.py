import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .constants import (
    NET_HOUSEHOLD, CHARGE_FROM_HOUSE, CHARGE_FROM_GRID, DISCHARGE_TO_HOUSE, DISCHARGE_TO_GRID,
    SOC, NET_BUY_PRICE, NET_SELL_PRICE, COST_WO_BATTERY, COST_WITH_BATTERY,
    EUR, KW, KWH, TIME, SAVINGS_PER_DAY,
    NET_HOUSEHOLD_WITH_BATTERY
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
                 ['sim_df', 'capacity', 'rate', 'strategy_name']
    """
    if not all_results:
        return

    # Extract unique values for dropdowns
    capacities = sorted(list(set(r['capacity'] for r in all_results)))
    rates = sorted(list(set(r['rate'] for r in all_results)))
    strategies = sorted(list(set(r['strategy_name'] for r in all_results)))

    # We use the first result to get the base layout and shared traces (like prices)
    # Actually, prices and consumption are shared across all results.
    # But SOC and Battery flows change.
    
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

    # To maintain zoom, we don't recreate the figure. We add all traces and toggle visibility.
    # Trace indices mapping
    trace_groups = [] # List of (capacity, rate, strategy, list_of_trace_indices)

    # Common traces (Prices) - we only need to add them once if they are the same
    # But for simplicity and avoiding indexing headaches, let's just add everything per combination.
    # Or add common traces once and never hide them.
    # Consumption (NET_HOUSEHOLD) and Prices are common.
    
    first_df = all_results[0]['sim_df']
    
    # Subplot 3: Prices (Common)
    fig.add_trace(go.Scatter(x=first_df[TIME], y=first_df[NET_BUY_PRICE], name=NET_BUY_PRICE, line=dict(color='orange')), row=3, col=1)
    fig.add_trace(go.Scatter(x=first_df[TIME], y=first_df[NET_SELL_PRICE], name=NET_SELL_PRICE, line=dict(color='blue')), row=3, col=1)
    
    # Subplot 2: Net Household (Common)
    fig.add_trace(go.Scatter(x=first_df[TIME], y=first_df[NET_HOUSEHOLD], name=NET_HOUSEHOLD, line=dict(color='grey', dash='dash')), row=2, col=1)
    
    # Subplot 4: Cost w/o battery (Common)
    fig.add_trace(go.Scatter(x=first_df[TIME], y=first_df[COST_WO_BATTERY], name=COST_WO_BATTERY, line=dict(color='gray', dash='dash')), row=4, col=1)

    common_trace_count = 5 # (2 prices + 1 household + 1 cost wo battery + 1 horizontal line) 
    # Wait, horizontal lines are not traces in the same way.
    
    # Add horizontal lines (static)
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="grey", row=2, col=1)
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="grey", row=4, col=1)

    common_trace_indices = list(range(len(fig.data)))

    for res in all_results:
        cap = res['capacity']
        r = res['rate']
        s = res['strategy_name']
        df = res['sim_df']
        
        group_indices = []
        
        # SOC
        fig.add_trace(go.Scatter(x=df[TIME], y=df[SOC], name=f"SOC (Cap={cap})", line=dict(color='royalblue'), fill='tozeroy', visible=False), row=1, col=1)
        group_indices.append(len(fig.data)-1)
        
        # Net Household with battery
        fig.add_trace(go.Scatter(x=df[TIME], y=df[NET_HOUSEHOLD_WITH_BATTERY], name=f"Net House (incl Batt)", line=dict(color='black'), visible=False), row=2, col=1)
        group_indices.append(len(fig.data)-1)
        
        # Charging
        fig.add_trace(go.Bar(x=df[TIME], y=df[CHARGE_FROM_HOUSE], name=CHARGE_FROM_HOUSE, marker_color='forestgreen', legendgroup='charge', visible=False), row=2, col=1)
        group_indices.append(len(fig.data)-1)
        fig.add_trace(go.Bar(x=df[TIME], y=df[CHARGE_FROM_GRID], name=CHARGE_FROM_GRID, marker_color='lightgreen', legendgroup='charge', visible=False), row=2, col=1)
        group_indices.append(len(fig.data)-1)
        
        # Discharging
        fig.add_trace(go.Bar(x=df[TIME], y=-df[DISCHARGE_TO_HOUSE], name=DISCHARGE_TO_HOUSE, marker_color='firebrick', legendgroup='discharge', visible=False), row=2, col=1)
        group_indices.append(len(fig.data)-1)
        fig.add_trace(go.Bar(x=df[TIME], y=-df[DISCHARGE_TO_GRID], name=DISCHARGE_TO_GRID, marker_color='salmon', legendgroup='discharge', visible=False), row=2, col=1)
        group_indices.append(len(fig.data)-1)
        
        # Cost with battery
        fig.add_trace(go.Scatter(x=df[TIME], y=df[COST_WITH_BATTERY], name=COST_WITH_BATTERY, line=dict(color='indigo'), visible=False), row=4, col=1)
        group_indices.append(len(fig.data)-1)
        
        # Savings per day
        fig.add_trace(go.Bar(x=df[TIME], y=df[SAVINGS_PER_DAY], name=SAVINGS_PER_DAY, visible=False), row=4, col=1)
        group_indices.append(len(fig.data)-1)
        
        trace_groups.append({
            'capacity': cap,
            'rate': r,
            'strategy_name': s,
            'indices': group_indices
        })

    # Set initial visible
    for idx in common_trace_indices:
        fig.data[idx].visible = True
    
    # Show first group by default
    for idx in trace_groups[0]['indices']:
        fig.data[idx].visible = True

    # Dropdown menus
    # Since we have 3 dimensions, and Plotly updatemenus are usually 1D filters, 
    # we need to create buttons that trigger based on the COMBINATION of selections.
    # Alternatively, we can have 3 dropdowns that each update visibility.
    # But a single button can only set visibility to a fixed list.
    
    # A better approach for multi-dimension in Plotly is to have one dropdown that lists ALL combinations
    # OR use custom JS (which is harder in this environment).
    # Let's try 3 separate dropdowns where each one filters the set.
    
    def get_visibility(cap, rate, strategy):
        vis = [False] * len(fig.data)
        for idx in common_trace_indices:
            vis[idx] = True
        for group in trace_groups:
            if group['capacity'] == cap and group['rate'] == rate and group['strategy_name'] == strategy:
                for idx in group['indices']:
                    vis[idx] = True
        return vis

    # If we want 3 independent dropdowns, we'd need them to "know" each other's state.
    # Plotly's updatemenus don't easily support this without Dash.
    # The simplest way is a single dropdown with all combinations: "Cap=5, Rate=0.8, Strategy=..."
    # Or, we can use the 'restyle' method with a bit more complexity.
    
    # Let's go with a single dropdown for now as it's the most robust with pure Plotly.
    buttons = []
    for group in trace_groups:
        label = f"Cap:{group['capacity']} Rate:{group['rate']} {group['strategy_name']}"
        buttons.append(dict(
            method="update",
            label=label,
            args=[{"visible": get_visibility(group['capacity'], group['rate'], group['strategy_name'])},
                  {"title": f"Battery Behavior: {label}"}]
        ))

    fig.update_layout(
        updatemenus=[dict(
            buttons=buttons,
            direction="down",
            showactive=True,
            x=0.5, xanchor="left",
            y=1.15, yanchor="top"
        )],
        height=1000,
        template="plotly_white",
        hovermode='x unified'
    )

    if days:
        end_date = first_df[TIME].max()
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
