"""
Data loading functions for the PhonePe Analytics dashboard.

All functions return pandas DataFrames from Databricks.
"""

import streamlit as st

from services.databricks_client import (
    get_table_name,
    run_query,
)


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def load_india_quarterly_kpis():
    """
    Load national quarterly PhonePe KPIs.
    """

    table_name = get_table_name(
        "mart_india_quarterly_kpis"
    )

    return run_query(
        f"""
        SELECT *
        FROM {table_name}
        ORDER BY period_start_date
        """
    )


def load_india_kpis():
    """
    Backward-compatible function name used by
    Executive Overview.
    """

    return load_india_quarterly_kpis()


# ============================================================
# STATE PERFORMANCE
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def load_state_quarterly_performance():
    """
    Load state-level quarterly performance metrics.
    """

    table_name = get_table_name(
        "mart_state_quarterly_performance"
    )

    return run_query(
        f"""
        SELECT
            state_slug,
            year,
            quarter,
            period,
            period_start_date,

            total_transaction_count,
            registered_user_count,
            registered_merchant_count,

            transaction_yoy_growth_pct,
            transactions_per_registered_user,

            transaction_rank,
            registered_user_rank

        FROM {table_name}

        ORDER BY
            period_start_date,
            transaction_rank,
            state_slug
        """
    )


# ============================================================
# DISTRICT INTELLIGENCE
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def load_district_quarterly_performance():
    """
    Load district-level quarterly performance metrics.
    """

    table_name = get_table_name(
        "mart_district_quarterly_performance"
    )

    return run_query(
        f"""
        SELECT
            state_slug,
            district_slug,
            district_name,

            year,
            quarter,
            period,
            period_start_date,

            total_transaction_count,
            total_transaction_amount,
            average_transaction_value,

            registered_user_count,
            registered_merchant_count,

            national_transaction_count_rank,
            national_transaction_amount_rank,

            state_transaction_count_rank,
            state_transaction_amount_rank,

            has_transaction_data,
            has_user_data,
            has_merchant_data

        FROM {table_name}

        ORDER BY
            period_start_date,
            national_transaction_count_rank,
            state_slug,
            district_slug
        """
    )


# ============================================================
# TRANSACTION CATEGORY TRENDS
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def load_transaction_category_trends():
    """
    Load quarterly transaction-category metrics.
    """

    table_name = get_table_name(
        "mart_transaction_category_trends"
    )

    return run_query(
        f"""
        SELECT *
        FROM {table_name}
        ORDER BY
            period_start_date,
            file_scope,
            geography_slug,
            category_rank
        """
    )


# ============================================================
# TOP GEOGRAPHIES
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def load_top_geographies():
    """
    Load ranked states, districts and pincodes.
    """

    table_name = get_table_name(
        "mart_top_geographies"
    )

    return run_query(
        f"""
        SELECT *
        FROM {table_name}
        ORDER BY
            period_start_date,
            metric_domain,
            geography_level,
            rank_position
        """
    )


# ============================================================
# ML TRAINING FEATURES
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def load_ml_state_features():
    """
    Load historical state-level ML features.
    """

    table_name = get_table_name(
        "mart_ml_state_features"
    )

    return run_query(
        f"""
        SELECT *
        FROM {table_name}
        ORDER BY
            feature_period_start_date,
            state_slug
        """
    )


# ============================================================
# ML SCORING FEATURES
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def load_ml_state_scoring_features():
    """
    Load the latest state records used for batch scoring.
    """

    table_name = get_table_name(
        "mart_ml_state_scoring_features"
    )

    return run_query(
        f"""
        SELECT *
        FROM {table_name}
        ORDER BY state_slug
        """
    )


# ============================================================
# ML FORECAST OUTPUT
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def load_state_transaction_forecasts():
    """
    Load state-level transaction forecasts generated
    by the Champion model.
    """

    return run_query(
        """
        SELECT *
        FROM workspace.ml.state_transaction_forecasts
        """
    )


# ============================================================
# DATA-QUALITY SUMMARY
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def load_dashboard_data_quality():
    """
    Load row counts and time coverage for the main
    dashboard datasets.
    """

    india_table = get_table_name(
        "mart_india_quarterly_kpis"
    )

    state_table = get_table_name(
        "mart_state_quarterly_performance"
    )

    district_table = get_table_name(
        "mart_district_quarterly_performance"
    )

    category_table = get_table_name(
        "mart_transaction_category_trends"
    )

    geography_table = get_table_name(
        "mart_top_geographies"
    )

    ml_features_table = get_table_name(
        "mart_ml_state_features"
    )

    return run_query(
        f"""
        SELECT
            'India quarterly KPIs' AS dataset,
            COUNT(*) AS row_count,
            MIN(period) AS first_period,
            MAX(period) AS last_period
        FROM {india_table}

        UNION ALL

        SELECT
            'State quarterly performance' AS dataset,
            COUNT(*) AS row_count,
            MIN(period) AS first_period,
            MAX(period) AS last_period
        FROM {state_table}

        UNION ALL

        SELECT
            'District quarterly performance' AS dataset,
            COUNT(*) AS row_count,
            MIN(period) AS first_period,
            MAX(period) AS last_period
        FROM {district_table}

        UNION ALL

        SELECT
            'Transaction category trends' AS dataset,
            COUNT(*) AS row_count,
            MIN(period) AS first_period,
            MAX(period) AS last_period
        FROM {category_table}

        UNION ALL

        SELECT
            'Top geographies' AS dataset,
            COUNT(*) AS row_count,
            MIN(period) AS first_period,
            MAX(period) AS last_period
        FROM {geography_table}

        UNION ALL

        SELECT
            'ML state features' AS dataset,
            COUNT(*) AS row_count,
            MIN(feature_period) AS first_period,
            MAX(target_period) AS last_period
        FROM {ml_features_table}

        ORDER BY dataset
        """
    )


# ============================================================
# CACHE MANAGEMENT
# ============================================================

def clear_dashboard_data_cache():
    """
    Clear all cached dashboard queries.
    """

    st.cache_data.clear()