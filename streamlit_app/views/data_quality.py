"""
Data Quality and Platform Monitoring page.

Monitors Gold marts, ML forecast coverage, data freshness,
record counts and production readiness.
"""

import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.formatters import (
    format_compact_number,
)
from components.layout import (
    render_insight_card,
    render_kpi_card,
)
from services.data_loader import (
    clear_dashboard_data_cache,
    load_dashboard_data_quality,
    load_state_transaction_forecasts,
)


# ============================================================
# PAGE CONSTANTS
# ============================================================

PHONEPE_PURPLE = "#5F259F"
PHONEPE_LIGHT_PURPLE = "#A855F7"
PHONEPE_GREEN = "#10B981"
PHONEPE_ORANGE = "#F59E0B"
PHONEPE_RED = "#EF4444"
PHONEPE_BLUE = "#3B82F6"
PHONEPE_GREY = "#64748B"

TRANSPARENT = "rgba(0,0,0,0)"
GRID_COLOUR = "rgba(95,37,159,0.11)"

MODEL_TEST_WMAPE = 2.82
NAIVE_TEST_WMAPE = 5.30
MODEL_IMPROVEMENT = 46.86

EXPECTED_FORECAST_STATES = 36


# ============================================================
# PAGE HEADER
# ============================================================

st.title("Data Quality & Platform Monitoring")

st.caption(
    "Monitor analytics-table coverage, data freshness, "
    "forecast quality and end-to-end platform readiness."
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def find_column(
    dataframe,
    candidates,
    required_terms=None,
):
    """
    Locate a column using exact candidates or partial terms.
    """

    column_lookup = {
        column.lower(): column
        for column in dataframe.columns
    }

    for candidate in candidates:
        if candidate.lower() in column_lookup:
            return column_lookup[
                candidate.lower()
            ]

    if required_terms:
        for column in dataframe.columns:
            normalized_column = column.lower()

            if all(
                term.lower()
                in normalized_column
                for term in required_terms
            ):
                return column

    return None


def quarter_to_start_date(period):
    """
    Convert values such as 2026-Q2 into timestamps.
    """

    if period is None or pd.isna(period):
        return pd.NaT

    period_match = re.fullmatch(
        r"(\d{4})-Q([1-4])",
        str(period).strip(),
    )

    if not period_match:
        return pd.NaT

    year = int(
        period_match.group(1)
    )

    quarter = int(
        period_match.group(2)
    )

    month = (
        (quarter - 1) * 3
    ) + 1

    return pd.Timestamp(
        year=year,
        month=month,
        day=1,
    )


def calculate_quarter_coverage(
    first_period,
    last_period,
):
    """
    Calculate the number of inclusive quarters between
    two period values.
    """

    first_date = quarter_to_start_date(
        first_period
    )

    last_date = quarter_to_start_date(
        last_period
    )

    if (
        pd.isna(first_date)
        or pd.isna(last_date)
    ):
        return np.nan

    return (
        (
            last_date.year
            - first_date.year
        )
        * 4
        + (
            (last_date.month - 1) // 3
            - (first_date.month - 1) // 3
        )
        + 1
    )


def apply_chart_layout(
    figure,
    height=430,
    show_legend=True,
):
    """
    Apply the dashboard Plotly theme.
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


# ============================================================
# REFRESH CONTROL
# ============================================================

refresh_col1, refresh_col2 = st.columns(
    [4, 1]
)

with refresh_col2:
    if st.button(
        "Refresh monitoring data",
        use_container_width=True,
    ):
        clear_dashboard_data_cache()
        st.rerun()


# ============================================================
# LOAD GOLD QUALITY SUMMARY
# ============================================================

try:
    with st.spinner(
        "Running Gold-layer monitoring checks..."
    ):
        quality_df = (
            load_dashboard_data_quality()
        )

except Exception as error:
    st.error(
        "The data-quality summary could not be loaded "
        "from Databricks."
    )

    st.exception(error)
    st.stop()


if quality_df.empty:
    st.warning(
        "The quality query returned no dataset records."
    )
    st.stop()


quality_df = quality_df.copy()

quality_df["row_count"] = pd.to_numeric(
    quality_df["row_count"],
    errors="coerce",
).fillna(0)

quality_df["first_period"] = (
    quality_df["first_period"]
    .astype(str)
)

quality_df["last_period"] = (
    quality_df["last_period"]
    .astype(str)
)

quality_df["quarter_coverage"] = (
    quality_df.apply(
        lambda row: calculate_quarter_coverage(
            row["first_period"],
            row["last_period"],
        ),
        axis=1,
    )
)


# ============================================================
# LOAD ML FORECAST QUALITY
# ============================================================

forecast_available = False
forecast_error_message = None
forecast_rows = 0
forecast_state_count = 0
missing_forecast_count = 0
negative_forecast_count = 0
forecast_period = "Not available"

try:
    raw_forecast_df = (
        load_state_transaction_forecasts()
    )

    if not raw_forecast_df.empty:
        forecast_available = True
        forecast_rows = len(raw_forecast_df)

        forecast_state_column = find_column(
            raw_forecast_df,
            candidates=[
                "state_slug",
                "state",
                "geography_slug",
            ],
            required_terms=[
                "state",
            ],
        )

        predicted_value_column = find_column(
            raw_forecast_df,
            candidates=[
                "predicted_transaction_count",
                "predicted_next_quarter_transaction_count",
                "forecast_transaction_count",
                "prediction",
                "predicted_value",
                "y_pred",
            ],
            required_terms=[
                "predict",
                "transaction",
            ],
        )

        forecast_period_column = find_column(
            raw_forecast_df,
            candidates=[
                "forecast_period",
                "target_period",
                "prediction_period",
                "predicted_period",
            ],
            required_terms=[
                "forecast",
                "period",
            ],
        )

        if forecast_state_column:
            forecast_state_count = (
                raw_forecast_df[
                    forecast_state_column
                ]
                .dropna()
                .nunique()
            )

        if predicted_value_column:
            forecast_values = pd.to_numeric(
                raw_forecast_df[
                    predicted_value_column
                ],
                errors="coerce",
            )

            missing_forecast_count = (
                forecast_values
                .isna()
                .sum()
            )

            negative_forecast_count = (
                forecast_values < 0
            ).sum()

        if forecast_period_column:
            available_forecast_periods = (
                raw_forecast_df[
                    forecast_period_column
                ]
                .dropna()
                .astype(str)
                .sort_values()
                .unique()
                .tolist()
            )

            if available_forecast_periods:
                forecast_period = (
                    available_forecast_periods[-1]
                )

except Exception as error:
    forecast_error_message = str(error)


# ============================================================
# PLATFORM-LEVEL CALCULATIONS
# ============================================================

dataset_count = (
    quality_df["dataset"]
    .nunique()
)

healthy_dataset_count = (
    quality_df.loc[
        quality_df["row_count"] > 0,
        "dataset",
    ]
    .nunique()
)

total_gold_rows = (
    quality_df["row_count"]
    .sum()
)

latest_data_period = (
    quality_df["last_period"]
    .replace(
        {
            "None": np.nan,
            "nan": np.nan,
        }
    )
    .dropna()
    .max()
)

earliest_data_period = (
    quality_df["first_period"]
    .replace(
        {
            "None": np.nan,
            "nan": np.nan,
        }
    )
    .dropna()
    .min()
)

aligned_latest_periods = (
    quality_df["last_period"]
    == latest_data_period
).sum()


# ============================================================
# QUALITY CHECKS
# ============================================================

quality_checks = []

for _, row in quality_df.iterrows():
    dataset_name = row["dataset"]
    row_count = row["row_count"]

    quality_checks.append(
        {
            "Check": (
                f"{dataset_name} contains records"
            ),
            "Layer": "Gold / Feature",
            "Result": (
                f"{row_count:,.0f} rows"
            ),
            "Status": (
                "PASS"
                if row_count > 0
                else "FAIL"
            ),
        }
    )

quality_checks.append(
    {
        "Check": (
            "Gold datasets aligned to latest period"
        ),
        "Layer": "Gold",
        "Result": (
            f"{aligned_latest_periods}/"
            f"{dataset_count} datasets at "
            f"{latest_data_period}"
        ),
        "Status": (
            "PASS"
            if aligned_latest_periods
            == dataset_count
            else "WARNING"
        ),
    }
)

quality_checks.append(
    {
        "Check": "Forecast output is available",
        "Layer": "ML",
        "Result": (
            f"{forecast_rows:,} forecast rows"
            if forecast_available
            else "Forecast table unavailable"
        ),
        "Status": (
            "PASS"
            if forecast_available
            else "FAIL"
        ),
    }
)

quality_checks.append(
    {
        "Check": "State forecast coverage",
        "Layer": "ML",
        "Result": (
            f"{forecast_state_count:,}/"
            f"{EXPECTED_FORECAST_STATES} "
            "states and UTs"
        ),
        "Status": (
            "PASS"
            if forecast_state_count
            == EXPECTED_FORECAST_STATES
            else "WARNING"
        ),
    }
)

quality_checks.append(
    {
        "Check": "Forecast values are populated",
        "Layer": "ML",
        "Result": (
            f"{missing_forecast_count:,} "
            "missing predictions"
        ),
        "Status": (
            "PASS"
            if missing_forecast_count == 0
            and forecast_available
            else "FAIL"
        ),
    }
)

quality_checks.append(
    {
        "Check": "Forecast values are non-negative",
        "Layer": "ML",
        "Result": (
            f"{negative_forecast_count:,} "
            "negative predictions"
        ),
        "Status": (
            "PASS"
            if negative_forecast_count == 0
            and forecast_available
            else "FAIL"
        ),
    }
)

quality_checks.append(
    {
        "Check": "Model beats naive baseline",
        "Layer": "ML validation",
        "Result": (
            f"{MODEL_TEST_WMAPE:.2f}% versus "
            f"{NAIVE_TEST_WMAPE:.2f}% WMAPE"
        ),
        "Status": (
            "PASS"
            if MODEL_TEST_WMAPE
            < NAIVE_TEST_WMAPE
            else "FAIL"
        ),
    }
)

checks_df = pd.DataFrame(
    quality_checks
)

pass_count = (
    checks_df["Status"]
    == "PASS"
).sum()

warning_count = (
    checks_df["Status"]
    == "WARNING"
).sum()

fail_count = (
    checks_df["Status"]
    == "FAIL"
).sum()

total_check_count = len(
    checks_df
)

quality_score = (
    (
        pass_count
        + warning_count * 0.5
    )
    / total_check_count
) * 100

overall_platform_status = (
    "Healthy"
    if fail_count == 0
    else "Attention required"
)


# ============================================================
# PLATFORM SUMMARY
# ============================================================

st.markdown("### Platform health summary")

kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

with kpi_col1:
    render_kpi_card(
        title="Platform status",
        value=overall_platform_status,
        subtitle=(
            f"{pass_count}/{total_check_count} "
            "checks passed"
        ),
        positive=fail_count == 0,
        icon="✓",
    )

with kpi_col2:
    render_kpi_card(
        title="Quality score",
        value=f"{quality_score:.1f}%",
        subtitle=(
            f"{warning_count} warnings · "
            f"{fail_count} failures"
        ),
        positive=quality_score >= 90,
        icon="◈",
    )

with kpi_col3:
    render_kpi_card(
        title="Analytics datasets",
        value=(
            f"{healthy_dataset_count}/"
            f"{dataset_count}"
        ),
        subtitle="Non-empty Gold and feature marts",
        positive=(
            healthy_dataset_count
            == dataset_count
        ),
        icon="▦",
    )

kpi_col4, kpi_col5, kpi_col6 = st.columns(3)

with kpi_col4:
    render_kpi_card(
        title="Total monitored rows",
        value=format_compact_number(
            total_gold_rows
        ),
        subtitle="Across monitored analytics tables",
        icon="▤",
    )

with kpi_col5:
    render_kpi_card(
        title="Historical coverage",
        value=(
            f"{earliest_data_period} → "
            f"{latest_data_period}"
        ),
        subtitle="Gold-layer reporting periods",
        icon="◷",
    )

with kpi_col6:
    render_kpi_card(
        title="Forecast coverage",
        value=(
            f"{forecast_state_count}/"
            f"{EXPECTED_FORECAST_STATES}"
        ),
        subtitle=(
            f"Latest forecast · "
            f"{forecast_period}"
        ),
        positive=(
            forecast_state_count
            == EXPECTED_FORECAST_STATES
        ),
        icon="⚙",
    )


# ============================================================
# QUALITY SCORE PROGRESS
# ============================================================

st.markdown("### Overall production-readiness score")

st.progress(
    min(
        max(
            quality_score / 100,
            0.0,
        ),
        1.0,
    ),
    text=(
        f"{quality_score:.1f}% production readiness"
    ),
)


# ============================================================
# TABLE ROW COUNTS
# ============================================================

st.markdown("### Analytics-table monitoring")

chart_col1, chart_col2 = st.columns([1.25, 1])

row_chart_df = quality_df.sort_values(
    "row_count",
    ascending=True,
)

with chart_col1:
    row_count_figure = px.bar(
        row_chart_df,
        x="row_count",
        y="dataset",
        orientation="h",
        color="row_count",
        color_continuous_scale=[
            "#DDD6FE",
            PHONEPE_LIGHT_PURPLE,
            PHONEPE_PURPLE,
        ],
        labels={
            "row_count": "Row count",
            "dataset": "Dataset",
        },
        title="Rows across monitored analytics datasets",
    )

    row_count_figure.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Rows: %{x:,.0f}"
            "<extra></extra>"
        )
    )

    row_count_figure.update_layout(
        coloraxis_showscale=False
    )

    apply_chart_layout(
        row_count_figure,
        height=500,
        show_legend=False,
    )

    st.plotly_chart(
        row_count_figure,
        use_container_width=True,
    )


coverage_chart_df = quality_df.dropna(
    subset=[
        "quarter_coverage"
    ]
).sort_values(
    "quarter_coverage",
    ascending=True,
)

with chart_col2:
    coverage_figure = px.bar(
        coverage_chart_df,
        x="quarter_coverage",
        y="dataset",
        orientation="h",
        color="quarter_coverage",
        color_continuous_scale=[
            "#DBEAFE",
            PHONEPE_BLUE,
            PHONEPE_PURPLE,
        ],
        labels={
            "quarter_coverage":
                "Covered quarters",
            "dataset":
                "Dataset",
        },
        title="Historical period coverage",
    )

    coverage_figure.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Quarters covered: %{x:.0f}"
            "<extra></extra>"
        )
    )

    coverage_figure.update_layout(
        coloraxis_showscale=False
    )

    apply_chart_layout(
        coverage_figure,
        height=500,
        show_legend=False,
    )

    st.plotly_chart(
        coverage_figure,
        use_container_width=True,
    )


# ============================================================
# COVERAGE TIMELINE
# ============================================================

st.markdown("### Dataset coverage timeline")

timeline_df = quality_df.copy()

timeline_df["coverage_start"] = (
    timeline_df["first_period"]
    .apply(quarter_to_start_date)
)

timeline_df["coverage_end"] = (
    timeline_df["last_period"]
    .apply(quarter_to_start_date)
    + pd.DateOffset(months=3)
    - pd.Timedelta(days=1)
)

timeline_df = timeline_df.dropna(
    subset=[
        "coverage_start",
        "coverage_end",
    ]
)

timeline_figure = px.timeline(
    timeline_df,
    x_start="coverage_start",
    x_end="coverage_end",
    y="dataset",
    color="dataset",
    hover_data=[
        "first_period",
        "last_period",
        "row_count",
    ],
    title=(
        "Historical coverage by analytics dataset"
    ),
)

timeline_figure.update_yaxes(
    autorange="reversed"
)

timeline_figure.update_layout(
    showlegend=False
)

apply_chart_layout(
    timeline_figure,
    height=460,
    show_legend=False,
)

st.plotly_chart(
    timeline_figure,
    use_container_width=True,
)


# ============================================================
# QUALITY CHECK RESULTS
# ============================================================

st.markdown("### Automated quality checks")

status_order = {
    "FAIL": 0,
    "WARNING": 1,
    "PASS": 2,
}

checks_df["status_order"] = (
    checks_df["Status"]
    .map(status_order)
)

checks_df = checks_df.sort_values(
    [
        "status_order",
        "Layer",
        "Check",
    ]
).drop(
    columns=[
        "status_order"
    ]
)

st.dataframe(
    checks_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Status": st.column_config.TextColumn(
            width="small"
        ),
        "Layer": st.column_config.TextColumn(
            width="medium"
        ),
        "Check": st.column_config.TextColumn(
            width="large"
        ),
        "Result": st.column_config.TextColumn(
            width="large"
        ),
    },
    height=520,
)


# ============================================================
# PLATFORM ARCHITECTURE
# ============================================================

st.markdown("### Lakehouse platform layers")

layer_col1, layer_col2, layer_col3 = (
    st.columns(3)
)

with layer_col1:
    render_insight_card(
        title="Amazon S3 · Raw layer",
        message=(
            "11,184 versioned PhonePe Pulse JSON "
            "files retained with ingestion manifests "
            "and source commit traceability."
        ),
        accent_color=PHONEPE_ORANGE,
        icon="☁",
    )

with layer_col2:
    render_insight_card(
        title="Databricks · Bronze and Silver",
        message=(
            "Raw JSON is preserved in Bronze and "
            "transformed into validated, typed Delta "
            "tables in the Silver layer."
        ),
        accent_color=PHONEPE_BLUE,
        icon="◇",
    )

with layer_col3:
    render_insight_card(
        title="dbt · Gold analytics layer",
        message=(
            "Tested marts provide national, state, "
            "district, category, ranking and ML-ready "
            "analytics datasets."
        ),
        accent_color=PHONEPE_PURPLE,
        icon="◆",
    )

layer_col4, layer_col5, layer_col6 = (
    st.columns(3)
)

with layer_col4:
    render_insight_card(
        title="MLflow · Model governance",
        message=(
            "The residual Random Forest is tracked, "
            "versioned and registered in Unity Catalog "
            "with the Champion alias."
        ),
        accent_color=PHONEPE_GREEN,
        icon="⚙",
    )

with layer_col5:
    render_insight_card(
        title="Batch forecasting",
        message=(
            f"{forecast_state_count} state and UT "
            f"forecasts are available for "
            f"{forecast_period}."
        ),
        positive=(
            forecast_state_count
            == EXPECTED_FORECAST_STATES
        ),
        icon="↗",
    )

with layer_col6:
    render_insight_card(
        title="Streamlit · Consumption layer",
        message=(
            "Interactive dashboards expose Gold marts "
            "and production ML forecasts for decision "
            "support."
        ),
        accent_color=PHONEPE_LIGHT_PURPLE,
        icon="▣",
    )


# ============================================================
# MODEL MONITORING
# ============================================================

st.markdown("### Model monitoring")

model_col1, model_col2, model_col3 = (
    st.columns(3)
)

with model_col1:
    render_kpi_card(
        title="Champion test WMAPE",
        value=f"{MODEL_TEST_WMAPE:.2f}%",
        subtitle="Untouched time-based test set",
        positive=True,
        icon="✓",
    )

with model_col2:
    render_kpi_card(
        title="Naive baseline WMAPE",
        value=f"{NAIVE_TEST_WMAPE:.2f}%",
        subtitle="Last-quarter forecast baseline",
        icon="◷",
    )

with model_col3:
    render_kpi_card(
        title="Relative improvement",
        value=f"{MODEL_IMPROVEMENT:.2f}%",
        subtitle="Champion versus naive baseline",
        positive=True,
        icon="↗",
    )


# ============================================================
# MONITORING INSIGHTS
# ============================================================

st.markdown("### Monitoring summary")

insight_col1, insight_col2, insight_col3 = (
    st.columns(3)
)

with insight_col1:
    render_insight_card(
        title="Dataset availability",
        message=(
            f"{healthy_dataset_count} of "
            f"{dataset_count} monitored analytics "
            "datasets contain records."
        ),
        positive=(
            healthy_dataset_count
            == dataset_count
        ),
        icon="✓",
    )

with insight_col2:
    render_insight_card(
        title="Reporting freshness",
        message=(
            f"The latest available analytics period "
            f"is {latest_data_period}. "
            f"{aligned_latest_periods} datasets are "
            "aligned to this period."
        ),
        accent_color=PHONEPE_BLUE,
        icon="◷",
    )

with insight_col3:
    render_insight_card(
        title="Forecast integrity",
        message=(
            f"The latest batch contains "
            f"{missing_forecast_count} missing and "
            f"{negative_forecast_count} negative "
            "forecast values."
        ),
        positive=(
            missing_forecast_count == 0
            and negative_forecast_count == 0
            and forecast_available
        ),
        icon="⚙",
    )


# ============================================================
# FORECAST ERROR INFORMATION
# ============================================================

if forecast_error_message:
    with st.expander(
        "Forecast monitoring connection details"
    ):
        st.error(
            forecast_error_message
        )


# ============================================================
# DOWNLOAD MONITORING REPORT
# ============================================================

st.markdown("### Export monitoring report")

export_df = checks_df.copy()

export_df["generated_at_utc"] = (
    pd.Timestamp.now(tz="UTC")
    .isoformat()
)

quality_csv = export_df.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="Download quality-check report",
    data=quality_csv,
    file_name=(
        "phonepe_platform_quality_report.csv"
    ),
    mime="text/csv",
    use_container_width=True,
)