import pandas as pd
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
    load_india_kpis,
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


def growth_delta_text(value: float) -> str:
    if pd.isna(value):
        return "No prior-year comparison"

    symbol = "▲" if value >= 0 else "▼"

    return f"{symbol} {abs(value):.2f}% YoY"


# ============================================================
# PAGE HEADER
# ============================================================

st.markdown(
    '<div class="page-kicker">Executive Overview</div>',
    unsafe_allow_html=True,
)

st.title("India's Digital Payments Pulse")

st.markdown(
    """
    <div class="page-description">
        Track quarterly transaction volume, registered-user
        adoption, merchant expansion and geographic performance
        using the production Databricks Gold layer.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATABRICKS DATA
# ============================================================

try:
    with st.spinner("Loading Databricks Gold metrics..."):
        india_df = load_india_kpis()
        state_df = load_state_quarterly_performance()

except Exception as error:
    st.error(
        "The Executive Overview could not load data from "
        "Databricks."
    )

    with st.expander("Technical details"):
        st.code(str(error))

    st.stop()


if india_df.empty:
    st.warning(
        "The national KPI Gold table contains no records."
    )
    st.stop()


# ============================================================
# PREPARE NATIONAL DATA
# ============================================================

india_df["period_start_date"] = pd.to_datetime(
    india_df["period_start_date"]
)

state_df["period_start_date"] = pd.to_datetime(
    state_df["period_start_date"]
)


national_numeric_columns = [
    "year",
    "quarter",
    "total_transaction_count",
    "registered_user_count",
    "registered_merchant_count",
]

for column in national_numeric_columns:
    india_df[column] = pd.to_numeric(
        india_df[column],
        errors="coerce",
    )


state_numeric_columns = [
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

for column in state_numeric_columns:
    state_df[column] = pd.to_numeric(
        state_df[column],
        errors="coerce",
    )


india_df = (
    india_df
    .sort_values("period_start_date")
    .reset_index(drop=True)
)


# Calculate dashboard metrics from the national time series.

india_df["transaction_yoy_growth"] = (
    india_df["total_transaction_count"]
    .pct_change(periods=4)
    .mul(100)
)

india_df["user_yoy_growth"] = (
    india_df["registered_user_count"]
    .pct_change(periods=4)
    .mul(100)
)

india_df["merchant_yoy_growth"] = (
    india_df["registered_merchant_count"]
    .pct_change(periods=4)
    .mul(100)
)

india_df["transactions_per_user"] = (
    india_df["total_transaction_count"]
    / india_df["registered_user_count"]
)


first_transaction_count = safe_number(
    india_df["total_transaction_count"].iloc[0],
    default=1.0,
)

first_user_count = safe_number(
    india_df["registered_user_count"].iloc[0],
    default=1.0,
)

first_merchant_count = safe_number(
    india_df["registered_merchant_count"].iloc[0],
    default=1.0,
)


india_df["transaction_index"] = (
    india_df["total_transaction_count"]
    / first_transaction_count
    * 100
)

india_df["user_index"] = (
    india_df["registered_user_count"]
    / first_user_count
    * 100
)

india_df["merchant_index"] = (
    india_df["registered_merchant_count"]
    / first_merchant_count
    * 100
)


state_df["state_name"] = (
    state_df["state_slug"]
    .apply(format_state_name)
)


# ============================================================
# REPORTING FILTERS
# ============================================================

available_years = sorted(
    india_df["year"]
    .dropna()
    .astype(int)
    .unique()
)


filter_column_1, filter_column_2, filter_column_3 = (
    st.columns([1, 1, 1.2])
)


with filter_column_1:
    selected_year = st.selectbox(
        "Reporting year",
        options=available_years,
        index=len(available_years) - 1,
        key="executive_year",
    )


available_quarters = sorted(
    india_df.loc[
        india_df["year"].astype(int) == selected_year,
        "quarter",
    ]
    .dropna()
    .astype(int)
    .unique()
)


with filter_column_2:
    selected_quarter = st.selectbox(
        "Quarter",
        options=available_quarters,
        index=len(available_quarters) - 1,
        format_func=lambda quarter: f"Q{quarter}",
        key="executive_quarter",
    )


with filter_column_3:
    st.write("")

    if st.button(
        "Refresh warehouse data",
        use_container_width=True,
        key="executive_refresh",
    ):
        clear_query_cache()
        st.rerun()


selected_national_df = india_df[
    (india_df["year"].astype(int) == selected_year)
    & (
        india_df["quarter"].astype(int)
        == selected_quarter
    )
]


if selected_national_df.empty:
    st.warning(
        "No national record exists for the selected period."
    )
    st.stop()


selected_row = selected_national_df.iloc[-1]
selected_period = str(selected_row["period"])


# ============================================================
# KPI VALUES
# ============================================================

transaction_count = safe_number(
    selected_row["total_transaction_count"]
)

registered_users = safe_number(
    selected_row["registered_user_count"]
)

registered_merchants = safe_number(
    selected_row["registered_merchant_count"]
)

transaction_yoy = safe_number(
    selected_row["transaction_yoy_growth"]
)

user_yoy = safe_number(
    selected_row["user_yoy_growth"]
)

merchant_yoy = safe_number(
    selected_row["merchant_yoy_growth"]
)

transactions_per_user = safe_number(
    selected_row["transactions_per_user"]
)

transaction_index = safe_number(
    selected_row["transaction_index"]
)


# ============================================================
# KPI CARDS
# ============================================================

st.markdown(
    f"### National performance · {selected_period}"
)


kpi_row_1 = st.columns(3)

with kpi_row_1[0]:
    render_kpi_card(
        label="Quarterly transactions",
        value=format_compact_number(
            transaction_count
        ),
        delta=growth_delta_text(transaction_yoy),
        positive=transaction_yoy >= 0,
    )

with kpi_row_1[1]:
    render_kpi_card(
        label="Registered users",
        value=format_compact_number(
            registered_users
        ),
        delta=growth_delta_text(user_yoy),
        positive=user_yoy >= 0,
    )

with kpi_row_1[2]:
    render_kpi_card(
        label="Registered merchants",
        value=format_compact_number(
            registered_merchants
        ),
        delta=growth_delta_text(merchant_yoy),
        positive=merchant_yoy >= 0,
    )


st.write("")


kpi_row_2 = st.columns(3)

with kpi_row_2[0]:
    render_kpi_card(
        label="Transaction YoY growth",
        value=format_percentage(transaction_yoy),
        delta="Compared with the same quarter last year",
        positive=transaction_yoy >= 0,
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
        label="Transaction volume index",
        value=f"{transaction_index:,.1f}",
        delta="2018-Q1 baseline = 100",
        positive=True,
    )


st.caption(
    "Transaction metrics represent transaction count rather "
    "than monetary transaction value."
)


# ============================================================
# NATIONAL TRANSACTION TREND
# ============================================================

st.markdown("### National growth trajectory")

trend_column, index_column = st.columns([1.6, 1])


transaction_trend_figure = go.Figure()

transaction_trend_figure.add_trace(
    go.Scatter(
        x=india_df["period_start_date"],
        y=(
            india_df["total_transaction_count"]
            / 1_000_000_000
        ),
        customdata=india_df[["period"]],
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

transaction_trend_figure.update_layout(
    title="Quarterly transaction volume",
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
    hovermode="x unified",
    showlegend=False,
)


with trend_column:
    st.plotly_chart(
        transaction_trend_figure,
        use_container_width=True,
        config={"displayModeBar": False},
    )


# ============================================================
# GROWTH INDEX COMPARISON
# ============================================================

index_figure = go.Figure()

index_figure.add_trace(
    go.Scatter(
        x=india_df["period_start_date"],
        y=india_df["transaction_index"],
        mode="lines",
        name="Transactions",
        line={
            "color": "#6C2EB9",
            "width": 3,
        },
    )
)

index_figure.add_trace(
    go.Scatter(
        x=india_df["period_start_date"],
        y=india_df["user_index"],
        mode="lines",
        name="Users",
        line={
            "color": "#D946EF",
            "width": 2.5,
        },
    )
)

index_figure.add_trace(
    go.Scatter(
        x=india_df["period_start_date"],
        y=india_df["merchant_index"],
        mode="lines",
        name="Merchants",
        line={
            "color": "#19A974",
            "width": 2.5,
        },
    )
)

index_figure.update_layout(
    title="Growth index comparison",
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
    legend={
        "orientation": "h",
        "y": 1.13,
        "x": 0,
    },
    xaxis={
        "title": "",
        "showgrid": False,
    },
    yaxis={
        "title": "Index (2018-Q1 = 100)",
        "gridcolor": "#EEE8F3",
    },
    hovermode="x unified",
)


with index_column:
    st.plotly_chart(
        index_figure,
        use_container_width=True,
        config={"displayModeBar": False},
    )


# ============================================================
# STATE LEADERSHIP
# ============================================================

selected_state_df = state_df[
    state_df["period"] == selected_period
].copy()


if not selected_state_df.empty:
    st.markdown(
        f"### State leadership · {selected_period}"
    )

    top_states = (
        selected_state_df
        .nlargest(
            10,
            "total_transaction_count",
        )
        .sort_values(
            "total_transaction_count"
        )
    )


    state_ranking_figure = go.Figure()

    state_ranking_figure.add_trace(
        go.Bar(
            x=(
                top_states[
                    "total_transaction_count"
                ]
                / 1_000_000_000
            ),
            y=top_states["state_name"],
            orientation="h",
            marker={
                "color": top_states[
                    "total_transaction_count"
                ],
                "colorscale": [
                    [0, "#DCC5F5"],
                    [1, "#6C2EB9"],
                ],
            },
            customdata=top_states[
                [
                    "transaction_yoy_growth_pct",
                    "transaction_rank",
                ]
            ],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "%{x:,.2f} billion transactions<br>"
                "YoY growth: %{customdata[0]:.2f}%<br>"
                "Rank: #%{customdata[1]:.0f}"
                "<extra></extra>"
            ),
        )
    )

    state_ranking_figure.update_layout(
        title="Top 10 states by transaction volume",
        height=470,
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 30,
        },
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"color": "#4B4252"},
        xaxis={
            "title": "Transactions (billions)",
            "gridcolor": "#EEE8F3",
        },
        yaxis={"title": ""},
        showlegend=False,
    )

    st.plotly_chart(
        state_ranking_figure,
        use_container_width=True,
        config={"displayModeBar": False},
    )


# ============================================================
# DYNAMIC BUSINESS INSIGHTS
# ============================================================

if not selected_state_df.empty:
    valid_growth_df = selected_state_df.dropna(
        subset=["transaction_yoy_growth_pct"]
    )

    valid_intensity_df = selected_state_df.dropna(
        subset=[
            "transactions_per_registered_user"
        ]
    )

    top_volume_row = selected_state_df.nlargest(
        1,
        "total_transaction_count",
    ).iloc[0]


    if valid_growth_df.empty:
        fastest_growth_row = top_volume_row
    else:
        fastest_growth_row = valid_growth_df.nlargest(
            1,
            "transaction_yoy_growth_pct",
        ).iloc[0]


    if valid_intensity_df.empty:
        highest_intensity_row = top_volume_row
    else:
        highest_intensity_row = (
            valid_intensity_df.nlargest(
                1,
                "transactions_per_registered_user",
            ).iloc[0]
        )


    st.markdown("### Executive intelligence")

    insight_columns = st.columns(3)


    with insight_columns[0]:
        render_insight_card(
            title="Transaction leader",
            message=(
                f"{top_volume_row['state_name']} ranked first "
                f"with "
                f"{format_compact_number(top_volume_row['total_transaction_count'])} "
                f"transactions during {selected_period}."
            ),
            accent_colour="#6C2EB9",
        )


    with insight_columns[1]:
        render_insight_card(
            title="Growth leader",
            message=(
                f"{fastest_growth_row['state_name']} recorded "
                f"the strongest year-on-year growth at "
                f"{safe_number(fastest_growth_row['transaction_yoy_growth_pct']):.2f}%."
            ),
            accent_colour="#19A974",
        )


    with insight_columns[2]:
        render_insight_card(
            title="Usage-intensity leader",
            message=(
                f"{highest_intensity_row['state_name']} generated "
                f"{safe_number(highest_intensity_row['transactions_per_registered_user']):.2f} "
                f"quarterly transactions per registered user."
            ),
            accent_colour="#D946EF",
        )