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
    load_district_quarterly_performance,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

PHONEPE_PURPLE = "#5F259F"
PHONEPE_LIGHT_PURPLE = "#A855F7"
PHONEPE_PINK = "#EC4899"
PHONEPE_GREEN = "#10B981"
PHONEPE_ORANGE = "#F59E0B"
PHONEPE_RED = "#EF4444"
PHONEPE_BLUE = "#3B82F6"
PHONEPE_MUTED = "#94A3B8"

PLOT_BACKGROUND = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(148,163,184,0.16)"

st.title("District Intelligence")

st.caption(
    "Explore district-level transaction activity, monetary value, "
    "digital adoption and geographic performance."
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_percentage_change(
    current_value,
    previous_value,
):
    if (
        previous_value is None
        or pd.isna(previous_value)
        or previous_value == 0
        or current_value is None
        or pd.isna(current_value)
    ):
        return None

    return (
        (current_value - previous_value)
        / previous_value
    ) * 100


def format_currency_compact(value):
    if value is None or pd.isna(value):
        return "—"

    absolute_value = abs(float(value))

    if absolute_value >= 1_00_00_00_00_000:
        return f"₹{value / 1_00_00_00_00_000:.2f}T"

    if absolute_value >= 1_00_00_000:
        return f"₹{value / 1_00_00_000:.2f}Cr"

    if absolute_value >= 1_00_000:
        return f"₹{value / 1_00_000:.2f}L"

    if absolute_value >= 1_000:
        return f"₹{value / 1_000:.1f}K"

    return f"₹{value:,.0f}"


def prepare_district_data(raw_df):
    district_df = raw_df.copy()

    district_df["period_start_date"] = pd.to_datetime(
        district_df["period_start_date"],
        errors="coerce",
    )

    numeric_columns = [
        "year",
        "quarter",
        "total_transaction_count",
        "total_transaction_amount",
        "average_transaction_value",
        "registered_user_count",
        "registered_merchant_count",
        "national_transaction_count_rank",
        "national_transaction_amount_rank",
        "state_transaction_count_rank",
        "state_transaction_amount_rank",
    ]

    for column in numeric_columns:
        if column in district_df.columns:
            district_df[column] = pd.to_numeric(
                district_df[column],
                errors="coerce",
            )

    district_df["state_name"] = (
        district_df["state_slug"]
        .fillna("Unknown")
        .apply(format_state_name)
    )

    district_df["district_display_name"] = (
        district_df["district_name"]
        .fillna(
            district_df["district_slug"]
            .str.replace("-", " ", regex=False)
        )
        .str.title()
    )

    district_df["district_state_label"] = (
        district_df["district_display_name"]
        + ", "
        + district_df["state_name"]
    )

    district_df["transactions_per_user"] = np.where(
        district_df["registered_user_count"] > 0,
        (
            district_df["total_transaction_count"]
            / district_df["registered_user_count"]
        ),
        np.nan,
    )

    district_df["transactions_per_merchant"] = np.where(
        district_df["registered_merchant_count"] > 0,
        (
            district_df["total_transaction_count"]
            / district_df["registered_merchant_count"]
        ),
        np.nan,
    )

    district_df["transaction_amount_per_user"] = np.where(
        district_df["registered_user_count"] > 0,
        (
            district_df["total_transaction_amount"]
            / district_df["registered_user_count"]
        ),
        np.nan,
    )

    return district_df


def apply_chart_layout(
    figure,
    height=430,
    show_legend=True,
):
    figure.update_layout(
        height=height,
        margin=dict(
            l=10,
            r=10,
            t=50,
            b=10,
        ),
        paper_bgcolor=PLOT_BACKGROUND,
        plot_bgcolor=PLOT_BACKGROUND,
        font=dict(
            family="Inter, sans-serif",
            color="#E2E8F0",
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
            bgcolor="#1E1B2E",
            font_color="#FFFFFF",
            bordercolor=PHONEPE_PURPLE,
        ),
    )

    figure.update_xaxes(
        showgrid=False,
        zeroline=False,
    )

    figure.update_yaxes(
        gridcolor=GRID_COLOR,
        zeroline=False,
    )

    return figure


# ============================================================
# LOAD DATA
# ============================================================

try:
    with st.spinner(
        "Loading district intelligence from Databricks..."
    ):
        raw_district_df = (
            load_district_quarterly_performance()
        )

except Exception as error:
    st.error(
        "The District Intelligence page could not load "
        "data from Databricks."
    )

    st.exception(error)
    st.stop()


if raw_district_df.empty:
    st.warning(
        "The district performance table returned no rows."
    )
    st.stop()


district_df = prepare_district_data(
    raw_district_df
)


# ============================================================
# FILTERS
# ============================================================

available_periods = (
    district_df[
        [
            "period",
            "period_start_date",
        ]
    ]
    .drop_duplicates()
    .dropna(subset=["period"])
    .sort_values(
        "period_start_date",
        ascending=False,
    )
)

period_options = (
    available_periods["period"]
    .astype(str)
    .tolist()
)

available_states = (
    district_df[
        [
            "state_slug",
            "state_name",
        ]
    ]
    .drop_duplicates()
    .sort_values("state_name")
)

state_name_to_slug = dict(
    zip(
        available_states["state_name"],
        available_states["state_slug"],
    )
)

with st.container(border=True):
    st.markdown("#### Dashboard filters")

    filter_col1, filter_col2, filter_col3 = (
        st.columns([1, 1.3, 1.5])
    )

    with filter_col1:
        selected_period = st.selectbox(
            "Quarter",
            options=period_options,
            index=0,
            key="district_selected_period",
        )

    with filter_col2:
        state_options = [
            "All States and UTs"
        ] + list(state_name_to_slug.keys())

        selected_state_name = st.selectbox(
            "State / Union Territory",
            options=state_options,
            index=0,
            key="district_selected_state",
        )

    period_state_df = district_df[
        district_df["period"] == selected_period
    ].copy()

    if selected_state_name != "All States and UTs":
        selected_state_slug = state_name_to_slug[
            selected_state_name
        ]

        period_state_df = period_state_df[
            period_state_df["state_slug"]
            == selected_state_slug
        ].copy()

    available_district_labels = sorted(
        period_state_df[
            "district_state_label"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    with filter_col3:
        district_options = [
            "All Districts"
        ] + available_district_labels

        selected_district_label = st.selectbox(
            "District",
            options=district_options,
            index=0,
            key="district_selected_district",
        )


selected_period_df = district_df[
    district_df["period"] == selected_period
].copy()

if selected_state_name != "All States and UTs":
    selected_state_slug = state_name_to_slug[
        selected_state_name
    ]

    selected_period_df = selected_period_df[
        selected_period_df["state_slug"]
        == selected_state_slug
    ].copy()

if selected_district_label != "All Districts":
    selected_period_df = selected_period_df[
        selected_period_df["district_state_label"]
        == selected_district_label
    ].copy()


if selected_period_df.empty:
    st.warning(
        "No district data is available for the selected filters."
    )
    st.stop()


# ============================================================
# PREVIOUS PERIOD COMPARISON
# ============================================================

current_period_date = (
    selected_period_df["period_start_date"].max()
)

all_previous_dates = (
    district_df.loc[
        district_df["period_start_date"]
        < current_period_date,
        "period_start_date",
    ]
    .dropna()
    .sort_values()
    .unique()
)

previous_period_date = (
    all_previous_dates[-1]
    if len(all_previous_dates) > 0
    else None
)

previous_period_df = pd.DataFrame()

if previous_period_date is not None:
    previous_period_df = district_df[
        district_df["period_start_date"]
        == previous_period_date
    ].copy()

    if selected_state_name != "All States and UTs":
        previous_period_df = previous_period_df[
            previous_period_df["state_slug"]
            == selected_state_slug
        ].copy()

    if selected_district_label != "All Districts":
        previous_period_df = previous_period_df[
            previous_period_df[
                "district_state_label"
            ]
            == selected_district_label
        ].copy()


# ============================================================
# KPI CALCULATIONS
# ============================================================

current_transaction_count = (
    selected_period_df[
        "total_transaction_count"
    ].sum(min_count=1)
)

current_transaction_amount = (
    selected_period_df[
        "total_transaction_amount"
    ].sum(min_count=1)
)

current_users = (
    selected_period_df[
        "registered_user_count"
    ].sum(min_count=1)
)

current_merchants = (
    selected_period_df[
        "registered_merchant_count"
    ].sum(min_count=1)
)

current_average_transaction_value = (
    current_transaction_amount
    / current_transaction_count
    if (
        pd.notna(current_transaction_amount)
        and pd.notna(current_transaction_count)
        and current_transaction_count > 0
    )
    else np.nan
)

district_count = (
    selected_period_df["district_slug"]
    .nunique()
)

previous_transaction_count = (
    previous_period_df[
        "total_transaction_count"
    ].sum(min_count=1)
    if not previous_period_df.empty
    else np.nan
)

previous_transaction_amount = (
    previous_period_df[
        "total_transaction_amount"
    ].sum(min_count=1)
    if not previous_period_df.empty
    else np.nan
)

previous_users = (
    previous_period_df[
        "registered_user_count"
    ].sum(min_count=1)
    if not previous_period_df.empty
    else np.nan
)

previous_merchants = (
    previous_period_df[
        "registered_merchant_count"
    ].sum(min_count=1)
    if not previous_period_df.empty
    else np.nan
)

transaction_count_growth = safe_percentage_change(
    current_transaction_count,
    previous_transaction_count,
)

transaction_amount_growth = safe_percentage_change(
    current_transaction_amount,
    previous_transaction_amount,
)

user_growth = safe_percentage_change(
    current_users,
    previous_users,
)

merchant_growth = safe_percentage_change(
    current_merchants,
    previous_merchants,
)


# ============================================================
# PAGE SUMMARY
# ============================================================

scope_label = selected_state_name

if selected_district_label != "All Districts":
    scope_label = selected_district_label

elif selected_state_name == "All States and UTs":
    scope_label = "India district network"

st.markdown(
    f"### {scope_label} · {selected_period}"
)

st.caption(
    f"Displaying {district_count:,} districts for the "
    "selected geographic scope."
)


# ============================================================
# KPI CARDS
# ============================================================

kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

with kpi_col1:
    render_kpi_card(
        title="Transaction volume",
        value=format_compact_number(
            current_transaction_count
        ),
        delta=format_percentage(
            transaction_count_growth
        ),
        subtitle="Quarter-over-quarter",
        icon="↗",
    )

with kpi_col2:
    render_kpi_card(
        title="Transaction value",
        value=format_currency_compact(
            current_transaction_amount
        ),
        delta=format_percentage(
            transaction_amount_growth
        ),
        subtitle="Quarter-over-quarter",
        icon="₹",
    )

with kpi_col3:
    render_kpi_card(
        title="Average transaction",
        value=format_currency_compact(
            current_average_transaction_value
        ),
        subtitle="Value per transaction",
        icon="◈",
    )

kpi_col4, kpi_col5, kpi_col6 = st.columns(3)

with kpi_col4:
    render_kpi_card(
        title="Registered users",
        value=format_compact_number(
            current_users
        ),
        delta=format_percentage(
            user_growth
        ),
        subtitle="Quarter-over-quarter",
        icon="◉",
    )

with kpi_col5:
    render_kpi_card(
        title="Registered merchants",
        value=format_compact_number(
            current_merchants
        ),
        delta=format_percentage(
            merchant_growth
        ),
        subtitle="Quarter-over-quarter",
        icon="◆",
    )

with kpi_col6:
    render_kpi_card(
        title="District coverage",
        value=f"{district_count:,}",
        subtitle="Districts represented",
        icon="⌖",
    )


# ============================================================
# TOP DISTRICTS
# ============================================================

st.markdown("### District leaders")

leader_col1, leader_col2 = st.columns(2)

top_transaction_districts = (
    selected_period_df
    .dropna(
        subset=[
            "total_transaction_count",
            "district_state_label",
        ]
    )
    .nlargest(
        15,
        "total_transaction_count",
    )
    .sort_values(
        "total_transaction_count",
        ascending=True,
    )
)

with leader_col1:
    transaction_figure = px.bar(
        top_transaction_districts,
        x="total_transaction_count",
        y="district_state_label",
        orientation="h",
        color="total_transaction_count",
        color_continuous_scale=[
            "#C4B5FD",
            PHONEPE_PURPLE,
            "#3B0764",
        ],
        labels={
            "total_transaction_count":
                "Transaction count",
            "district_state_label":
                "District",
        },
        title="Top districts by transaction volume",
    )

    transaction_figure.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Transactions: %{x:,.0f}"
            "<extra></extra>"
        )
    )

    transaction_figure.update_layout(
        coloraxis_showscale=False
    )

    apply_chart_layout(
        transaction_figure,
        height=520,
        show_legend=False,
    )

    st.plotly_chart(
        transaction_figure,
        use_container_width=True,
    )

top_value_districts = (
    selected_period_df
    .dropna(
        subset=[
            "total_transaction_amount",
            "district_state_label",
        ]
    )
    .nlargest(
        15,
        "total_transaction_amount",
    )
    .sort_values(
        "total_transaction_amount",
        ascending=True,
    )
)

with leader_col2:
    value_figure = px.bar(
        top_value_districts,
        x="total_transaction_amount",
        y="district_state_label",
        orientation="h",
        color="total_transaction_amount",
        color_continuous_scale=[
            "#FBCFE8",
            PHONEPE_PINK,
            "#831843",
        ],
        labels={
            "total_transaction_amount":
                "Transaction value",
            "district_state_label":
                "District",
        },
        title="Top districts by transaction value",
    )

    value_figure.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Transaction value: ₹%{x:,.0f}"
            "<extra></extra>"
        )
    )

    value_figure.update_layout(
        coloraxis_showscale=False
    )

    apply_chart_layout(
        value_figure,
        height=520,
        show_legend=False,
    )

    st.plotly_chart(
        value_figure,
        use_container_width=True,
    )


# ============================================================
# ADOPTION AND VALUE ANALYSIS
# ============================================================

st.markdown("### Adoption and economic activity")

analysis_col1, analysis_col2 = st.columns(2)

scatter_df = selected_period_df.dropna(
    subset=[
        "registered_user_count",
        "total_transaction_count",
        "district_state_label",
    ]
).copy()

with analysis_col1:
    adoption_figure = px.scatter(
        scatter_df,
        x="registered_user_count",
        y="total_transaction_count",
        size="total_transaction_amount",
        color="state_name",
        hover_name="district_state_label",
        size_max=38,
        labels={
            "registered_user_count":
                "Registered users",
            "total_transaction_count":
                "Transaction count",
            "state_name":
                "State / UT",
        },
        title=(
            "Registered users versus transaction activity"
        ),
    )

    adoption_figure.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Users: %{x:,.0f}<br>"
            "Transactions: %{y:,.0f}"
            "<extra></extra>"
        )
    )

    apply_chart_layout(
        adoption_figure,
        height=500,
        show_legend=False,
    )

    st.plotly_chart(
        adoption_figure,
        use_container_width=True,
    )

value_scatter_df = selected_period_df.dropna(
    subset=[
        "average_transaction_value",
        "total_transaction_count",
        "district_state_label",
    ]
).copy()

with analysis_col2:
    value_scatter_figure = px.scatter(
        value_scatter_df,
        x="total_transaction_count",
        y="average_transaction_value",
        size="registered_user_count",
        color="state_name",
        hover_name="district_state_label",
        size_max=38,
        labels={
            "total_transaction_count":
                "Transaction count",
            "average_transaction_value":
                "Average transaction value",
            "state_name":
                "State / UT",
        },
        title=(
            "Transaction volume versus average value"
        ),
    )

    value_scatter_figure.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Transactions: %{x:,.0f}<br>"
            "Average value: ₹%{y:,.2f}"
            "<extra></extra>"
        )
    )

    apply_chart_layout(
        value_scatter_figure,
        height=500,
        show_legend=False,
    )

    st.plotly_chart(
        value_scatter_figure,
        use_container_width=True,
    )


# ============================================================
# DISTRICT TREND
# ============================================================

if selected_district_label != "All Districts":
    st.markdown(
        f"### Historical trajectory · "
        f"{selected_district_label}"
    )

    selected_district_history = (
        district_df[
            district_df["district_state_label"]
            == selected_district_label
        ]
        .sort_values("period_start_date")
        .copy()
    )

    trend_col1, trend_col2 = st.columns(2)

    with trend_col1:
        transaction_trend_figure = go.Figure()

        transaction_trend_figure.add_trace(
            go.Scatter(
                x=selected_district_history[
                    "period_start_date"
                ],
                y=selected_district_history[
                    "total_transaction_count"
                ],
                mode="lines+markers",
                name="Transactions",
                line=dict(
                    color=PHONEPE_LIGHT_PURPLE,
                    width=3,
                ),
                marker=dict(size=7),
                fill="tozeroy",
                fillcolor=(
                    "rgba(168,85,247,0.12)"
                ),
                customdata=selected_district_history[
                    ["period"]
                ],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Transactions: %{y:,.0f}"
                    "<extra></extra>"
                ),
            )
        )

        transaction_trend_figure.update_layout(
            title="Quarterly transaction trajectory",
            xaxis_title="Quarter",
            yaxis_title="Transaction count",
        )

        apply_chart_layout(
            transaction_trend_figure,
            height=430,
        )

        st.plotly_chart(
            transaction_trend_figure,
            use_container_width=True,
        )

    with trend_col2:
        rank_trend_figure = go.Figure()

        rank_trend_figure.add_trace(
            go.Scatter(
                x=selected_district_history[
                    "period_start_date"
                ],
                y=selected_district_history[
                    "national_transaction_count_rank"
                ],
                mode="lines+markers",
                name="National rank",
                line=dict(
                    color=PHONEPE_GREEN,
                    width=3,
                ),
                marker=dict(size=7),
                customdata=selected_district_history[
                    ["period"]
                ],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "National rank: %{y:,.0f}"
                    "<extra></extra>"
                ),
            )
        )

        rank_trend_figure.update_layout(
            title="National transaction ranking",
            xaxis_title="Quarter",
            yaxis_title=(
                "Rank — lower is better"
            ),
        )

        rank_trend_figure.update_yaxes(
            autorange="reversed"
        )

        apply_chart_layout(
            rank_trend_figure,
            height=430,
        )

        st.plotly_chart(
            rank_trend_figure,
            use_container_width=True,
        )


# ============================================================
# DISTRIBUTION ANALYSIS
# ============================================================

st.markdown("### District performance distribution")

distribution_col1, distribution_col2 = st.columns(2)

with distribution_col1:
    distribution_figure = px.histogram(
        selected_period_df.dropna(
            subset=["transactions_per_user"]
        ),
        x="transactions_per_user",
        nbins=30,
        color_discrete_sequence=[
            PHONEPE_LIGHT_PURPLE
        ],
        labels={
            "transactions_per_user":
                "Transactions per registered user"
        },
        title=(
            "Digital engagement distribution"
        ),
    )

    distribution_figure.update_traces(
        hovertemplate=(
            "Transactions per user: %{x:.2f}<br>"
            "Districts: %{y:,}"
            "<extra></extra>"
        )
    )

    apply_chart_layout(
        distribution_figure,
        height=420,
        show_legend=False,
    )

    st.plotly_chart(
        distribution_figure,
        use_container_width=True,
    )

with distribution_col2:
    average_value_figure = px.box(
        selected_period_df.dropna(
            subset=["average_transaction_value"]
        ),
        y="average_transaction_value",
        points="outliers",
        color_discrete_sequence=[
            PHONEPE_PINK
        ],
        labels={
            "average_transaction_value":
                "Average transaction value"
        },
        title=(
            "Average transaction value distribution"
        ),
    )

    average_value_figure.update_traces(
        hovertemplate=(
            "Average value: ₹%{y:,.2f}"
            "<extra></extra>"
        )
    )

    apply_chart_layout(
        average_value_figure,
        height=420,
        show_legend=False,
    )

    st.plotly_chart(
        average_value_figure,
        use_container_width=True,
    )


# ============================================================
# DYNAMIC INSIGHTS
# ============================================================

st.markdown("### Intelligence summary")

valid_transaction_rows = (
    selected_period_df.dropna(
        subset=["total_transaction_count"]
    )
)

valid_value_rows = (
    selected_period_df.dropna(
        subset=["total_transaction_amount"]
    )
)

valid_engagement_rows = (
    selected_period_df.dropna(
        subset=["transactions_per_user"]
    )
)

top_transaction_row = (
    valid_transaction_rows.nlargest(
        1,
        "total_transaction_count",
    ).iloc[0]
    if not valid_transaction_rows.empty
    else None
)

top_value_row = (
    valid_value_rows.nlargest(
        1,
        "total_transaction_amount",
    ).iloc[0]
    if not valid_value_rows.empty
    else None
)

top_engagement_row = (
    valid_engagement_rows.nlargest(
        1,
        "transactions_per_user",
    ).iloc[0]
    if not valid_engagement_rows.empty
    else None
)

insight_col1, insight_col2, insight_col3 = (
    st.columns(3)
)

with insight_col1:
    if top_transaction_row is not None:
        render_insight_card(
            title="Volume leader",
            body=(
                f"{top_transaction_row['district_state_label']} "
                f"recorded "
                f"{format_compact_number(top_transaction_row['total_transaction_count'])} "
                "transactions."
            ),
            accent_color=PHONEPE_PURPLE,
        )

with insight_col2:
    if top_value_row is not None:
        render_insight_card(
            title="Value leader",
            body=(
                f"{top_value_row['district_state_label']} "
                f"processed "
                f"{format_currency_compact(top_value_row['total_transaction_amount'])} "
                "in transaction value."
            ),
            accent_color=PHONEPE_PINK,
        )

with insight_col3:
    if top_engagement_row is not None:
        render_insight_card(
            title="Highest engagement",
            body=(
                f"{top_engagement_row['district_state_label']} "
                f"recorded "
                f"{top_engagement_row['transactions_per_user']:.2f} "
                "transactions per registered user."
            ),
            accent_color=PHONEPE_GREEN,
        )


# ============================================================
# DISTRICT LEADERBOARD
# ============================================================

st.markdown("### District leaderboard")

leaderboard_df = (
    selected_period_df[
        [
            "district_display_name",
            "state_name",
            "total_transaction_count",
            "total_transaction_amount",
            "average_transaction_value",
            "registered_user_count",
            "registered_merchant_count",
            "transactions_per_user",
            "national_transaction_count_rank",
            "state_transaction_count_rank",
        ]
    ]
    .sort_values(
        [
            "total_transaction_count",
            "total_transaction_amount",
        ],
        ascending=False,
    )
    .copy()
)

leaderboard_df = leaderboard_df.rename(
    columns={
        "district_display_name": "District",
        "state_name": "State / UT",
        "total_transaction_count":
            "Transactions",
        "total_transaction_amount":
            "Transaction value",
        "average_transaction_value":
            "Average value",
        "registered_user_count":
            "Registered users",
        "registered_merchant_count":
            "Registered merchants",
        "transactions_per_user":
            "Transactions per user",
        "national_transaction_count_rank":
            "National rank",
        "state_transaction_count_rank":
            "State rank",
    }
)

st.dataframe(
    leaderboard_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Transactions": st.column_config.NumberColumn(
            format="localized"
        ),
        "Transaction value":
            st.column_config.NumberColumn(
                format="₹ %.0f"
            ),
        "Average value":
            st.column_config.NumberColumn(
                format="₹ %.2f"
            ),
        "Registered users":
            st.column_config.NumberColumn(
                format="localized"
            ),
        "Registered merchants":
            st.column_config.NumberColumn(
                format="localized"
            ),
        "Transactions per user":
            st.column_config.NumberColumn(
                format="%.2f"
            ),
        "National rank":
            st.column_config.NumberColumn(
                format="%d"
            ),
        "State rank":
            st.column_config.NumberColumn(
                format="%d"
            ),
    },
    height=520,
)