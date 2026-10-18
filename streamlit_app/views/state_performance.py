import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.formatters import (
    format_compact_number,
    format_state_name,
)
from components.layout import (
    render_insight_card,
    render_kpi_card,
)
from services.data_loader import (
    load_state_quarterly_performance,
)
from services.databricks_client import clear_query_cache


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_number(value, default=0.0) -> float:
    if value is None or pd.isna(value):
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_growth(value) -> str:
    if value is None or pd.isna(value):
        return "—"

    return f"{float(value):.2f}%"


def classify_performance_segment(row) -> str:
    """
    Classify every state relative to the quarterly median
    transaction volume and growth.
    """

    transaction_count = row[
        "total_transaction_count"
    ]

    transaction_growth = row[
        "transaction_yoy_growth_pct"
    ]

    median_count = row[
        "period_median_transaction_count"
    ]

    median_growth = row[
        "period_median_growth"
    ]

    if pd.isna(transaction_growth):
        return "Insufficient growth history"

    high_volume = transaction_count >= median_count
    high_growth = transaction_growth >= median_growth

    if high_volume and high_growth:
        return "High-volume high-growth"

    if high_volume and not high_growth:
        return "High-volume mature"

    if not high_volume and high_growth:
        return "Emerging high-growth"

    return "Lower-volume lower-growth"


# ============================================================
# PAGE HEADER
# ============================================================

st.markdown(
    '<div class="page-kicker">State Performance</div>',
    unsafe_allow_html=True,
)

st.title("State-Level Digital Payment Intelligence")

st.markdown(
    """
    <div class="page-description">
        Compare transaction scale, registered-user adoption,
        merchant penetration, growth momentum and performance
        rankings across India's states and union territories.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATA
# ============================================================

try:
    with st.spinner(
        "Loading state performance data..."
    ):
        state_df = (
            load_state_quarterly_performance()
        )

except Exception as error:
    st.error(
        "State performance data could not be loaded "
        "from Databricks."
    )

    with st.expander("Technical details"):
        st.code(str(error))

    st.stop()


if state_df.empty:
    st.warning(
        "No state performance records are available."
    )
    st.stop()


# ============================================================
# PREPARE DATA
# ============================================================

state_df["period_start_date"] = pd.to_datetime(
    state_df["period_start_date"]
)


numeric_columns = [
    "year",
    "quarter",
    "total_transaction_count",
    "registered_user_count",
    "registered_merchant_count",
    "transaction_yoy_growth_pct",
    "transactions_per_registered_user",
    "transaction_rank",
    "registered_user_rank",
]

for column in numeric_columns:
    state_df[column] = pd.to_numeric(
        state_df[column],
        errors="coerce",
    )


state_df["state_name"] = (
    state_df["state_slug"]
    .apply(format_state_name)
)


# Calculate quarterly median benchmarks.

state_df["period_median_transaction_count"] = (
    state_df
    .groupby("period")[
        "total_transaction_count"
    ]
    .transform("median")
)

state_df["period_median_growth"] = (
    state_df
    .groupby("period")[
        "transaction_yoy_growth_pct"
    ]
    .transform("median")
)


# Create dynamic performance segments.

state_df["performance_segment"] = (
    state_df.apply(
        classify_performance_segment,
        axis=1,
    )
)


state_df = (
    state_df
    .sort_values(
        [
            "period_start_date",
            "transaction_rank",
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# FILTER OPTIONS
# ============================================================

period_options_df = (
    state_df[
        [
            "period",
            "period_start_date",
        ]
    ]
    .drop_duplicates()
    .sort_values("period_start_date")
)

available_periods = (
    period_options_df["period"].tolist()
)


state_options_df = (
    state_df[
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
        state_options_df["state_name"],
        state_options_df["state_slug"],
    )
)

state_names = list(
    state_name_to_slug.keys()
)

default_state_name = (
    "Maharashtra"
    if "Maharashtra" in state_names
    else state_names[0]
)


# ============================================================
# FILTERS
# ============================================================

filter_column_1, filter_column_2, filter_column_3 = (
    st.columns([1.1, 1.3, 1])
)


with filter_column_1:
    selected_period = st.selectbox(
        "Reporting period",
        options=available_periods,
        index=len(available_periods) - 1,
        key="state_reporting_period",
    )


with filter_column_2:
    selected_state_name = st.selectbox(
        "Focus state or UT",
        options=state_names,
        index=state_names.index(
            default_state_name
        ),
        key="state_focus_state",
    )


with filter_column_3:
    st.write("")

    if st.button(
        "Refresh warehouse data",
        use_container_width=True,
        key="state_refresh",
    ):
        clear_query_cache()
        st.rerun()


selected_state_slug = state_name_to_slug[
    selected_state_name
]


period_df = state_df[
    state_df["period"] == selected_period
].copy()


state_history_df = state_df[
    state_df["state_slug"]
    == selected_state_slug
].copy()


selected_state_df = period_df[
    period_df["state_slug"]
    == selected_state_slug
]


if selected_state_df.empty:
    st.warning(
        "No state record exists for the selected period."
    )
    st.stop()


selected_state_row = selected_state_df.iloc[0]


# ============================================================
# KPI CALCULATIONS
# ============================================================

transaction_count = safe_number(
    selected_state_row[
        "total_transaction_count"
    ]
)

registered_users = safe_number(
    selected_state_row[
        "registered_user_count"
    ]
)

registered_merchants = safe_number(
    selected_state_row[
        "registered_merchant_count"
    ]
)

transaction_yoy_raw = selected_state_row[
    "transaction_yoy_growth_pct"
]

transaction_yoy = (
    None
    if pd.isna(transaction_yoy_raw)
    else float(transaction_yoy_raw)
)

transactions_per_user = safe_number(
    selected_state_row[
        "transactions_per_registered_user"
    ]
)

transaction_rank = int(
    safe_number(
        selected_state_row["transaction_rank"],
        default=0,
    )
)

registered_user_rank = int(
    safe_number(
        selected_state_row[
            "registered_user_rank"
        ],
        default=0,
    )
)

performance_segment = str(
    selected_state_row["performance_segment"]
)


national_state_transaction_total = safe_number(
    period_df["total_transaction_count"].sum()
)

if national_state_transaction_total > 0:
    transaction_share = (
        transaction_count
        / national_state_transaction_total
        * 100
    )
else:
    transaction_share = 0.0


period_median_growth = (
    period_df[
        "transaction_yoy_growth_pct"
    ].median()
)


if (
    transaction_yoy is not None
    and not pd.isna(period_median_growth)
):
    growth_difference = (
        transaction_yoy
        - float(period_median_growth)
    )
else:
    growth_difference = None


# ============================================================
# KPI CARDS
# ============================================================

st.markdown(
    f"### {selected_state_name} · {selected_period}"
)


kpi_row_1 = st.columns(3)

with kpi_row_1[0]:
    render_kpi_card(
        label="Transaction volume",
        value=format_compact_number(
            transaction_count
        ),
        delta=(
            f"{transaction_share:.2f}% of "
            f"state-level national volume"
        ),
        positive=True,
    )

with kpi_row_1[1]:
    render_kpi_card(
        label="Registered users",
        value=format_compact_number(
            registered_users
        ),
        delta=(
            f"National user rank "
            f"#{registered_user_rank}"
        ),
        positive=True,
    )

with kpi_row_1[2]:
    render_kpi_card(
        label="Registered merchants",
        value=format_compact_number(
            registered_merchants
        ),
        delta="Merchant acceptance network",
        positive=True,
    )


st.write("")


kpi_row_2 = st.columns(3)

with kpi_row_2[0]:
    if growth_difference is None:
        growth_delta = (
            "Insufficient prior-year history"
        )
        growth_positive = True
    else:
        growth_delta = (
            f"{abs(growth_difference):.2f} percentage "
            f"points "
            f"{'above' if growth_difference >= 0 else 'below'} "
            f"the period median"
        )
        growth_positive = (
            growth_difference >= 0
        )

    render_kpi_card(
        label="Transaction YoY growth",
        value=format_growth(
            transaction_yoy
        ),
        delta=growth_delta,
        positive=growth_positive,
    )

with kpi_row_2[1]:
    render_kpi_card(
        label="Transactions per registered user",
        value=f"{transactions_per_user:,.2f}",
        delta="Quarterly transaction intensity",
        positive=True,
    )

with kpi_row_2[2]:
    render_kpi_card(
        label="Transaction rank",
        value=(
            f"#{transaction_rank}"
            if transaction_rank > 0
            else "—"
        ),
        delta=performance_segment,
        positive=(
            transaction_rank > 0
            and transaction_rank <= 10
        ),
    )


# ============================================================
# STATE HISTORY
# ============================================================

st.markdown("### Historical state trajectory")

trend_column, rank_column = st.columns(
    [1.55, 1]
)


state_trend_figure = go.Figure()

state_trend_figure.add_trace(
    go.Scatter(
        x=state_history_df[
            "period_start_date"
        ],
        y=(
            state_history_df[
                "total_transaction_count"
            ]
            / 1_000_000_000
        ),
        customdata=state_history_df[
            ["period"]
        ],
        mode="lines+markers",
        line={
            "color": "#6C2EB9",
            "width": 3,
        },
        marker={
            "size": 6,
            "color": "#6C2EB9",
        },
        fill="tozeroy",
        fillcolor="rgba(108, 46, 185, 0.10)",
        hovertemplate=(
            "%{customdata[0]}<br>"
            "%{y:,.2f} billion transactions"
            "<extra></extra>"
        ),
    )
)

state_trend_figure.update_layout(
    title=(
        f"{selected_state_name} "
        f"transaction trajectory"
    ),
    height=400,
    margin={
        "l": 25,
        "r": 20,
        "t": 60,
        "b": 25,
    },
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font={"color": "#4B4252"},
    xaxis={
        "title": "",
        "showgrid": False,
    },
    yaxis={
        "title": "Transactions (billions)",
        "gridcolor": "#EEE8F3",
    },
    showlegend=False,
)


with trend_column:
    st.plotly_chart(
        state_trend_figure,
        use_container_width=True,
        config={"displayModeBar": False},
    )


rank_figure = go.Figure()

rank_figure.add_trace(
    go.Scatter(
        x=state_history_df[
            "period_start_date"
        ],
        y=state_history_df[
            "transaction_rank"
        ],
        customdata=state_history_df[
            ["period"]
        ],
        mode="lines+markers",
        line={
            "color": "#D946EF",
            "width": 3,
        },
        marker={
            "size": 7,
            "color": "#D946EF",
        },
        hovertemplate=(
            "%{customdata[0]}<br>"
            "Rank #%{y:.0f}"
            "<extra></extra>"
        ),
    )
)

rank_figure.update_layout(
    title="National transaction rank",
    height=400,
    margin={
        "l": 25,
        "r": 20,
        "t": 60,
        "b": 25,
    },
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font={"color": "#4B4252"},
    xaxis={
        "title": "",
        "showgrid": False,
    },
    yaxis={
        "title": "Rank",
        "autorange": "reversed",
        "dtick": 5,
        "gridcolor": "#EEE8F3",
    },
    showlegend=False,
)


with rank_column:
    st.plotly_chart(
        rank_figure,
        use_container_width=True,
        config={"displayModeBar": False},
    )


# ============================================================
# CROSS-STATE COMPARISON
# ============================================================

st.markdown(
    f"### Cross-state comparison · {selected_period}"
)


period_df["transaction_count_billions"] = (
    period_df["total_transaction_count"]
    / 1_000_000_000
)

period_df["registered_users_millions"] = (
    period_df["registered_user_count"]
    / 1_000_000
)

period_df["registered_merchants_millions"] = (
    period_df["registered_merchant_count"]
    .fillna(0)
    / 1_000_000
)

period_df["bubble_size"] = (
    period_df[
        "registered_merchants_millions"
    ]
    .fillna(0)
    .clip(lower=0.01)
)

period_df["growth_for_chart"] = (
    period_df[
        "transaction_yoy_growth_pct"
    ]
    .fillna(0)
)


comparison_figure = px.scatter(
    period_df,
    x="registered_users_millions",
    y="transaction_count_billions",
    size="bubble_size",
    color="growth_for_chart",
    hover_name="state_name",
    hover_data={
        "registered_users_millions": ":.2f",
        "transaction_count_billions": ":.2f",
        "registered_merchants_millions": ":.2f",
        "growth_for_chart": ":.2f",
        "bubble_size": False,
    },
    color_continuous_scale=[
        "#F1E5FF",
        "#9A5ED1",
        "#4C197F",
    ],
    size_max=48,
    labels={
        "registered_users_millions": (
            "Registered users (millions)"
        ),
        "transaction_count_billions": (
            "Transactions (billions)"
        ),
        "registered_merchants_millions": (
            "Registered merchants (millions)"
        ),
        "growth_for_chart": "YoY growth (%)",
    },
)

comparison_figure.update_layout(
    title=(
        "Transaction scale vs registered-user base"
    ),
    height=510,
    margin={
        "l": 30,
        "r": 20,
        "t": 65,
        "b": 35,
    },
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font={"color": "#4B4252"},
    xaxis={"gridcolor": "#EEE8F3"},
    yaxis={"gridcolor": "#EEE8F3"},
)


comparison_figure.add_annotation(
    x=registered_users / 1_000_000,
    y=transaction_count / 1_000_000_000,
    text=selected_state_name,
    showarrow=True,
    arrowcolor="#6C2EB9",
    bgcolor="#FFFFFF",
    bordercolor="#6C2EB9",
    font={
        "color": "#6C2EB9",
        "size": 12,
    },
)


st.plotly_chart(
    comparison_figure,
    use_container_width=True,
    config={"displayModeBar": False},
)


# ============================================================
# GROWTH-VOLUME QUADRANT
# ============================================================

median_transaction_volume = safe_number(
    period_df[
        "transaction_count_billions"
    ].median()
)

median_growth_for_chart = safe_number(
    period_df["growth_for_chart"].median()
)


quadrant_figure = px.scatter(
    period_df,
    x="growth_for_chart",
    y="transaction_count_billions",
    size="registered_users_millions",
    color="performance_segment",
    hover_name="state_name",
    hover_data={
        "growth_for_chart": ":.2f",
        "transaction_count_billions": ":.2f",
        "registered_users_millions": ":.2f",
    },
    size_max=45,
    color_discrete_sequence=[
        "#6C2EB9",
        "#D946EF",
        "#19A974",
        "#F59E0B",
        "#64748B",
    ],
    labels={
        "growth_for_chart": (
            "Transaction YoY growth (%)"
        ),
        "transaction_count_billions": (
            "Transactions (billions)"
        ),
        "registered_users_millions": (
            "Registered users (millions)"
        ),
        "performance_segment": (
            "Performance segment"
        ),
    },
)

quadrant_figure.add_vline(
    x=median_growth_for_chart,
    line_dash="dash",
    line_color="#A69DAE",
)

quadrant_figure.add_hline(
    y=median_transaction_volume,
    line_dash="dash",
    line_color="#A69DAE",
)

quadrant_figure.update_layout(
    title="Growth-volume performance quadrant",
    height=530,
    margin={
        "l": 30,
        "r": 20,
        "t": 70,
        "b": 35,
    },
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font={"color": "#4B4252"},
    xaxis={"gridcolor": "#EEE8F3"},
    yaxis={"gridcolor": "#EEE8F3"},
    legend={
        "orientation": "h",
        "y": 1.13,
        "x": 0,
    },
)

st.plotly_chart(
    quadrant_figure,
    use_container_width=True,
    config={"displayModeBar": False},
)


# ============================================================
# DYNAMIC INSIGHTS
# ============================================================

top_volume_row = period_df.nlargest(
    1,
    "total_transaction_count",
).iloc[0]


valid_growth_df = period_df.dropna(
    subset=["transaction_yoy_growth_pct"]
)

if valid_growth_df.empty:
    fastest_growth_row = top_volume_row
else:
    fastest_growth_row = (
        valid_growth_df.nlargest(
            1,
            "transaction_yoy_growth_pct",
        ).iloc[0]
    )


valid_intensity_df = period_df.dropna(
    subset=[
        "transactions_per_registered_user"
    ]
)

if valid_intensity_df.empty:
    highest_intensity_row = top_volume_row
else:
    highest_intensity_row = (
        valid_intensity_df.nlargest(
            1,
            "transactions_per_registered_user",
        ).iloc[0]
    )


st.markdown("### State intelligence summary")

insight_columns = st.columns(3)


with insight_columns[0]:
    render_insight_card(
        title="Market leader",
        message=(
            f"{top_volume_row['state_name']} led India "
            f"with "
            f"{format_compact_number(top_volume_row['total_transaction_count'])} "
            f"transactions in {selected_period}."
        ),
        accent_colour="#6C2EB9",
    )


with insight_columns[1]:
    render_insight_card(
        title="Growth leader",
        message=(
            f"{fastest_growth_row['state_name']} "
            f"recorded the highest YoY growth at "
            f"{safe_number(fastest_growth_row['transaction_yoy_growth_pct']):.2f}%."
        ),
        accent_colour="#19A974",
    )


with insight_columns[2]:
    render_insight_card(
        title="Usage-intensity leader",
        message=(
            f"{highest_intensity_row['state_name']} "
            f"generated "
            f"{safe_number(highest_intensity_row['transactions_per_registered_user']):.2f} "
            f"quarterly transactions per "
            f"registered user."
        ),
        accent_colour="#D946EF",
    )


# ============================================================
# STATE LEADERBOARD
# ============================================================

st.markdown("### State performance leaderboard")


leaderboard_df = (
    period_df[
        [
            "transaction_rank",
            "state_name",
            "total_transaction_count",
            "transaction_yoy_growth_pct",
            "registered_user_count",
            "registered_merchant_count",
            "transactions_per_registered_user",
            "performance_segment",
        ]
    ]
    .sort_values("transaction_rank")
    .rename(
        columns={
            "transaction_rank": "Rank",
            "state_name": "State / UT",
            "total_transaction_count": (
                "Transaction count"
            ),
            "transaction_yoy_growth_pct": (
                "YoY growth (%)"
            ),
            "registered_user_count": (
                "Registered users"
            ),
            "registered_merchant_count": (
                "Registered merchants"
            ),
            "transactions_per_registered_user": (
                "Transactions per user"
            ),
            "performance_segment": (
                "Performance segment"
            ),
        }
    )
)


st.dataframe(
    leaderboard_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn(
            format="%d"
        ),
        "Transaction count": (
            st.column_config.NumberColumn(
                format="%,d"
            )
        ),
        "YoY growth (%)": (
            st.column_config.NumberColumn(
                format="%.2f"
            )
        ),
        "Registered users": (
            st.column_config.NumberColumn(
                format="%,d"
            )
        ),
        "Registered merchants": (
            st.column_config.NumberColumn(
                format="%,d"
            )
        ),
        "Transactions per user": (
            st.column_config.NumberColumn(
                format="%.2f"
            )
        ),
    },
)