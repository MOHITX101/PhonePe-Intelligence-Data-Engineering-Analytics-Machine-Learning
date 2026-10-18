"""
Reusable visual components for the PhonePe Streamlit dashboard.

These components support the argument styles used across:
- Executive Overview
- State Performance
- District Intelligence
"""

import html

import streamlit as st


# ============================================================
# COLOURS
# ============================================================

PHONEPE_PURPLE = "#5F259F"
PHONEPE_LIGHT_PURPLE = "#A855F7"

POSITIVE_GREEN = "#10B981"
NEGATIVE_RED = "#EF4444"
WARNING_ORANGE = "#F59E0B"
INFORMATION_BLUE = "#3B82F6"
NEUTRAL_GREY = "#64748B"


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _escape(value):
    """
    Convert a value into HTML-safe text.
    """

    if value is None:
        return ""

    return html.escape(str(value))


def _get_delta_color(
    delta=None,
    positive=None,
):
    """
    Determine the colour used for a KPI delta.

    The explicit positive argument takes priority.
    """

    if positive is True:
        return POSITIVE_GREEN

    if positive is False:
        return NEGATIVE_RED

    if delta is None:
        return NEUTRAL_GREY

    delta_text = str(delta).strip()

    if (
        delta_text.startswith("-")
        or delta_text.startswith("▼")
        or delta_text.startswith("↓")
    ):
        return NEGATIVE_RED

    if (
        delta_text.startswith("+")
        or delta_text.startswith("▲")
        or delta_text.startswith("↑")
    ):
        return POSITIVE_GREEN

    return NEUTRAL_GREY


def _get_insight_color(
    accent_color=None,
    tone=None,
    positive=None,
):
    """
    Determine the colour used for an insight card.
    """

    if accent_color:
        return accent_color

    if positive is True:
        return POSITIVE_GREEN

    if positive is False:
        return NEGATIVE_RED

    if tone is None:
        return PHONEPE_PURPLE

    normalized_tone = str(tone).strip().lower()

    tone_colours = {
        "positive": POSITIVE_GREEN,
        "success": POSITIVE_GREEN,
        "growth": POSITIVE_GREEN,
        "negative": NEGATIVE_RED,
        "danger": NEGATIVE_RED,
        "decline": NEGATIVE_RED,
        "warning": WARNING_ORANGE,
        "attention": WARNING_ORANGE,
        "information": INFORMATION_BLUE,
        "info": INFORMATION_BLUE,
        "neutral": NEUTRAL_GREY,
        "purple": PHONEPE_PURPLE,
    }

    return tone_colours.get(
        normalized_tone,
        PHONEPE_PURPLE,
    )


# ============================================================
# KPI CARD
# ============================================================

def render_kpi_card(
    label=None,
    value="—",
    delta=None,
    help_text=None,
    icon="◆",
    positive=None,
    *,
    title=None,
    subtitle=None,
    **kwargs,
):
    """
    Render a modern KPI card.

    Supported naming styles:

    render_kpi_card(
        label="Transactions",
        value="38.7B",
        help_text="Quarterly volume"
    )

    render_kpi_card(
        title="Transactions",
        value="38.7B",
        subtitle="Quarter-over-quarter",
        positive=True
    )
    """

    card_title = (
        title
        or label
        or kwargs.get("heading")
        or "Metric"
    )

    card_subtitle = (
        subtitle
        or help_text
        or kwargs.get("description")
        or ""
    )

    delta_color = _get_delta_color(
        delta=delta,
        positive=positive,
    )

    if delta is not None and str(delta).strip():
        delta_html = (
            f'<div style="'
            f'display:inline-flex;'
            f'align-items:center;'
            f'margin-top:10px;'
            f'padding:4px 10px;'
            f'border-radius:999px;'
            f'background:{delta_color}18;'
            f'color:{delta_color};'
            f'font-size:0.78rem;'
            f'font-weight:700;'
            f'line-height:1.2;'
            f'">'
            f'{_escape(delta)}'
            f'</div>'
        )
    else:
        delta_html = ""

    if card_subtitle:
        subtitle_html = (
            f'<div style="'
            f'margin-top:8px;'
            f'color:#7C7485;'
            f'font-size:0.77rem;'
            f'line-height:1.4;'
            f'">'
            f'{_escape(card_subtitle)}'
            f'</div>'
        )
    else:
        subtitle_html = ""

    card_html = (
        f'<div style="'
        f'min-height:166px;'
        f'padding:18px;'
        f'margin-bottom:14px;'
        f'border:1px solid rgba(95,37,159,0.18);'
        f'border-radius:18px;'
        f'background:'
        f'linear-gradient('
        f'145deg,'
        f'rgba(255,255,255,0.99),'
        f'rgba(248,245,255,0.97)'
        f');'
        f'box-shadow:'
        f'0 10px 28px rgba(60,20,100,0.08);'
        f'overflow:hidden;'
        f'">'
        f'<div style="'
        f'display:flex;'
        f'align-items:flex-start;'
        f'justify-content:space-between;'
        f'gap:12px;'
        f'">'
        f'<div style="'
        f'color:#6B6475;'
        f'font-size:0.78rem;'
        f'font-weight:700;'
        f'letter-spacing:0.04em;'
        f'text-transform:uppercase;'
        f'line-height:1.4;'
        f'">'
        f'{_escape(card_title)}'
        f'</div>'
        f'<div style="'
        f'width:34px;'
        f'height:34px;'
        f'display:flex;'
        f'align-items:center;'
        f'justify-content:center;'
        f'flex-shrink:0;'
        f'border-radius:11px;'
        f'color:#FFFFFF;'
        f'background:'
        f'linear-gradient('
        f'135deg,'
        f'{PHONEPE_PURPLE},'
        f'{PHONEPE_LIGHT_PURPLE}'
        f');'
        f'box-shadow:'
        f'0 7px 17px rgba(95,37,159,0.24);'
        f'font-size:1rem;'
        f'font-weight:800;'
        f'">'
        f'{_escape(icon)}'
        f'</div>'
        f'</div>'
        f'<div style="'
        f'margin-top:13px;'
        f'color:#24152F;'
        f'font-size:clamp(1.45rem,2vw,2rem);'
        f'font-weight:800;'
        f'line-height:1.1;'
        f'letter-spacing:-0.03em;'
        f'word-break:break-word;'
        f'">'
        f'{_escape(value)}'
        f'</div>'
        f'{delta_html}'
        f'{subtitle_html}'
        f'</div>'
    )

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )


# ============================================================
# INSIGHT CARD
# ============================================================

def render_insight_card(
    title=None,
    body=None,
    accent_color=None,
    *,
    heading=None,
    text=None,
    message=None,
    icon="✦",
    tone=None,
    positive=None,
    color=None,
    **kwargs,
):
    """
    Render a modern dashboard insight card.

    Supported naming styles:

    render_insight_card(
        title="Volume leader",
        body="Maharashtra leads transaction activity."
    )

    render_insight_card(
        title="Growth insight",
        message="Transaction volume increased.",
        positive=True
    )

    render_insight_card(
        heading="User adoption",
        text="Registered users increased."
    )
    """

    card_title = (
        title
        or heading
        or kwargs.get("label")
        or "Insight"
    )

    card_body = (
        body
        or message
        or text
        or kwargs.get("description")
        or ""
    )

    selected_accent = (
        accent_color
        or color
        or kwargs.get("accent")
    )

    final_accent_color = _get_insight_color(
        accent_color=selected_accent,
        tone=tone,
        positive=positive,
    )

    card_html = (
        f'<div style="'
        f'min-height:155px;'
        f'padding:18px;'
        f'margin-bottom:14px;'
        f'border:1px solid {final_accent_color}2E;'
        f'border-left:4px solid {final_accent_color};'
        f'border-radius:16px;'
        f'background:'
        f'linear-gradient('
        f'145deg,'
        f'rgba(255,255,255,0.99),'
        f'rgba(248,245,255,0.96)'
        f');'
        f'box-shadow:'
        f'0 9px 24px rgba(60,20,100,0.07);'
        f'overflow:hidden;'
        f'">'
        f'<div style="'
        f'display:flex;'
        f'align-items:center;'
        f'gap:9px;'
        f'margin-bottom:11px;'
        f'">'
        f'<div style="'
        f'width:30px;'
        f'height:30px;'
        f'display:flex;'
        f'align-items:center;'
        f'justify-content:center;'
        f'flex-shrink:0;'
        f'border-radius:10px;'
        f'color:#FFFFFF;'
        f'background:{final_accent_color};'
        f'font-size:0.9rem;'
        f'font-weight:800;'
        f'">'
        f'{_escape(icon)}'
        f'</div>'
        f'<div style="'
        f'color:#2E193A;'
        f'font-size:0.92rem;'
        f'font-weight:800;'
        f'line-height:1.35;'
        f'">'
        f'{_escape(card_title)}'
        f'</div>'
        f'</div>'
        f'<div style="'
        f'color:#6B6475;'
        f'font-size:0.86rem;'
        f'line-height:1.6;'
        f'word-break:break-word;'
        f'">'
        f'{_escape(card_body)}'
        f'</div>'
        f'</div>'
    )

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )