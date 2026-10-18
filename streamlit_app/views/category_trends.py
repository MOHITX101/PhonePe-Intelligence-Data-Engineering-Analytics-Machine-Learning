"""
Category Trends page.

Analyses PhonePe transaction-category composition, growth,
market share and geographic concentration.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.formatters import (
    format_compact_number,
    format_percentage,
    format_state_name,
)
from components.layout import (
    render_insight_card,
    render_kpi_card,
)
from services.data_loader import (
    load_transaction_category_trends,
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

CATEGORY_COLOURS = [
    PHONEPE_PURPLE,
    PHONEPE_LIGHT_PURPLE,
    PHONEPE_PINK,
    PHONEPE_GREEN,
    PHONEPE_ORANGE,
    PHONEPE_BLUE,
    PHONEPE_RED,
    "#14B8A6",
    "#6366F1",
    "#F97316",
]

TRANSPARENT = "rgba(0,0,0,0)"
GRID_COLOUR = "rgba(95,37,159,0.10)"


# ============================================================
# PAGE HEADER
# ============================================================

st.title("Transaction Category Trends")

st.caption(
    "Analyse transaction-category composition, quarterly growth, "
    "market share and geographic concentration across India."
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_percentage_change(
    current_value,
    previous_value,
):
    """
    Calculate percentage change while safely handling
    missing or zero previous values.
    """

    if (
        current_value is None
        or previous_value is None
        or pd.isna(current_value)
        or pd.isna(previous_value)
        or previous_value == 0
    ):
        return None

    return (
        (current_value - previous_value)
        / previous_value
    ) * 100


def clean_category_name(value):
    """
    Convert category values into readable labels.
    """

    if value is None or pd.isna(value):
        return "Unknown category"

    return (
        str(value)
        .replace("_", " ")
        .replace("-", " ")
        .strip()
        .title()
    )


def apply_chart_layout(
    figure,
    height=430,
    show_legend=True,
):
    """
    Apply the common dashboard chart style.
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


def prepare_category_data(raw_df):
    """
    Clean and enrich the transaction-category dataset.
    """

    category_df = raw_df.copy()

    category_df["period_start_date"] = pd.to_datetime(
        category_df["period_start_date"],
        errors="coerce",
    )

    numeric_columns = [
        "year",
        "quarter",
        "category_transaction_count",
        "geography_total_transaction_count",
        "category_share_pct",
        "category_rank",
    ]

    for column in numeric_columns:
        if column in category_df.columns:
            category_df[column] = pd.to_numeric(
                category_df[column],
                errors="coerce",
            )

    category_df["category_name"] = (
        category_df["transaction_category"]
        .apply(clean_category_name)
    )

    category_df["geography_name"] = np.where(
        category_df["file_scope"] == "country",
        "India",
        category_df["geography_slug"].apply(
            format_state_name
        ),
    )

    category_df["geography_key"] = (
        category_df["file_scope"].astype(str)
        + "|"
        + category_df["geography_slug"].astype(str)
    )

    return category_df


# ============================================================
# LOAD DATA
# ============================================================

try:
    with st.spinner(
        "Loading category trends from Databricks..."
    ):
        raw_category_df = (
            load_transaction_category_trends()
        )

except Exception as error:
    st.error(
        "The Category Trends page could not load "
        "data from Databricks."
    )

    st.exception(error)
    st.stop()


if raw_category_df.empty:
    st.warning(
        "The transaction-category table returned no rows."
    )
    st.stop()


category_df = prepare_category_data(
    raw_category_df
)


# ============================================================
# FILTER OPTIONS
# ============================================================

period_lookup = (
    category_df[
        [
            "period",
            "period_start_date",
        ]
    ]
    .drop_duplicates()
    .dropna(
        subset=[
            "period",
            "period_start_date",
        ]
    )
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

geography_lookup = (
    category_df[
        [
            "file_scope",
            "geography_slug",
            "geography_name",
            "geography_key",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        [
            "file_scope",
            "geography_name",
        ]
    )
)

geography_label_to_key = dict(
    zip(
        geography_lookup["geography_name"],
        geography_lookup["geography_key"],
    )
)

geography_options = []

if "India" in geography_label_to_key:
    geography_options.append("India")

geography_options.extend(
    sorted(
        [
            geography
            for geography in geography_label_to_key
            if geography != "India"
        ]
    )
)


# ============================================================
# FILTER PANEL
# ============================================================

with st.container(border=True):
    st.markdown("#### Dashboard filters")

    filter_col1, filter_col2, filter_col3 = (
        st.columns([1, 1.4, 1.4])
    )

    with filter_col1:
        selected_period = st.selectbox(
            "Reporting quarter",
            options=period_options,
            index=0,
            key="category_selected_period",
        )

    with filter_col2:
        selected_geography = st.selectbox(
            "Geography",
            options=geography_options,
            index=0,
            key="category_selected_geography",
        )

    selected_geography_key = (
        geography_label_to_key[selected_geography]
    )

    selected_scope, selected_geography_slug = (
        selected_geography_key.split(
            "|",
            maxsplit=1,
        )
    )

    current_geography_df = category_df[
        (
            category_df["file_scope"]
            == selected_scope
        )
        & (
            category_df["geography_slug"]
            == selected_geography_slug
        )
        & (
            category_df["period"]
            == selected_period
        )
    ].copy()

    available_category_lookup = (
        current_geography_df[
            [
                "transaction_category",
                "category_name",
            ]
        ]
        .drop_duplicates()
        .sort_values("category_name")
    )

    category_name_to_value = dict(
        zip(
            available_category_lookup[
                "category_name"
            ],
            available_category_lookup[
                "transaction_category"
            ],
        )
    )

    category_options = [
        "All Categories"
    ] + list(category_name_to_value.keys())

    with filter_col3:
        selected_category_name = st.selectbox(
            "Transaction category",
            options=category_options,
            index=0,
            key="category_selected_category",
        )


if current_geography_df.empty:
    st.warning(
        "No category records are available for the "
        "selected quarter and geography."
    )
    st.stop()


selected_category_value = None

if selected_category_name != "All Categories":
    selected_category_value = (
        category_name_to_value[
            selected_category_name
        ]
    )


# ============================================================
# HISTORICAL GEOGRAPHY DATA
# ============================================================

geography_history_df = category_df[
    (
        category_df["file_scope"]
        == selected_scope
    )
    & (
        category_df["geography_slug"]
        == selected_geography_slug
    )
].copy()

geography_history_df = (
    geography_history_df
    .sort_values("period_start_date")
)


# ============================================================
# CURRENT AND PREVIOUS PERIOD
# ============================================================

selected_period_date = (
    current_geography_df[
        "period_start_date"
    ].max()
)

previous_period_dates = (
    geography_history_df.loc[
        geography_history_df[
            "period_start_date"
        ]
        < selected_period_date,
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

previous_geography_df = pd.DataFrame()

if previous_period_date is not None:
    previous_geography_df = (
        geography_history_df[
            geography_history_df[
                "period_start_date"
            ]
            == previous_period_date
        ]
        .copy()
    )


# ============================================================
# FILTERED KPI DATA
# ============================================================

if selected_category_value is None:
    current_kpi_df = current_geography_df.copy()
    previous_kpi_df = previous_geography_df.copy()

else:
    current_kpi_df = current_geography_df[
        current_geography_df[
            "transaction_category"
        ]
        == selected_category_value
    ].copy()

    previous_kpi_df = previous_geography_df[
        previous_geography_df[
            "transaction_category"
        ]
        == selected_category_value
    ].copy()


current_transaction_count = (
    current_kpi_df[
        "category_transaction_count"
    ].sum(min_count=1)
)

previous_transaction_count = (
    previous_kpi_df[
        "category_transaction_count"
    ].sum(min_count=1)
    if not previous_kpi_df.empty
    else np.nan
)

transaction_growth_pct = (
    safe_percentage_change(
        current_transaction_count,
        previous_transaction_count,
    )
)

if selected_category_value is None:
    selected_category_share = 100.0

else:
    selected_category_share = (
        current_kpi_df[
            "category_share_pct"
        ].iloc[0]
        if not current_kpi_df.empty
        else np.nan
    )

leading_category_row = (
    current_geography_df
    .dropna(
        subset=[
            "category_transaction_count"
        ]
    )
    .nlargest(
        1,
        "category_transaction_count",
    )
    .iloc[0]
)

leading_category_name = (
    leading_category_row["category_name"]
)

leading_category_share = (
    leading_category_row["category_share_pct"]
)

active_category_count = (
    current_geography_df[
        "transaction_category"
    ]
    .nunique()
)

average_category_count = (
    current_geography_df[
        "category_transaction_count"
    ]
    .mean()
)


# ============================================================
# PAGE SUMMARY
# ============================================================

st.markdown(
    f"### {selected_geography} category performance "
    f"· {selected_period}"
)

if selected_category_name == "All Categories":
    st.caption(
        f"Showing the complete transaction mix across "
        f"{active_category_count:,} categories."
    )

else:
    st.caption(
        f"Detailed trend analysis for "
        f"{selected_category_name}."
    )


# ============================================================
# KPI CARDS
# ============================================================

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = (
    st.columns(4)
)

with kpi_col1:
    render_kpi_card(
        title="Transaction volume",
        value=format_compact_number(
            current_transaction_count
        ),
        delta=format_percentage(
            transaction_growth_pct
        ),
        subtitle="Quarter-over-quarter",
        positive=(
            transaction_growth_pct is not None
            and transaction_growth_pct >= 0
        ),
        icon="↗",
    )

with kpi_col2:
    render_kpi_card(
        title="Selected category share",
        value=(
            f"{selected_category_share:.2f}%"
            if pd.notna(selected_category_share)
            else "—"
        ),
        subtitle=(
            selected_category_name
            if selected_category_value
            else "Complete transaction mix"
        ),
        icon="◔",
    )

with kpi_col3:
    render_kpi_card(
        title="Leading category",
        value=leading_category_name,
        subtitle=(
            f"{leading_category_share:.2f}% "
            "of transaction volume"
        ),
        icon="★",
    )

with kpi_col4:
    render_kpi_card(
        title="Active categories",
        value=f"{active_category_count:,}",
        subtitle=(
            "Categories with transaction activity"
        ),
        icon="▦",
    )


# ============================================================
# TRANSACTION MIX AND TREND
# ============================================================

st.markdown("### Category mix and historical movement")

mix_col, trend_col = st.columns([0.9, 1.5])

category_mix_df = (
    current_geography_df
    .dropna(
        subset=[
            "category_transaction_count"
        ]
    )
    .sort_values(
        "category_transaction_count",
        ascending=False,
    )
)

with mix_col:
    mix_figure = px.pie(
        category_mix_df,
        names="category_name",
        values="category_transaction_count",
        hole=0.62,
        color="category_name",
        color_discrete_sequence=CATEGORY_COLOURS,
        title="Current category composition",
    )

    mix_figure.update_traces(
        textposition="inside",
        textinfo="percent",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Transactions: %{value:,.0f}<br>"
            "Share: %{percent}"
            "<extra></extra>"
        ),
        marker=dict(
            line=dict(
                color="#FFFFFF",
                width=2,
            )
        ),
    )

    mix_figure.add_annotation(
        text=(
            f"<b>{format_compact_number(current_geography_df['category_transaction_count'].sum())}</b>"
            "<br><span style='font-size:11px'>transactions</span>"
        ),
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(
            color="#24152F",
            size=17,
        ),
    )

    apply_chart_layout(
        mix_figure,
        height=480,
        show_legend=True,
    )

    mix_figure.update_layout(
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
        )
    )

    st.plotly_chart(
        mix_figure,
        use_container_width=True,
    )


if selected_category_value is not None:
    trend_categories = [
        selected_category_value
    ]

else:
    trend_categories = (
        category_mix_df
        .nlargest(
            5,
            "category_transaction_count",
        )[
            "transaction_category"
        ]
        .tolist()
    )

category_trend_df = geography_history_df[
    geography_history_df[
        "transaction_category"
    ]
    .isin(trend_categories)
].copy()

with trend_col:
    trend_figure = px.line(
        category_trend_df,
        x="period_start_date",
        y="category_transaction_count",
        color="category_name",
        markers=True,
        color_discrete_sequence=CATEGORY_COLOURS,
        labels={
            "period_start_date": "Quarter",
            "category_transaction_count":
                "Transaction count",
            "category_name":
                "Transaction category",
        },
        title="Quarterly category transaction trajectory",
        custom_data=[
            "period",
        ],
    )

    trend_figure.update_traces(
        line=dict(width=3),
        marker=dict(size=7),
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "Quarter: %{customdata[0]}<br>"
            "Transactions: %{y:,.0f}"
            "<extra></extra>"
        ),
    )

    apply_chart_layout(
        trend_figure,
        height=480,
        show_legend=True,
    )

    st.plotly_chart(
        trend_figure,
        use_container_width=True,
    )


# ============================================================
# SHARE TREND
# ============================================================

st.markdown("### Category share evolution")

share_figure = px.area(
    category_trend_df,
    x="period_start_date",
    y="category_share_pct",
    color="category_name",
    color_discrete_sequence=CATEGORY_COLOURS,
    labels={
        "period_start_date": "Quarter",
        "category_share_pct":
            "Share of transactions (%)",
        "category_name":
            "Transaction category",
    },
    title=(
        "Quarterly movement in category market share"
    ),
    custom_data=[
        "period",
        "category_transaction_count",
    ],
)

share_figure.update_traces(
    hovertemplate=(
        "<b>%{fullData.name}</b><br>"
        "Quarter: %{customdata[0]}<br>"
        "Share: %{y:.2f}%<br>"
        "Transactions: %{customdata[1]:,.0f}"
        "<extra></extra>"
    )
)

apply_chart_layout(
    share_figure,
    height=460,
    show_legend=True,
)

st.plotly_chart(
    share_figure,
    use_container_width=True,
)


# ============================================================
# CATEGORY GROWTH CALCULATION
# ============================================================

current_growth_df = current_geography_df[
    [
        "transaction_category",
        "category_name",
        "category_transaction_count",
    ]
].rename(
    columns={
        "category_transaction_count":
            "current_transaction_count"
    }
)

previous_growth_df = previous_geography_df[
    [
        "transaction_category",
        "category_transaction_count",
    ]
].rename(
    columns={
        "category_transaction_count":
            "previous_transaction_count"
    }
)

category_growth_df = current_growth_df.merge(
    previous_growth_df,
    on="transaction_category",
    how="left",
)

category_growth_df["qoq_growth_pct"] = np.where(
    category_growth_df[
        "previous_transaction_count"
    ] > 0,
    (
        (
            category_growth_df[
                "current_transaction_count"
            ]
            / category_growth_df[
                "previous_transaction_count"
            ]
        )
        - 1
    )
    * 100,
    np.nan,
)

category_growth_df = category_growth_df.sort_values(
    "qoq_growth_pct",
    ascending=False,
)


# ============================================================
# GROWTH AND STATE COMPARISON
# ============================================================

st.markdown("### Growth and geographic comparison")

growth_col, geography_col = st.columns(2)

with growth_col:
    growth_chart_df = (
        category_growth_df
        .dropna(subset=["qoq_growth_pct"])
        .sort_values(
            "qoq_growth_pct",
            ascending=True,
        )
    )

    growth_colours = [
        (
            PHONEPE_GREEN
            if value >= 0
            else PHONEPE_RED
        )
        for value in growth_chart_df[
            "qoq_growth_pct"
        ]
    ]

    growth_figure = go.Figure(
        go.Bar(
            x=growth_chart_df[
                "qoq_growth_pct"
            ],
            y=growth_chart_df[
                "category_name"
            ],
            orientation="h",
            marker_color=growth_colours,
            customdata=growth_chart_df[
                [
                    "current_transaction_count",
                    "previous_transaction_count",
                ]
            ],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "QoQ growth: %{x:.2f}%<br>"
                "Current: %{customdata[0]:,.0f}<br>"
                "Previous: %{customdata[1]:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    growth_figure.update_layout(
        title="Quarter-over-quarter category growth",
        xaxis_title="QoQ growth (%)",
        yaxis_title="",
    )

    growth_figure.add_vline(
        x=0,
        line_dash="dash",
        line_color="#94A3B8",
    )

    apply_chart_layout(
        growth_figure,
        height=470,
        show_legend=False,
    )

    st.plotly_chart(
        growth_figure,
        use_container_width=True,
    )


comparison_category_value = (
    selected_category_value
    if selected_category_value is not None
    else leading_category_row[
        "transaction_category"
    ]
)

comparison_category_name = (
    selected_category_name
    if selected_category_value is not None
    else leading_category_name
)

state_comparison_df = category_df[
    (
        category_df["period"]
        == selected_period
    )
    & (
        category_df["file_scope"]
        == "state"
    )
    & (
        category_df["transaction_category"]
        == comparison_category_value
    )
].copy()

state_comparison_df = (
    state_comparison_df
    .dropna(
        subset=[
            "category_transaction_count"
        ]
    )
    .nlargest(
        15,
        "category_transaction_count",
    )
    .sort_values(
        "category_transaction_count",
        ascending=True,
    )
)

with geography_col:
    state_figure = px.bar(
        state_comparison_df,
        x="category_transaction_count",
        y="geography_name",
        orientation="h",
        color="category_share_pct",
        color_continuous_scale=[
            "#DDD6FE",
            PHONEPE_LIGHT_PURPLE,
            PHONEPE_PURPLE,
        ],
        labels={
            "category_transaction_count":
                "Transaction count",
            "geography_name":
                "State / UT",
            "category_share_pct":
                "State share %",
        },
        title=(
            f"Top states · {comparison_category_name}"
        ),
    )

    state_figure.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Transactions: %{x:,.0f}<br>"
            "State category share: "
            "%{marker.color:.2f}%"
            "<extra></extra>"
        )
    )

    state_figure.update_layout(
        coloraxis_showscale=False
    )

    apply_chart_layout(
        state_figure,
        height=470,
        show_legend=False,
    )

    st.plotly_chart(
        state_figure,
        use_container_width=True,
    )


# ============================================================
# STATE CATEGORY HEATMAP
# ============================================================

st.markdown("### State category concentration")

current_state_categories_df = category_df[
    (
        category_df["period"]
        == selected_period
    )
    & (
        category_df["file_scope"]
        == "state"
    )
].copy()

top_state_names = (
    current_state_categories_df[
        [
            "geography_name",
            "geography_total_transaction_count",
        ]
    ]
    .drop_duplicates()
    .nlargest(
        12,
        "geography_total_transaction_count",
    )[
        "geography_name"
    ]
    .tolist()
)

heatmap_source_df = (
    current_state_categories_df[
        current_state_categories_df[
            "geography_name"
        ]
        .isin(top_state_names)
    ]
)

heatmap_pivot = heatmap_source_df.pivot_table(
    index="geography_name",
    columns="category_name",
    values="category_share_pct",
    aggfunc="first",
)

heatmap_pivot = heatmap_pivot.reindex(
    top_state_names
)

heatmap_figure = go.Figure(
    data=go.Heatmap(
        z=heatmap_pivot.values,
        x=heatmap_pivot.columns.tolist(),
        y=heatmap_pivot.index.tolist(),
        colorscale=[
            [0.0, "#F5F3FF"],
            [0.35, "#C4B5FD"],
            [0.70, "#8B5CF6"],
            [1.0, PHONEPE_PURPLE],
        ],
        colorbar=dict(
            title="Share %",
        ),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Category: %{x}<br>"
            "Share: %{z:.2f}%"
            "<extra></extra>"
        ),
    )
)

heatmap_figure.update_layout(
    title=(
        "Category share across the largest state markets"
    ),
    xaxis_title="Transaction category",
    yaxis_title="State / UT",
)

apply_chart_layout(
    heatmap_figure,
    height=520,
    show_legend=False,
)

st.plotly_chart(
    heatmap_figure,
    use_container_width=True,
)


# ============================================================
# DYNAMIC INSIGHTS
# ============================================================

st.markdown("### Category intelligence summary")

fastest_growth_row = None

valid_growth_df = category_growth_df.dropna(
    subset=["qoq_growth_pct"]
)

if not valid_growth_df.empty:
    fastest_growth_row = (
        valid_growth_df
        .nlargest(
            1,
            "qoq_growth_pct",
        )
        .iloc[0]
    )

highest_state_share_row = None

if not state_comparison_df.empty:
    highest_state_share_row = (
        state_comparison_df
        .nlargest(
            1,
            "category_share_pct",
        )
        .iloc[0]
    )

insight_col1, insight_col2, insight_col3 = (
    st.columns(3)
)

with insight_col1:
    render_insight_card(
        title="Category leader",
        message=(
            f"{leading_category_name} leads "
            f"{selected_geography} with "
            f"{leading_category_share:.2f}% of "
            "transaction volume."
        ),
        accent_color=PHONEPE_PURPLE,
        icon="★",
    )

with insight_col2:
    if fastest_growth_row is not None:
        fastest_growth_value = (
            fastest_growth_row[
                "qoq_growth_pct"
            ]
        )

        render_insight_card(
            title="Fastest quarterly growth",
            message=(
                f"{fastest_growth_row['category_name']} "
                f"changed by "
                f"{fastest_growth_value:+.2f}% "
                "from the previous quarter."
            ),
            positive=fastest_growth_value >= 0,
            icon="↗",
        )

with insight_col3:
    if highest_state_share_row is not None:
        render_insight_card(
            title="Highest state concentration",
            message=(
                f"{highest_state_share_row['geography_name']} "
                f"has the highest {comparison_category_name} "
                f"share at "
                f"{highest_state_share_row['category_share_pct']:.2f}%."
            ),
            accent_color=PHONEPE_GREEN,
            icon="⌖",
        )


# ============================================================
# CATEGORY LEADERBOARD
# ============================================================

st.markdown("### Category leaderboard")

leaderboard_df = (
    current_geography_df[
        [
            "category_rank",
            "category_name",
            "category_transaction_count",
            "category_share_pct",
        ]
    ]
    .merge(
        category_growth_df[
            [
                "transaction_category",
                "qoq_growth_pct",
            ]
        ],
        left_on=current_geography_df[
            "transaction_category"
        ],
        right_on=category_growth_df[
            "transaction_category"
        ],
        how="left",
    )
)

drop_columns = [
    column
    for column in [
        "key_0",
        "transaction_category",
    ]
    if column in leaderboard_df.columns
]

leaderboard_df = leaderboard_df.drop(
    columns=drop_columns
)

leaderboard_df = leaderboard_df.sort_values(
    [
        "category_rank",
        "category_transaction_count",
    ],
    ascending=[
        True,
        False,
    ],
)

leaderboard_df = leaderboard_df.rename(
    columns={
        "category_rank": "Rank",
        "category_name": "Transaction category",
        "category_transaction_count":
            "Transaction count",
        "category_share_pct":
            "Category share (%)",
        "qoq_growth_pct":
            "QoQ growth (%)",
    }
)

st.dataframe(
    leaderboard_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn(
            format="%d"
        ),
        "Transaction count":
            st.column_config.NumberColumn(
                format="localized"
            ),
        "Category share (%)":
            st.column_config.ProgressColumn(
                format="%.2f%%",
                min_value=0,
                max_value=100,
            ),
        "QoQ growth (%)":
            st.column_config.NumberColumn(
                format="%.2f%%"
            ),
    },
    height=400,
)