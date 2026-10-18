from pathlib import Path

import streamlit as st


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Pulse Intelligence",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# GLOBAL CSS
# ============================================================

APP_DIRECTORY = Path(__file__).resolve().parent
CSS_FILE = APP_DIRECTORY / "assets" / "styles.css"

if CSS_FILE.exists():
    st.markdown(
        f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )


# ============================================================
# SIDEBAR BRAND
# ============================================================

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-logo">P</div>
            <div>
                <div class="brand-title">Pulse Intelligence</div>
                <div class="brand-subtitle">Payments Analytics Platform</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# APPLICATION NAVIGATION
# ============================================================

pages = {
    "Business Intelligence": [
        st.Page(
            "views/executive_overview.py",
            title="Executive Overview",
            icon="🏠",
            default=True,
        ),
        st.Page(
            "views/state_performance.py",
            title="State Performance",
            icon="📊",
        ),
        st.Page(
            "views/district_intelligence.py",
            title="District Intelligence",
            icon="🗺️",
        ),
        st.Page(
            "views/category_trends.py",
            title="Category Trends",
            icon="📈",
        ),
        st.Page(
            "views/geographic_leaders.py",
            title="Geographic Leaders",
            icon="🏆",
        ),
    ],
    "Machine Learning": [
        st.Page(
            "views/ml_forecasting.py",
            title="ML Forecasting",
            icon="🤖",
        ),
    ],
    "Platform Monitoring": [
        st.Page(
            "views/data_quality.py",
            title="Data Quality",
            icon="✅",
        ),
    ],
}

navigation = st.navigation(pages, position="sidebar")


# ============================================================
# SIDEBAR FOOTER
# ============================================================

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-footer">
            <div class="status-line">
                <span class="status-dot"></span>
                Data platform operational
            </div>
            <div class="status-caption">
                Databricks Lakehouse · dbt · MLflow
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


navigation.run()