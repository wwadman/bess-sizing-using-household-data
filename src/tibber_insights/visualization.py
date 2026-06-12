import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.tibber_insights.quantities import (
    NET_HOUSEHOLD, CHARGE_FROM_HOUSE, CHARGE_FROM_GRID, DISCHARGE_TO_HOUSE, DISCHARGE_TO_GRID,
    SOC, NET_BUY_PRICE, NET_SELL_PRICE, COST_WO_BESS, COST_WITH_BESS,
    TIME, CUMULATIVE_SAVINGS_DAILY, DAILY_SAVINGS_TOTAL,
    NET_HOUSEHOLD_WITH_BESS,
    BESS, ANNUAL_SAVINGS, PROFIT_AFTER_10_YEARS, PAYBACK_PERIOD, SAVINGS_STATS
)


def plot_interactive_bess_behavior(bess_behavior, savings_stats, days=10):
    """
    Creates an interactive Plotly figure with 4 subplots showing bess behavior over time.
    
    The plot includes one dropdown menu at the top to filter simulation
    results by Bess configuration.

    Args:
        bess_behavior (dict): A dict with Bess instances as keys, and
            sim_df as values.
        savings_stats (dict): A dict with Bess instances as keys, and
            stats as values.
        days (int, optional): The number of days to show by default (zoomed in).
            Defaults to 10.
    """

    # Create all stuff that does not change when toggling anything from the dropdowns
    fig = _create_base_figure()
    # To get the base layout and shared traces (like prices), just take the first sim_df
    first_bess = list(bess_behavior.keys())[0]
    first_df = bess_behavior[first_bess]
    common_trace_indices = _add_common_traces(fig, first_df)
    for idx in common_trace_indices:
        fig.data[idx].visible = True  # Set initial visible

    # Create all stuff that does change when toggling anything from the dropdowns
    trace_groups = _add_result_traces(fig, bess_behavior)
    for idx in trace_groups[0]['indices']:
        fig.data[idx].visible = True  # Show by default the first group from dropdown menu
    fig = _create_dropdown_menus(fig, common_trace_indices, trace_groups, bess_behavior, savings_stats)

    _polish_layout(fig, first_df, days)


def _create_base_figure():
    """
    Initializes a 4-row Plotly figure with shared X-axes and predefined subplot titles.

    Returns:
        plotly.graph_objects.Figure: The skeleton figure for the interactive plot.
    """
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "State of Charge (SOC)",
            "Power Flows (Charging/Discharging)",
            "Net Buy/Sell Prices",
            "Cost Comparison"
        ),
        row_heights=[0.1, 0.2, 0.2, 0.1],
    )
    return fig


def _add_interactive_trace(fig, subplot_row, quantity, current_df, swap=False, visible=True, trace_type=go.Scatter, **kwargs):
    """
    Adds a standardized trace to a specific subplot in the interactive figure.

    This helper function configures the legend, hover template, and Y-axis units
    for a given trace.

    Args:
        fig (plotly.graph_objects.Figure): The figure to add the trace to.
        subplot_row (int): The row index (1-based) of the subplot.
        quantity (Quantity): The quantity being plotted (used for naming and units).
        current_df (pd.DataFrame): The source DataFrame (used for the TIME X-axis).
        swap (bool, optional): Whether to swap the sign of the Y-values. Defaults to False.
        visible (bool or "legendonly", optional): Initial visibility of the trace. Defaults to True.
        trace_type (type, optional): The Plotly trace class (e.g., go.Scatter, go.Bar).
            Defaults to go.Scatter.
        **kwargs: Additional keyword arguments passed to the trace constructor.

    Returns:
        int: The index of the added trace in `fig.data`.
    """

    trace = trace_type(
        x=current_df[TIME],
        y=current_df[quantity] * (-1)**swap,
        name=quantity,
        legend=f'legend{subplot_row}',
        hovertemplate=f"{quantity}: %{{y:.3f}} {quantity.unit}<extra></extra>",
        visible=visible,
        **kwargs
    )
    fig.add_trace(trace, row=subplot_row, col=1)
    fig.update_yaxes(title_text=quantity.unit, row=subplot_row, col=1)
    
    # Ensure price subplot (row 3) doesn't force zero to make price fluctuations more pronounced
    if subplot_row == 3:
        fig.update_yaxes(rangemode="normal", row=subplot_row, col=1)

    return len(fig.data) - 1


def _add_common_traces(fig, first_df):
    """
    Adds static traces that are shared across all simulation configurations.

    Includes prices, baseline household consumption, and horizontal reference lines.

    Args:
        fig (plotly.graph_objects.Figure): The figure to add traces to.
        first_df (pd.DataFrame): A DataFrame containing the common data.

    Returns:
        list[int]: The indices of the added common traces in `fig.data`.
    """
    indices = [
        _add_interactive_trace(fig, 3, NET_BUY_PRICE, first_df, line=dict(color='firebrick'), legendgroup='prices'),
        _add_interactive_trace(fig, 3, NET_SELL_PRICE, first_df, line=dict(color='darkseagreen'), legendgroup='prices'),
        _add_interactive_trace(fig, 2, NET_HOUSEHOLD, first_df, line=dict(color='grey', dash='dash'), legendgroup='net_household'),
        _add_interactive_trace(fig, 4, COST_WO_BESS, first_df, line=dict(color='gray', dash='dash'), legendgroup='costs'),
    ]
    # Add horizontal lines (static)
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="grey", row=2, col=1)
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="grey", row=4, col=1)
    return indices


def _add_result_traces(fig, bess_behavior):
    """
    Adds all simulation-specific traces to the figure, initially hidden.

    Iterates through all simulation results and creates traces for SOC, power flows,
    costs, and savings. These are grouped by their configuration metadata.

    Args:
        fig (plotly.graph_objects.Figure): The figure to add traces to.
        bess_behavior (dict): The dict of results mapping Bess to sim_df.

    Returns:
        list[dict]: A list of trace groups, each containing metadata and the
            indices of its associated traces in `fig.data`.
    """
    trace_groups = []
    for bess, df in bess_behavior.items():
        group_indices = [
            _add_interactive_trace(fig, 1, SOC, df, visible=False, line=dict(color='royalblue'), fill='tozeroy', showlegend=False),
            _add_interactive_trace(fig, 2, NET_HOUSEHOLD_WITH_BESS, df, visible=False, line=dict(color='black'), legendgroup='net_household'),
            _add_interactive_trace(fig, 2, CHARGE_FROM_HOUSE, df, visible=False, trace_type=go.Bar, marker_color='darkseagreen', legendgroup='charge'),
            _add_interactive_trace(fig, 2, CHARGE_FROM_GRID, df, visible=False, trace_type=go.Bar, marker_color='forestgreen', legendgroup='charge'),
            _add_interactive_trace(fig, 2, DISCHARGE_TO_HOUSE, df, swap=True, visible=False, trace_type=go.Bar, marker_color='firebrick', legendgroup='discharge'),
            _add_interactive_trace(fig, 2, DISCHARGE_TO_GRID, df, swap=True, visible=False, trace_type=go.Bar, marker_color='salmon', legendgroup='discharge'),
            _add_interactive_trace(fig, 4, COST_WITH_BESS, df, visible=False, line=dict(color='indigo'), legendgroup='costs'),
            _add_interactive_trace(fig, 4, CUMULATIVE_SAVINGS_DAILY, df, visible=False, trace_type=go.Bar, opacity=0.5, marker_color='orange', legendgroup='savings'),
            _add_interactive_trace(fig, 4, DAILY_SAVINGS_TOTAL, df, visible=False, trace_type=go.Bar, opacity=1.0, marker_color='darkorange', legendgroup='savings'),
        ]
        group = {
            'indices': group_indices,
            BESS: bess
        }
        trace_groups.append(group)
    return trace_groups


def _create_dropdown_menus(fig, common_trace_indices, trace_groups, bess_behavior, savings_stats):
    """
    Constructs the Plotly updatemenus for BESS configuration.

    Args:
        fig (plotly.graph_objects.Figure): The figure to apply the menus to.
        common_trace_indices (list[int]): Indices of traces that should always be visible.
        trace_groups (list[dict]): Metadata and indices for each simulation configuration.
        bess_behavior (dict): The dict of results.
        savings_stats (dict): The dict of savings stats.

    Returns:
        plotly.graph_objects.Figure: The updated figure.
    """
    def get_visibility_filter(value):
        vis = [False] * len(fig.data)
        for idx in common_trace_indices:
            vis[idx] = True
        for group in trace_groups:
            if group[BESS].name == value:
                for idx in group['indices']:
                    vis[idx] = True
        return vis

    # 1. Define fixed widths for alignment
    w_name = max(len(bess.name) for bess in bess_behavior.keys())
    w_prop, w_sav, w_pay, w_profit = 30, 20, 20, 20

    # 2. Create the header string
    header_stats = [f"{f'{stat} ({stat.unit})':^{w_profit}}" for stat in SAVINGS_STATS]
    header = f"|| {BESS:^{w_name}} | {'Properties':^{w_prop}} || {' | '.join(header_stats)} ||"

    # 3. Find the best values for bolding
    all_stats = list(savings_stats.values())
    max_annual_savings = max(s[ANNUAL_SAVINGS] for s in all_stats)
    max_profit_10y = max(s[PROFIT_AFTER_10_YEARS] for s in all_stats)
    min_payback_period = min(s[PAYBACK_PERIOD] for s in all_stats)

    buttons = []
    for bess in bess_behavior.keys():
        props = bess.properties_to_short_string()
        stats = savings_stats[bess]

        # Formatting helper to bold best values
        def format_val(val, best_val, width, fmt):
            s_val = f"{val:^{width}{fmt}}"
            if val == best_val:
                return f"<b>{s_val}</b>"
            return s_val

        s_annual = format_val(stats[ANNUAL_SAVINGS], max_annual_savings, w_sav, ".0f")
        s_profit = format_val(stats[PROFIT_AFTER_10_YEARS], max_profit_10y, w_profit, ".0f")
        s_payback = format_val(stats[PAYBACK_PERIOD], min_payback_period, w_pay, ".2f")

        # Format label with fixed widths to match the header
        label = f"|| {bess.name:^{w_name}} | {props:^{w_prop}} || {s_annual} | {s_profit} | {s_payback} ||"

        buttons.append(dict(
            method="update",
            label=label,
            args=[{"visible": get_visibility_filter(bess.name)}]
        ))

    update_menus = [dict(
        buttons=buttons,
        direction="down",
        showactive=True,
        x=0.5, xanchor="center",
        y=1.05, yanchor="top",
        font=dict(size=14, family="Courier New, monospace")
    )]

    fig.update_layout(
        updatemenus=update_menus,
        height=1000,
        margin=dict(t=200, b=50, l=50, r=50),
        template="plotly_white",
        hovermode='x unified',
        showlegend=True,
        legend2=dict(orientation="h", yanchor="top", y=0.79, xanchor="right", x=1),
        legend3=dict(orientation="h", yanchor="top", y=0.41, xanchor="right", x=1),
        legend4=dict(orientation="h", yanchor="top", y=0.19, xanchor="right", x=1),
        barmode='relative',
        # 4. Add the header as an annotation above the dropdown
        annotations=[dict(
            text=header,
            showarrow=False,
            xref="paper", yref="paper",
            x=0.5, y=1.08,
            xanchor="center", yanchor="bottom",
            font=dict(size=14, family="Courier New, monospace")
        )]
    )
    return fig


def _polish_layout(fig=None, first_df=None, days=None):
    fig.update_yaxes(fixedrange=True)

    if days:
        end_date = first_df[TIME].max()
        start_date = end_date - pd.Timedelta(days=days)
        fig.update_xaxes(range=[start_date, end_date])

    fig.show()


if __name__ == "__main__":
    OUTPUT_DIR = "../../output/"
    bess_behavior = pd.read_pickle(OUTPUT_DIR + "bess_behavior.pkl")
    savings_stats = pd.read_pickle(OUTPUT_DIR + "savings_stats.pkl")
    plot_interactive_bess_behavior(bess_behavior, savings_stats, days=10)
