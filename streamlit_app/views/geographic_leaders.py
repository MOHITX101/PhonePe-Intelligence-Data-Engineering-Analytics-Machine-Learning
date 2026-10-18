"""
Geographic Leaders page.

Explores PhonePe's highest-ranked states, districts and pincodes
for transactions, registered users and registered merchants.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from plotly.subplots import make_subplots

from components.formatters import (
    format_compact_number,
    format_state_name,
)
from components.layout import (
    render_insight_card,
    render_kpi_card,
)
from services.data_loader import (
    load_top_geographies,
)


# ============================================================
# PAGE CONSTANTS
# ============================================================

PHONEPE_PURPLE = "#5F259F"
PHONEPE_LIGHT_PURPLE = "#A855F7"
PHONEPE_PINK = "#EC4899"
PHONEPE_GREEN = "#10B981"
PHONEPE_ORANGE = "#F59E0B"
PHONEPE_BLUE = "#3B82F6"
PHONEPE_RED = "#EF4444"

TRANSPARENT = "rgba(0,0,0,0)"
GRID_COLOUR = "rgba(95,37,159,0.11)"

DOMAIN_COLOURS = {
    "Transaction": PHONEPE_PURPLE,
    "User": PHONEPE_BLUE,
    "Merchant": PHONEPE_GREEN,
}


# ============================================================
# PAGE HEADER
# ============================================================

st.title("Geographic Leaders")

st.caption(
    "Discover the highest-performing states, districts and "
    "pincodes across transactions, registered users and merchants."
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(value):
    """
    Convert slugs and coded values into readable labels.
    """

    if value is None or pd.isna(value):
        return "Unknown"

    return (
        str(value)
        .replace("_", " ")
        .replace("-", " ")
        .strip()
        .title()
    )


def clean_entity_name(
    entity_name,
    geography_level,
):
    """
    Format entity names while preserving pincodes.
    """

    if entity_name is None or pd.isna(entity_name):
        return "Unknown"

    entity_text = str(entity_name).strip()

    if geography_level == "pincode":
        return entity_text

    return clean_text(entity_text)


def format_metric_name(value):
    """
    Format metric names for display.
    """

    metric_labels = {
        "transaction_count": "Transaction Count",
        "registered_user_count": "Registered Users",
        "registered_merchant_count":
            "Registered Merchants",
    }

    return metric_labels.get(
        str(value),
        clean_text(value),
    )


def safe_gap_percentage(
    leader_value,
    runner_up_value,
):
    """
    Calculate how far the leader is ahead of the runner-up.
    """

    if (
        leader_value is None
        or runner_up_value is None
        or pd.isna(leader_value)
        or pd.isna(runner_up_value)
        or runner_up_value == 0
    ):
        return None

    return (
        (leader_value - runner_up_value)
        / runner_up_value
    ) * 100


def apply_chart_layout(
    figure,
    height=450,
    show_legend=True,
):
    """
    Apply the shared visual style.
    """

    figure.update_layout(
        height=height,
        margin=dict(
            l=15,
            r=15,
            t=60,
            b=20,
        ),
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font=dict(
            family="Inter, sans-serif",
            color="#33263D",
        ),
        title_font=dict(
            size=18,
            color="#24152F",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        showlegend=show_legend,
        hoverlabel=dict(
            bgcolor="#24152F",
            font_color="#FFFFFF",
            bordercolor=PHONEPE_PURPLE,
        ),
    )

    figure.update_xaxes(
        showgrid=False,
        zeroline=False,
        color="#7C7485",
    )

    figure.update_yaxes(
        gridcolor=GRID_COLOUR,
        zeroline=False,
        color="#7C7485",
    )

    return figure


def prepare_geography_data(raw_df):
    """
    Clean and enrich the geographic ranking dataset.
    """

    geography_df = raw_df.copy()

    geography_df["period_start_date"] = pd.to_datetime(
        geography_df["period_start_date"],
        errors="coerce",
    )

    numeric_columns = [
        "year",
        "quarter",
        "rank_position",
        "metric_value",
    ]

    for column in numeric_columns:
        geography_df[column] = pd.to_numeric(
            geography_df[column],
            errors="coerce",
        )

    geography_df["domain_name"] = (
        geography_df["metric_domain"]
        .apply(clean_text)
    )

    geography_df["metric_display_name"] = (
        geography_df["metric_name"]
        .apply(format_metric_name)
    )

    geography_df["geography_level_name"] = (
        geography_df["geography_level"]
        .apply(clean_text)
    )

    geography_df["ranking_scope_name"] = np.where(
        geography_df["file_scope"] == "country",
        "India-wide ranking",
        "Within-state ranking",
    )

    geography_df["parent_state_name"] = (
        geography_df["parent_state_slug"]
        .fillna("India")
        .apply(
            lambda value: (
                "India"
                if value == "India"
                else format_state_name(value)
            )
        )
    )

    geography_df["entity_display_name"] = (
        geography_df.apply(
            lambda row: clean_entity_name(
                row["entity_name"],
                row["geography_level"],
            ),
            axis=1,
        )
    )

    geography_df["entity_state_label"] = np.where(
        geography_df["parent_state_name"]
        == "India",
        geography_df["entity_display_name"],
        (
            geography_df["entity_display_name"]
            + ", "
            + geography_df["parent_state_name"]
        ),
    )

    geography_df["entity_key"] = (
        geography_df["file_scope"].astype(str)
        + "|"
        + geography_df[
            "geography_level"
        ].astype(str)
        + "|"
        + geography_df[
            "parent_state_slug"
        ].fillna("india").astype(str)
        + "|"
        + geography_df[
            "geography_slug"
        ].astype(str)
    )

    return geography_df


# ============================================================
# LOAD DATA
# ============================================================

try:
    with st.spinner(
        "Loading geographic leaders from Databricks..."
    ):
        raw_geography_df = load_top_geographies()

except Exception as error:
    st.error(
        "The Geographic Leaders page could not load "
        "data from Databricks."
    )

    st.exception(error)
    st.stop()


if raw_geography_df.empty:
    st.warning(
        "The geographic leader table returned no rows."
    )
    st.stop()


geography_df = prepare_geography_data(
    raw_geography_df
)


# ============================================================
# FILTER OPTIONS
# ============================================================

period_lookup = (
    geography_df[
        [
            "period",
            "period_start_date",
        ]
    ]
    .drop_duplicates()
    .dropna()
    .sort_values(
        "period_start_date",
        ascending=False,
    )
)

period_options = (
    period_lookup["period"]
    .astype(str)
    .tolist()
)

domain_options = (
    geography_df["domain_name"]
    .dropna()
    .sort_values()
    .unique()
    .tolist()
)


# ============================================================
# PRIMARY FILTERS
# ============================================================

with st.container(border=True):
    st.markdown("#### Ranking filters")

    filter_col1, filter_col2, filter_col3 = (
        st.columns(3)
    )

    with filter_col1:
        selected_period = st.selectbox(
            "Reporting quarter",
            options=period_options,
            index=0,
            key="leader_selected_period",
        )

    default_domain_index = (
        domain_options.index("Transaction")
        if "Transaction" in domain_options
        else 0
    )

    with filter_col2:
        selected_domain = st.selectbox(
            "Metric domain",
            options=domain_options,
            index=default_domain_index,
            key="leader_selected_domain",
        )

    period_domain_df = geography_df[
        (
            geography_df["period"]
            == selected_period
        )
        & (
            geography_df["domain_name"]
            == selected_domain
        )
    ].copy()

    scope_options = (
        period_domain_df[
            "ranking_scope_name"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    scope_options = sorted(
        scope_options,
        key=lambda value: (
            value != "India-wide ranking",
            value,
        ),
    )

    with filter_col3:
        selected_scope_name = st.selectbox(
            "Ranking scope",
            options=scope_options,
            index=0,
            key="leader_selected_scope",
        )


selected_scope = (
    "country"
    if selected_scope_name
    == "India-wide ranking"
    else "state"
)

scope_df = period_domain_df[
    period_domain_df["file_scope"]
    == selected_scope
].copy()

geography_level_options = (
    scope_df[
        [
            "geography_level",
            "geography_level_name",
        ]
    ]
    .drop_duplicates()
    .sort_values("geography_level_name")
)

level_name_to_value = dict(
    zip(
        geography_level_options[
            "geography_level_name"
        ],
        geography_level_options[
            "geography_level"
        ],
    )
)

level_display_options = list(
    level_name_to_value.keys()
)

default_level_index = 0

if "State" in level_display_options:
    default_level_index = (
        level_display_options.index("State")
    )

with st.container(border=True):
    secondary_col1, secondary_col2, secondary_col3 = (
        st.columns(3)
    )

    with secondary_col1:
        selected_level_name = st.selectbox(
            "Geography level",
            options=level_display_options,
            index=default_level_index,
            key="leader_selected_level",
        )

    selected_level = level_name_to_value[
        selected_level_name
    ]

    level_df = scope_df[
        scope_df["geography_level"]
        == selected_level
    ].copy()

    state_options = ["All States and UTs"]

    if selected_scope == "state":
        available_states = (
            level_df[
                "parent_state_name"
            ]
            .dropna()
            .sort_values()
            .unique()
            .tolist()
        )

        state_options.extend(
            available_states
        )

    with secondary_col2:
        selected_parent_state = st.selectbox(
            "Parent state",
            options=state_options,
            index=0,
            disabled=selected_scope != "state",
            key="leader_selected_parent_state",
        )

    if (
        selected_scope == "state"
        and selected_parent_state
        != "All States and UTs"
    ):
        level_df = level_df[
            level_df["parent_state_name"]
            == selected_parent_state
        ].copy()

    metric_options = (
        level_df[
            "metric_display_name"
        ]
        .dropna()
        .sort_values()
        .unique()
        .tolist()
    )

    with secondary_col3:
        selected_metric_name = st.selectbox(
            "Metric",
            options=metric_options,
            index=0,
            key="leader_selected_metric",
        )


current_leaders_df = level_df[
    level_df["metric_display_name"]
    == selected_metric_name
].copy()

current_leaders_df = (
    current_leaders_df
    .dropna(
        subset=[
            "rank_position",
            "metric_value",
        ]
    )
    .sort_values(
        [
            "rank_position",
            "metric_value",
        ],
        ascending=[
            True,
            False,
        ],
    )
)


if current_leaders_df.empty:
    st.warning(
        "No geographic ranking records are available "
        "for the selected filters."
    )
    st.stop()


# ============================================================
# CURRENT LEADER CALCULATIONS
# ============================================================

leader_row = current_leaders_df.iloc[0]

runner_up_row = (
    current_leaders_df.iloc[1]
    if len(current_leaders_df) > 1
    else None
)

leader_name = leader_row[
    "entity_state_label"
]

leader_value = leader_row[
    "metric_value"
]

runner_up_value = (
    runner_up_row["metric_value"]
    if runner_up_row is not None
    else np.nan
)

leader_gap_pct = safe_gap_percentage(
    leader_value,
    runner_up_value,
)

ranked_entity_count = (
    current_leaders_df[
        "entity_key"
    ]
    .nunique()
)

average_metric_value = (
    current_leaders_df[
        "metric_value"
    ]
    .mean()
)

maximum_rank = (
    current_leaders_df[
        "rank_position"
    ]
    .max()
)


# ============================================================
# PREVIOUS PERIOD AND RANK MOVEMENT
# ============================================================

current_period_date = (
    current_leaders_df[
        "period_start_date"
    ].max()
)

historical_scope_df = geography_df[
    (
        geography_df["metric_domain"]
        == leader_row["metric_domain"]
    )
    & (
        geography_df["metric_name"]
        == leader_row["metric_name"]
    )
    & (
        geography_df["file_scope"]
        == selected_scope
    )
    & (
        geography_df["geography_level"]
        == selected_level
    )
].copy()

if (
    selected_scope == "state"
    and selected_parent_state
    != "All States and UTs"
):
    historical_scope_df = historical_scope_df[
        historical_scope_df[
            "parent_state_name"
        ]
        == selected_parent_state
    ].copy()

previous_period_dates = (
    historical_scope_df.loc[
        historical_scope_df[
            "period_start_date"
        ]
        < current_period_date,
        "period_start_date",
    ]
    .dropna()
    .sort_values()
    .unique()
)

previous_period_date = (
    previous_period_dates[-1]
    if len(previous_period_dates) > 0
    else None
)

rank_movement_df = pd.DataFrame()

if previous_period_date is not None:
    previous_rank_df = historical_scope_df[
        historical_scope_df[
            "period_start_date"
        ]
        == previous_period_date
    ][
        [
            "entity_key",
            "rank_position",
            "metric_value",
        ]
    ].rename(
        columns={
            "rank_position":
                "previous_rank",
            "metric_value":
                "previous_metric_value",
        }
    )

    current_rank_df = current_leaders_df[
        [
            "entity_key",
            "entity_state_label",
            "rank_position",
            "metric_value",
        ]
    ].rename(
        columns={
            "rank_position":
                "current_rank",
            "metric_value":
                "current_metric_value",
        }
    )

    rank_movement_df = current_rank_df.merge(
        previous_rank_df,
        on="entity_key",
        how="left",
    )

    rank_movement_df["rank_improvement"] = (
        rank_movement_df["previous_rank"]
        - rank_movement_df["current_rank"]
    )

    rank_movement_df[
        "metric_growth_pct"
    ] = np.where(
        rank_movement_df[
            "previous_metric_value"
        ] > 0,
        (
            (
                rank_movement_df[
                    "current_metric_value"
                ]
                / rank_movement_df[
                    "previous_metric_value"
                ]
            )
            - 1
        )
        * 100,
        np.nan,
    )


# ============================================================
# PAGE SUMMARY
# ============================================================

scope_description = selected_scope_name

if (
    selected_scope == "state"
    and selected_parent_state
    != "All States and UTs"
):
    scope_description = (
        f"{selected_parent_state} ranking"
    )

st.markdown(
    f"### {selected_level_name} leaders · "
    f"{selected_period}"
)

st.caption(
    f"{selected_metric_name} · "
    f"{scope_description} · "
    f"{ranked_entity_count:,} ranked entities"
)


# ============================================================
# KPI CARDS
# ============================================================

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = (
    st.columns(4)
)

with kpi_col1:
    render_kpi_card(
        title="Current leader",
        value=leader_name,
        subtitle=selected_metric_name,
        icon="★",
    )

with kpi_col2:
    render_kpi_card(
        title="Leader metric",
        value=format_compact_number(
            leader_value
        ),
        subtitle="Ranked number one",
        icon="↗",
    )

with kpi_col3:
    render_kpi_card(
        title="Lead over runner-up",
        value=(
            f"{leader_gap_pct:.2f}%"
            if leader_gap_pct is not None
            else "—"
        ),
        subtitle=(
            "Difference from rank two"
        ),
        positive=(
            leader_gap_pct is not None
            and leader_gap_pct >= 0
        ),
        icon="△",
    )

with kpi_col4:
    render_kpi_card(
        title="Ranked entities",
        value=f"{ranked_entity_count:,}",
        subtitle=(
            f"Ranks 1 to {maximum_rank:,.0f}"
        ),
        icon="▦",
    )


# ============================================================
# LEADERBOARD VISUALS
# ============================================================

st.markdown("### Leadership comparison")

bar_col, bubble_col = st.columns([1.25, 1])

top_bar_df = (
    current_leaders_df
    .head(20)
    .sort_values(
        "metric_value",
        ascending=True,
    )
)

with bar_col:
    bar_figure = px.bar(
        top_bar_df,
        x="metric_value",
        y="entity_state_label",
        orientation="h",
        color="rank_position",
        color_continuous_scale=[
            "#DDD6FE",
            PHONEPE_LIGHT_PURPLE,
            PHONEPE_PURPLE,
        ],
        labels={
            "metric_value":
                selected_metric_name,
            "entity_state_label":
                selected_level_name,
            "rank_position":
                "Rank",
        },
        title=(
            f"Top {selected_level_name.lower()} "
            f"by {selected_metric_name.lower()}"
        ),
    )

    bar_figure.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Metric value: %{x:,.0f}<br>"
            "Rank: %{marker.color:.0f}"
            "<extra></extra>"
        )
    )

    bar_figure.update_layout(
        coloraxis_showscale=False
    )

    apply_chart_layout(
        bar_figure,
        height=560,
        show_legend=False,
    )

    st.plotly_chart(
        bar_figure,
        use_container_width=True,
    )


with bubble_col:
    bubble_figure = px.scatter(
        current_leaders_df.head(30),
        x="rank_position",
        y="metric_value",
        size="metric_value",
        color="parent_state_name",
        hover_name="entity_state_label",
        size_max=45,
        labels={
            "rank_position":
                "Rank position",
            "metric_value":
                selected_metric_name,
            "parent_state_name":
                "Parent state",
        },
        title=(
            "Rank versus metric scale"
        ),
    )

    bubble_figure.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Rank: %{x:.0f}<br>"
            "Metric value: %{y:,.0f}"
            "<extra></extra>"
        )
    )

    bubble_figure.update_xaxes(
        autorange="reversed"
    )

    apply_chart_layout(
        bubble_figure,
        height=560,
        show_legend=False,
    )

    st.plotly_chart(
        bubble_figure,
        use_container_width=True,
    )


# ============================================================
# TREEMAP
# ============================================================

st.markdown("### Geographic concentration")

treemap_df = current_leaders_df.head(30).copy()

treemap_figure = px.treemap(
    treemap_df,
    path=[
        "parent_state_name",
        "entity_display_name",
    ],
    values="metric_value",
    color="rank_position",
    color_continuous_scale=[
        PHONEPE_PURPLE,
        PHONEPE_LIGHT_PURPLE,
        "#DDD6FE",
    ],
    labels={
        "metric_value":
            selected_metric_name,
        "rank_position":
            "Rank",
    },
    title=(
        "Relative scale of leading geographic entities"
    ),
)

treemap_figure.update_traces(
    hovertemplate=(
        "<b>%{label}</b><br>"
        "Metric value: %{value:,.0f}<br>"
        "Share of displayed hierarchy: "
        "%{percentParent:.2%}"
        "<extra></extra>"
    )
)

treemap_figure.update_layout(
    coloraxis_showscale=False
)

apply_chart_layout(
    treemap_figure,
    height=520,
    show_legend=False,
)

st.plotly_chart(
    treemap_figure,
    use_container_width=True,
)


# ============================================================
# ENTITY HISTORY
# ============================================================

st.markdown("### Entity ranking history")

entity_options = (
    current_leaders_df[
        "entity_state_label"
    ]
    .drop_duplicates()
    .tolist()
)

selected_entity_label = st.selectbox(
    "Select an entity for historical analysis",
    options=entity_options,
    index=0,
    key="leader_selected_entity",
)

selected_entity_row = (
    current_leaders_df[
        current_leaders_df[
            "entity_state_label"
        ]
        == selected_entity_label
    ]
    .iloc[0]
)

selected_entity_key = selected_entity_row[
    "entity_key"
]

entity_history_df = historical_scope_df[
    historical_scope_df["entity_key"]
    == selected_entity_key
].copy()

entity_history_df = (
    entity_history_df
    .sort_values("period_start_date")
)

if entity_history_df.empty:
    st.info(
        "No historical ranking records are available "
        "for the selected entity."
    )

else:
    history_figure = make_subplots(
        specs=[
            [
                {
                    "secondary_y": True
                }
            ]
        ]
    )

    history_figure.add_trace(
        go.Scatter(
            x=entity_history_df[
                "period_start_date"
            ],
            y=entity_history_df[
                "metric_value"
            ],
            mode="lines+markers",
            name=selected_metric_name,
            line=dict(
                color=PHONEPE_PURPLE,
                width=3,
            ),
            marker=dict(size=7),
            customdata=entity_history_df[
                ["period"]
            ],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Metric value: %{y:,.0f}"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    history_figure.add_trace(
        go.Scatter(
            x=entity_history_df[
                "period_start_date"
            ],
            y=entity_history_df[
                "rank_position"
            ],
            mode="lines+markers",
            name="Rank position",
            line=dict(
                color=PHONEPE_GREEN,
                width=3,
                dash="dot",
            ),
            marker=dict(size=7),
            customdata=entity_history_df[
                ["period"]
            ],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Rank: %{y:.0f}"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    history_figure.update_layout(
        title=(
            f"Historical performance · "
            f"{selected_entity_label}"
        )
    )

    history_figure.update_yaxes(
        title_text=selected_metric_name,
        secondary_y=False,
    )

    history_figure.update_yaxes(
        title_text="Rank — lower is better",
        autorange="reversed",
        secondary_y=True,
    )

    apply_chart_layout(
        history_figure,
        height=480,
        show_legend=True,
    )

    st.plotly_chart(
        history_figure,
        use_container_width=True,
    )


# ============================================================
# RANK MOVEMENT
# ============================================================

if not rank_movement_df.empty:
    st.markdown("### Quarter-over-quarter rank movement")

    movement_chart_df = (
        rank_movement_df
        .dropna(
            subset=[
                "rank_improvement"
            ]
        )
        .sort_values(
            "rank_improvement",
            ascending=True,
        )
        .tail(20)
    )

    movement_colours = [
        (
            PHONEPE_GREEN
            if movement >= 0
            else PHONEPE_RED
        )
        for movement in movement_chart_df[
            "rank_improvement"
        ]
    ]

    movement_figure = go.Figure(
        go.Bar(
            x=movement_chart_df[
                "rank_improvement"
            ],
            y=movement_chart_df[
                "entity_state_label"
            ],
            orientation="h",
            marker_color=movement_colours,
            customdata=movement_chart_df[
                [
                    "current_rank",
                    "previous_rank",
                    "metric_growth_pct",
                ]
            ],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Positions gained: %{x:.0f}<br>"
                "Current rank: "
                "%{customdata[0]:.0f}<br>"
                "Previous rank: "
                "%{customdata[1]:.0f}<br>"
                "Metric growth: "
                "%{customdata[2]:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    movement_figure.update_layout(
        title=(
            "Largest rank improvements among "
            "currently ranked entities"
        ),
        xaxis_title=(
            "Rank positions gained"
        ),
        yaxis_title="",
    )

    movement_figure.add_vline(
        x=0,
        line_dash="dash",
        line_color="#94A3B8",
    )

    apply_chart_layout(
        movement_figure,
        height=520,
        show_legend=False,
    )

    st.plotly_chart(
        movement_figure,
        use_container_width=True,
    )


# ============================================================
# DYNAMIC INSIGHTS
# ============================================================

st.markdown("### Geographic intelligence summary")

strongest_riser = None

if not rank_movement_df.empty:
    valid_rank_movements = (
        rank_movement_df
        .dropna(
            subset=[
                "rank_improvement"
            ]
        )
    )

    if not valid_rank_movements.empty:
        strongest_riser = (
            valid_rank_movements
            .nlargest(
                1,
                "rank_improvement",
            )
            .iloc[0]
        )

highest_growth_entity = None

if not rank_movement_df.empty:
    valid_growth_records = (
        rank_movement_df
        .dropna(
            subset=[
                "metric_growth_pct"
            ]
        )
    )

    if not valid_growth_records.empty:
        highest_growth_entity = (
            valid_growth_records
            .nlargest(
                1,
                "metric_growth_pct",
            )
            .iloc[0]
        )

insight_col1, insight_col2, insight_col3 = (
    st.columns(3)
)

with insight_col1:
    render_insight_card(
        title="Geographic leader",
        message=(
            f"{leader_name} ranks first for "
            f"{selected_metric_name.lower()} with "
            f"{format_compact_number(leader_value)}."
        ),
        accent_color=PHONEPE_PURPLE,
        icon="★",
    )

with insight_col2:
    if strongest_riser is not None:
        positions_gained = (
            strongest_riser[
                "rank_improvement"
            ]
        )

        render_insight_card(
            title="Strongest rank movement",
            message=(
                f"{strongest_riser['entity_state_label']} "
                f"gained {positions_gained:.0f} "
                "ranking positions from the "
                "previous quarter."
            ),
            positive=positions_gained >= 0,
            icon="↗",
        )

    else:
        render_insight_card(
            title="Rank movement",
            message=(
                "A previous-period comparison is "
                "not available for this selection."
            ),
            accent_color=PHONEPE_ORANGE,
            icon="◷",
        )

with insight_col3:
    if highest_growth_entity is not None:
        growth_value = (
            highest_growth_entity[
                "metric_growth_pct"
            ]
        )

        render_insight_card(
            title="Fastest metric growth",
            message=(
                f"{highest_growth_entity['entity_state_label']} "
                f"recorded {growth_value:+.2f}% "
                "quarter-over-quarter growth."
            ),
            positive=growth_value >= 0,
            icon="△",
        )

    else:
        render_insight_card(
            title="Leader advantage",
            message=(
                f"The current leader is "
                f"{leader_gap_pct:.2f}% ahead of "
                "the runner-up."
                if leader_gap_pct is not None
                else (
                    "A runner-up comparison is "
                    "not available."
                )
            ),
            accent_color=PHONEPE_BLUE,
            icon="◈",
        )


# ============================================================
# LEADERBOARD TABLE
# ============================================================

st.markdown("### Geographic leaderboard")

leaderboard_df = current_leaders_df[
    [
        "rank_position",
        "entity_display_name",
        "parent_state_name",
        "geography_level_name",
        "metric_display_name",
        "metric_value",
    ]
].copy()

if not rank_movement_df.empty:
    leaderboard_df = leaderboard_df.merge(
        rank_movement_df[
            [
                "entity_state_label",
                "rank_improvement",
                "metric_growth_pct",
            ]
        ],
        left_on=(
            current_leaders_df[
                "entity_state_label"
            ]
        ),
        right_on="entity_state_label",
        how="left",
    )

    drop_columns = [
        column
        for column in [
            "key_0",
            "entity_state_label",
        ]
        if column in leaderboard_df.columns
    ]

    leaderboard_df = leaderboard_df.drop(
        columns=drop_columns
    )

else:
    leaderboard_df[
        "rank_improvement"
    ] = np.nan

    leaderboard_df[
        "metric_growth_pct"
    ] = np.nan

leaderboard_df = leaderboard_df.rename(
    columns={
        "rank_position": "Rank",
        "entity_display_name": "Entity",
        "parent_state_name": "Parent geography",
        "geography_level_name": "Geography level",
        "metric_display_name": "Metric",
        "metric_value": "Metric value",
        "rank_improvement": "Positions gained",
        "metric_growth_pct": "QoQ growth (%)",
    }
)

leaderboard_df = leaderboard_df.sort_values(
    "Rank"
)

st.dataframe(
    leaderboard_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn(
            format="%d"
        ),
        "Metric value":
            st.column_config.NumberColumn(
                format="localized"
            ),
        "Positions gained":
            st.column_config.NumberColumn(
                format="%.0f"
            ),
        "QoQ growth (%)":
            st.column_config.NumberColumn(
                format="%.2f%%"
            ),
    },
    height=520,
)