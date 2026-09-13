from __future__ import annotations

import os
import sys
import time
import subprocess

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from theme import inject_global_style, ACCENT


# ==========================================================
# PATHS
# ==========================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

DB_PATH = os.path.join(
    PROJECT_ROOT,
    "database",
    "macro_database.csv"
)

UPDATER_PATH = os.path.join(
    PROJECT_ROOT,
    "updater.py"
)


# ==========================================================
# STAT CARD
# ==========================================================

def _stat_card(label: str, value: str) -> str:

    return f"""
    <div class="stat-card">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{value}</div>
    </div>
    """


# ==========================================================
# REGIME MATRIX
# ==========================================================

REGIME_MATRIX = {

    # ======================================================
    # GROWTH ↑ / INFLATION ↓
    # ======================================================

    ("Growth ↑", "Inflation ↓", "Bull Flattening"): {
        "title": "Goldilocks + Bull Flattening",
        "best": "NASDAQ / Long UST / Gold",
        "good": "SP500",
        "weak": "WTI / Copper",
        "bias": "Risk-on + duration"
    },

    ("Growth ↑", "Inflation ↓", "Bull Steepening"): {
        "title": "Goldilocks + Bull Steepening",
        "best": "SP500 / Cyclicals / Long UST",
        "good": "NASDAQ / Gold",
        "weak": "WTI",
        "bias": "Risk-on + easing"
    },

    ("Growth ↑", "Inflation ↓", "Bear Flattening"): {
        "title": "Goldilocks + Bear Flattening",
        "best": "Cyclicals / SP500",
        "good": "NASDAQ",
        "weak": "Long UST",
        "bias": "Late-cycle tightening"
    },

    ("Growth ↑", "Inflation ↓", "Bear Steepening"): {
        "title": "Goldilocks + Bear Steepening",
        "best": "Cyclicals / Copper / WTI",
        "good": "SP500",
        "weak": "Long UST / Gold",
        "bias": "Growth / reflation"
    },


    # ======================================================
    # GROWTH ↑ / INFLATION ↑
    # ======================================================

    ("Growth ↑", "Inflation ↑", "Bull Flattening"): {
        "title": "Reflation + Bull Flattening",
        "best": "NASDAQ / Gold",
        "good": "SP500 / WTI",
        "weak": "Long UST",
        "bias": "Mixed risk-on"
    },

    ("Growth ↑", "Inflation ↑", "Bull Steepening"): {
        "title": "Reflation + Bull Steepening",
        "best": "Cyclicals / WTI / Copper",
        "good": "SP500",
        "weak": "Long UST",
        "bias": "Reflation"
    },

    ("Growth ↑", "Inflation ↑", "Bear Flattening"): {
        "title": "Reflation + Bear Flattening",
        "best": "WTI / Copper / Value",
        "good": "SP500",
        "weak": "NASDAQ / Long UST",
        "bias": "Late-cycle inflation"
    },

    ("Growth ↑", "Inflation ↑", "Bear Steepening"): {
        "title": "Reflation + Bear Steepening",
        "best": "WTI / Copper / Cyclicals",
        "good": "SP500",
        "weak": "Long UST / Gold",
        "bias": "Strong reflation"
    },


    # ======================================================
    # GROWTH ↓ / INFLATION ↓
    # ======================================================

    ("Growth ↓", "Inflation ↓", "Bull Flattening"): {
        "title": "Disinflation + Bull Flattening",
        "best": "Long UST / Gold",
        "good": "NASDAQ",
        "weak": "WTI / Copper",
        "bias": "Defensive duration"
    },

    ("Growth ↓", "Inflation ↓", "Bull Steepening"): {
        "title": "Recession + Bull Steepening",
        "best": "Long UST / Gold",
        "good": "USD",
        "weak": "SP500 / NASDAQ / WTI",
        "bias": "Recession / Fed easing"
    },

    ("Growth ↓", "Inflation ↓", "Bear Flattening"): {
        "title": "Weak Growth + Bear Flattening",
        "best": "Gold / USD",
        "good": "Defensives",
        "weak": "Long UST / Cyclicals",
        "bias": "Defensive"
    },

    ("Growth ↓", "Inflation ↓", "Bear Steepening"): {
        "title": "Weak Growth + Bear Steepening",
        "best": "USD / Defensives",
        "good": "Gold",
        "weak": "Stocks / Long UST",
        "bias": "Term-premium risk"
    },


    # ======================================================
    # GROWTH ↓ / INFLATION ↑
    # ======================================================

    ("Growth ↓", "Inflation ↑", "Bull Flattening"): {
        "title": "Stagflation + Bull Flattening",
        "best": "Gold / TIPS",
        "good": "USD",
        "weak": "NASDAQ / Cyclicals",
        "bias": "Inflation hedge"
    },

    ("Growth ↓", "Inflation ↑", "Bull Steepening"): {
        "title": "Stagflation + Bull Steepening",
        "best": "Gold / TIPS",
        "good": "USD",
        "weak": "Stocks / Oil",
        "bias": "Mixed but inflation-led"
    },

    ("Growth ↓", "Inflation ↑", "Bear Flattening"): {
        "title": "Stagflation + Bear Flattening",
        "best": "Gold / USD",
        "good": "TIPS",
        "weak": "Long UST / NASDAQ",
        "bias": "Very defensive"
    },

    ("Growth ↓", "Inflation ↑", "Bear Steepening"): {
        "title": "Stagflation + Bear Steepening",
        "best": "Gold / Oil / USD",
        "good": "Copper / TIPS",
        "weak": "Long UST / NASDAQ / SP500",
        "bias": "Strong stagflation"
    },
}


# ==========================================================
# DATE HELPERS
# ==========================================================

def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    if "Date" not in df.columns:
        return pd.DataFrame()

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["Date"]
    )

    df = df.sort_values("Date")

    return df


# ==========================================================
# GENERIC CHANGE
# ==========================================================

def _latest_valid_change(df: pd.DataFrame, column: str, days: int, asof: pd.Timestamp | None = None) -> float:

    if column not in df.columns:
        return np.nan

    temp = df[["Date", column]].dropna(subset=[column]).copy()
    if temp.empty:
        return np.nan

    temp["Date"] = pd.to_datetime(temp["Date"], errors="coerce")
    temp = temp.dropna(subset=["Date"])
    if temp.empty:
        return np.nan

    temp = temp.sort_values("Date")

    if asof is not None:
        temp = temp[temp["Date"] <= asof]
        if temp.empty:
            return np.nan

    latest_date = temp["Date"].iloc[-1]
    latest_value = pd.to_numeric(temp[column].iloc[-1], errors="coerce")

    if pd.isna(latest_value):
        return np.nan

    target_date = latest_date - pd.Timedelta(days=days)
    prev = temp[temp["Date"] <= target_date]

    if prev.empty:
        return np.nan

    prev_value = pd.to_numeric(prev[column].iloc[-1], errors="coerce")

    if pd.isna(prev_value):
        return np.nan

    return float(latest_value - prev_value)


def _latest_yoy_rate(df: pd.DataFrame, column: str, months: int = 12, asof: pd.Timestamp | None = None) -> float:

    if column not in df.columns:
        return np.nan

    temp = df[["Date", column]].dropna(subset=[column]).copy()
    if temp.empty:
        return np.nan

    temp["Date"] = pd.to_datetime(temp["Date"], errors="coerce")
    temp[column] = pd.to_numeric(temp[column], errors="coerce")
    temp = temp.dropna(subset=["Date", column])
    temp = temp.sort_values("Date")

    if temp.empty:
        return np.nan

    if asof is not None:
        temp = temp[temp["Date"] <= asof]
        if temp.empty:
            return np.nan

    latest_date = temp["Date"].iloc[-1]
    latest_value = temp[column].iloc[-1]

    target_date = latest_date - pd.DateOffset(months=months)
    prev = temp[temp["Date"] <= target_date]

    if prev.empty:
        return np.nan

    prev_value = prev[column].iloc[-1]

    if pd.isna(prev_value) or prev_value == 0:
        return np.nan

    return float((latest_value / prev_value - 1) * 100)


def _latest_yoy_rate_at_offset(df: pd.DataFrame, column: str, offset_months: int = 3, asof: pd.Timestamp | None = None) -> float:

    if column not in df.columns:
        return np.nan

    temp = df[["Date", column]].dropna(subset=[column]).copy()
    if temp.empty:
        return np.nan

    temp["Date"] = pd.to_datetime(temp["Date"], errors="coerce")
    temp[column] = pd.to_numeric(temp[column], errors="coerce")
    temp = temp.dropna(subset=["Date", column])
    temp = temp.sort_values("Date")

    if temp.empty:
        return np.nan

    if asof is not None:
        temp = temp[temp["Date"] <= asof]
        if temp.empty:
            return np.nan

    latest_date = temp["Date"].iloc[-1]
    target_date = latest_date - pd.DateOffset(months=offset_months)

    current_candidates = temp[temp["Date"] <= target_date]
    if current_candidates.empty:
        return np.nan

    current_date = current_candidates["Date"].iloc[-1]
    current_value = current_candidates[column].iloc[-1]

    yoy_target = current_date - pd.DateOffset(months=12)
    previous_candidates = temp[temp["Date"] <= yoy_target]

    if previous_candidates.empty:
        return np.nan

    previous_value = previous_candidates[column].iloc[-1]

    if pd.isna(previous_value) or previous_value == 0:
        return np.nan

    return float((current_value / previous_value - 1) * 100)


# ==========================================================
# GROWTH REGIME and INFLATION REGIME
# ==========================================================

GROWTH_SIGNAL_LABELS = {
    "cli_3m": "OECD CLI — تغییر ۳ ماهه",
    "cli_6m": "OECD CLI — تغییر ۶ ماهه",
    "cfnai_3m": "CFNAI-MA3 — تغییر ۳ ماهه",
    "gdp_1y": "Real GDP — تغییر ۱ ساله",
}


def compute_growth_signals(df: pd.DataFrame, asof: pd.Timestamp | None = None) -> dict:
    """هر سیگنال رشد رو جدا برمی‌گردونه (نه فقط جمعشون) تا بشه دید هرکدوم
    چقدر مثبت/منفی بوده، نه فقط رأی +۱/−۱ نهایی‌شون."""

    signals = {}

    cli_3m = _latest_valid_change(df, "USALOLITOAASTSAM", 90, asof=asof)
    if pd.notna(cli_3m):
        signals["cli_3m"] = (cli_3m, 1 if cli_3m > 0 else -1)

    cli_6m = _latest_valid_change(df, "USALOLITOAASTSAM", 180, asof=asof)
    if pd.notna(cli_6m):
        signals["cli_6m"] = (cli_6m, 1 if cli_6m > 0 else -1)

    cfnai_3m = _latest_valid_change(df, "CFNAIMA3", 90, asof=asof)
    if pd.notna(cfnai_3m):
        signals["cfnai_3m"] = (cfnai_3m, 1 if cfnai_3m > 0 else -1)

    gdp_1y = _latest_valid_change(df, "A191RO1Q156NBEA", 365, asof=asof)
    if pd.notna(gdp_1y):
        signals["gdp_1y"] = (gdp_1y, 1 if gdp_1y > 0 else -1)

    score = sum(s for _, s in signals.values())
    label = "Growth ?" if not signals else ("Growth ↑" if score > 0 else "Growth ↓")

    return {"signals": signals, "score": score, "label": label}


def detect_growth_regime(df: pd.DataFrame, asof: pd.Timestamp | None = None):
    return compute_growth_signals(df, asof=asof)["label"]


INFLATION_SIGNAL_LABELS = {
    "cpi_yoy_trend": "Core CPI YoY — روند ۳ ماهه",
    "pce_yoy_trend": "Core PCE YoY — روند ۳ ماهه",
    "breakeven_10y": "10Y Breakeven — تغییر ۳ ماهه",
    "forward_5y5y": "5Y5Y Forward — تغییر ۳ ماهه",
}


def compute_inflation_signals(df: pd.DataFrame, asof: pd.Timestamp | None = None) -> dict:

    signals = {}

    cpi_now = _latest_yoy_rate(df, "CPILFESL", 12, asof=asof)
    cpi_3m_ago = _latest_yoy_rate_at_offset(df, "CPILFESL", 3, asof=asof)
    if pd.notna(cpi_now) and pd.notna(cpi_3m_ago):
        signals["cpi_yoy_trend"] = (cpi_now - cpi_3m_ago, 1 if cpi_now > cpi_3m_ago else -1)

    pce_now = _latest_yoy_rate(df, "PCEPILFE", 12, asof=asof)
    pce_3m_ago = _latest_yoy_rate_at_offset(df, "PCEPILFE", 3, asof=asof)
    if pd.notna(pce_now) and pd.notna(pce_3m_ago):
        signals["pce_yoy_trend"] = (pce_now - pce_3m_ago, 1 if pce_now > pce_3m_ago else -1)

    be10 = _latest_valid_change(df, "T10YIE", 90, asof=asof)
    if pd.notna(be10):
        signals["breakeven_10y"] = (be10, 1 if be10 > 0 else -1)

    fwd = _latest_valid_change(df, "T5YIFR", 90, asof=asof)
    if pd.notna(fwd):
        signals["forward_5y5y"] = (fwd, 1 if fwd > 0 else -1)

    score = sum(s for _, s in signals.values())
    label = "Inflation ?" if not signals else ("Inflation ↑" if score > 0 else "Inflation ↓")

    return {"signals": signals, "score": score, "label": label}


def detect_inflation_regime(df: pd.DataFrame, asof: pd.Timestamp | None = None):
    return compute_inflation_signals(df, asof=asof)["label"]


# ==========================================================
# CURRENT CURVE REGIME
# ==========================================================

def detect_current_curve_regime(
    df: pd.DataFrame,
    lookback: int = 20
):

    required = [
        "2Y",
        "10Y"
    ]

    if not all(
        col in df.columns
        for col in required
    ):
        return "Unknown"

    temp = df[
        [
            "Date",
            "2Y",
            "10Y"
        ]
    ].copy()

    temp["2Y"] = pd.to_numeric(
        temp["2Y"],
        errors="coerce"
    )

    temp["10Y"] = pd.to_numeric(
        temp["10Y"],
        errors="coerce"
    )

    temp = temp.dropna(
        subset=[
            "2Y",
            "10Y"
        ]
    )

    temp = temp.sort_values(
        "Date"
    )

    if len(temp) <= lookback:
        return "Unknown"

    current = temp.iloc[-1]

    previous = temp.iloc[
        -1 - lookback
    ]

    y2 = current["2Y"]
    y10 = current["10Y"]

    y2_prev = previous["2Y"]
    y10_prev = previous["10Y"]

    spread = y10 - y2

    spread_prev = (
        y10_prev
        - y2_prev
    )

    spread_change = (
        spread
        - spread_prev
    )

    # ------------------------------------------------------
    # STEEPENING
    # ------------------------------------------------------

    if spread_change > 0:

        if (
            y2 < y2_prev
            and y10 < y10_prev
        ):
            return "Bull Steepening"

        if (
            y2 > y2_prev
            and y10 > y10_prev
        ):
            return "Bear Steepening"

        return "Steepener Twist"

    # ------------------------------------------------------
    # FLATTENING
    # ------------------------------------------------------

    if spread_change < 0:

        if (
            y2 < y2_prev
            and y10 < y10_prev
        ):
            return "Bull Flattening"

        if (
            y2 > y2_prev
            and y10 > y10_prev
        ):
            return "Bear Flattening"

        return "Flattener Twist"

    return "Neutral"


# ==========================================================
# RENDER MATRIX
# ==========================================================

def render_regime_matrix(
    growth_regime,
    inflation_regime,
    curve_regime
):

    curve_regimes = [
        "Bull Flattening",
        "Bull Steepening",
        "Bear Flattening",
        "Bear Steepening",
    ]

    macro_regimes = [
        ("Growth ↑", "Inflation ↓"),
        ("Growth ↑", "Inflation ↑"),
        ("Growth ↓", "Inflation ↓"),
        ("Growth ↓", "Inflation ↑"),
    ]

    # ------------------------------------------------------
    # HEADER
    # ------------------------------------------------------

    html_parts = []

    html_parts.append(
        """
        <div class="matrix">
            <div class="empty-header"></div>

            <div class="header">
                Bull Flattening
            </div>

            <div class="header">
                Bull Steepening
            </div>

            <div class="header">
                Bear Flattening
            </div>

            <div class="header">
                Bear Steepening
            </div>
        """
    )

    # ------------------------------------------------------
    # CELLS
    # ------------------------------------------------------

    for growth, inflation in macro_regimes:

        # Row label

        row_class = "row-label"

        row_label = f"""
        <div class="{row_class}">
            <div>
                <div>{growth}</div>
                <div>{inflation}</div>
            </div>
        </div>
        """

        html_parts.append(
            row_label
        )

        # Four curve states

        for curve in curve_regimes:

            data = REGIME_MATRIX[
                (
                    growth,
                    inflation,
                    curve
                )
            ]

            active = (
                growth == growth_regime
                and inflation == inflation_regime
                and curve == curve_regime
            )

            active_class = (
                " current"
                if active
                else ""
            )

            badge = ""

            if active:

                badge = """
                <div class="badge">
                    CURRENT
                </div>
                """

            cell = f"""
            <div class="cell{active_class}">

                <div class="cell-title">
                    {data["title"]}
                </div>

                <div class="cell-bias">
                    {data["bias"]}
                </div>

                <div class="cell-body">

                    <div>
                        <span class="label">
                            Best
                        </span>
                        {data["best"]}
                    </div>

                    <div>
                        <span class="label">
                            Good
                        </span>
                        {data["good"]}
                    </div>

                    <div>
                        <span class="label">
                            Weak
                        </span>
                        {data["weak"]}
                    </div>

                </div>

                {badge}

            </div>
            """

            html_parts.append(
                cell
            )

    html_parts.append(
        """
        </div>
        """
    )

    html = "".join(
        html_parts
    )

    full_html = f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <style>

            html,
            body {{
                margin: 0;
                padding: 0;
                background: transparent;
            }}

            body {{
                font-family:
                    -apple-system,
                    BlinkMacSystemFont,
                    "Segoe UI",
                    Arial,
                    sans-serif;

                color: #f1f1f1;

                overflow-x: auto;
            }}

            .matrix {{
                min-width: 1050px;

                display: grid;

                grid-template-columns:
                    125px
                    repeat(
                        4,
                        minmax(210px, 1fr)
                    );

                gap: 10px;

                align-items: stretch;
            }}

            .empty-header {{
                min-height: 35px;
            }}

            .header {{
                text-align: center;

                min-height: 35px;

                display: flex;
                align-items: center;
                justify-content: center;

                font-size: 12px;

                font-weight: 800;

                color: #d8d8d8;
            }}

            .row-label {{
                min-height: 180px;

                display: flex;

                align-items: center;

                justify-content: center;

                text-align: center;

                border:
                    1px solid
                    rgba(255,255,255,0.09);

                border-radius: 14px;

                background:
                    rgba(255,255,255,0.025);

                font-size: 12px;

                font-weight: 800;

                color: #d8d8d8;

                line-height: 1.6;
            }}

            .cell {{
                min-height: 180px;

                padding: 15px;

                border:
                    1px solid
                    rgba(255,255,255,0.09);

                border-radius: 14px;

                background:
                    rgba(255,255,255,0.025);

                box-sizing: border-box;

                transition:
                    transform 0.18s ease,
                    border-color 0.18s ease,
                    box-shadow 0.18s ease;
            }}

            .cell:hover {{
                transform:
                    translateY(-2px);

                border-color:
                    {ACCENT};
            }}

            .cell.current {{
                border:
                    2px solid
                    {ACCENT};

                box-shadow:
                    0 0 20px
                    {ACCENT}33;
            }}

            .cell-title {{
                font-size: 13px;

                font-weight: 800;

                color: #f2f2f2;

                margin-bottom: 8px;

                line-height: 1.3;
            }}

            .cell-bias {{
                font-size: 10px;

                color: #8f949e;

                margin-bottom: 12px;

                line-height: 1.4;
            }}

            .cell-body {{
                font-size: 11px;

                color: #d8d8d8;

                line-height: 1.7;
            }}

            .cell-body > div {{
                margin-bottom: 2px;
            }}

            .label {{
                display: inline-block;

                min-width: 36px;

                color: #8f949e;

                font-size: 10px;

                font-weight: 700;

                margin-right: 3px;
            }}

            .badge {{
                display: inline-block;

                margin-top: 8px;

                padding: 3px 8px;

                border-radius: 999px;

                background:
                    {ACCENT};

                color: #ffffff;

                font-size: 9px;

                font-weight: 800;

                letter-spacing: 0.3px;
            }}

        </style>

    </head>

    <body>

        {html}

    </body>

    </html>
    """

    components.html(
        full_html,
        height=830,
        scrolling=True
    )



def render_score_breakdown(df: pd.DataFrame, latest_date: pd.Timestamp):
    """اسکورکارت رشد/تورم برای این ماه و ماه قبل، کنار هم — تا معلوم بشه
    نتیجه‌ی نهایی (↑/↓) یه اجماع قویه یا یه رأی شکننده و نزدیک‌به‌مساوی."""

    asof_prev = latest_date - pd.DateOffset(months=1)

    growth_now = compute_growth_signals(df, asof=latest_date)
    growth_prev = compute_growth_signals(df, asof=asof_prev)

    inflation_now = compute_inflation_signals(df, asof=latest_date)
    inflation_prev = compute_inflation_signals(df, asof=asof_prev)

    def _fmt(val, sign):
        if pd.isna(val) or sign == 0:
            return "—"
        arrow = "▲" if sign > 0 else "▼"
        color = "#4caf50" if sign > 0 else "#d9534f"
        return f"<span style='color:{color};font-weight:700;'>{arrow} {val:+.2f}</span>"

    def _build_table(now, prev, labels):
        all_keys = list(dict.fromkeys(list(now["signals"].keys()) + list(prev["signals"].keys())))
        rows = ""

        for key in all_keys:
            label = labels.get(key, key)
            now_val, now_sign = now["signals"].get(key, (np.nan, 0))
            prev_val, prev_sign = prev["signals"].get(key, (np.nan, 0))

            flipped = now_sign != 0 and prev_sign != 0 and now_sign != prev_sign
            flip_marker = " 🔄" if flipped else ""

            rows += (
                "<tr>"
                f"<td style='padding:6px 10px;border:1px solid rgba(255,255,255,0.09);'>{label}{flip_marker}</td>"
                f"<td style='padding:6px 10px;border:1px solid rgba(255,255,255,0.09);text-align:center;'>{_fmt(now_val, now_sign)}</td>"
                f"<td style='padding:6px 10px;border:1px solid rgba(255,255,255,0.09);text-align:center;'>{_fmt(prev_val, prev_sign)}</td>"
                "</tr>"
            )

        score_row = (
            "<tr style='font-weight:800;background:rgba(255,255,255,0.04);'>"
            "<td style='padding:6px 10px;border:1px solid rgba(255,255,255,0.09);'>مجموع امتیاز</td>"
            f"<td style='padding:6px 10px;border:1px solid rgba(255,255,255,0.09);text-align:center;'>{now['score']:+d} → {now['label']}</td>"
            f"<td style='padding:6px 10px;border:1px solid rgba(255,255,255,0.09);text-align:center;'>{prev['score']:+d} → {prev['label']}</td>"
            "</tr>"
        )

        return (
            "<table style='width:100%;border-collapse:collapse;font-size:12px;'>"
            "<tr style='background:rgba(255,255,255,0.06);font-weight:800;'>"
            "<td style='padding:6px 10px;border:1px solid rgba(255,255,255,0.09);'>سیگنال</td>"
            "<td style='padding:6px 10px;border:1px solid rgba(255,255,255,0.09);text-align:center;'>این ماه</td>"
            "<td style='padding:6px 10px;border:1px solid rgba(255,255,255,0.09);text-align:center;'>ماه قبل</td>"
            "</tr>" + rows + score_row + "</table>"
        )

    with st.expander("🔍 جزئیات امتیازدهی Growth / Inflation (این ماه در برابر ماه قبل)"):
        st.caption(
            "هر سیگنال یا +۱ یا −۱ می‌ده؛ مجموع امتیازها رژیم رو تعیین می‌کنه. 🔄 یعنی جهت اون "
            "سیگنال نسبت به ماه قبل عوض شده. اگه مجموع نزدیک صفر باشه (مثلاً +۱ از ۴ سیگنال)، "
            "نتیجه شکننده‌ست و با یه سیگنال دیگه ممکنه برعکس بشه."
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Growth Signals**")
            st.markdown(_build_table(growth_now, growth_prev, GROWTH_SIGNAL_LABELS), unsafe_allow_html=True)
        with col2:
            st.markdown("**Inflation Signals**")
            st.markdown(_build_table(inflation_now, inflation_prev, INFLATION_SIGNAL_LABELS), unsafe_allow_html=True)


# ==========================================================
# SEASONALITY — میانگین بازدهی هر ماه تقویمی
# ==========================================================
# برای هر دارایی: بازدهی ماهانه (پایان‌ماه به پایان‌ماه) طی `years`
# سال اخیر رو حساب می‌کنیم، بعد بازدهی‌ها رو بر اساس شماره‌ی ماه
# تقویمی (۱=ژانویه ... ۱۲=دسامبر) گروه‌بندی و میانگین می‌گیریم.
# ماه جاری با آبی مشخص می‌شه (صرف‌نظر از مثبت/منفی بودنش)؛ بقیه‌ی
# ماه‌ها سبز (میانگین مثبت) یا قرمز (میانگین منفی).

SEASONALITY_ASSETS = [
    ("SP500", "S&P 500"),
    ("GOLD", "Gold"),
    ("EURUSD", "EUR/USD"),
]

MONTH_LABELS_EN = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _monthly_seasonality(df: pd.DataFrame, column: str, years: int = 15) -> pd.Series:
    """میانگین بازدهی هر ماه تقویمی (۱ تا ۱۲) طی `years` سال اخیر.
    خروجی یه Series با ایندکس ۱..۱۲ هست (مقدار NaN یعنی داده‌ی کافی
    برای اون ماه نبوده)."""

    if column not in df.columns:
        return pd.Series(dtype=float)

    temp = df[["Date", column]].dropna(subset=[column]).copy()
    if temp.empty:
        return pd.Series(dtype=float)

    temp["Date"] = pd.to_datetime(temp["Date"], errors="coerce")
    temp = temp.dropna(subset=["Date"]).sort_values("Date")
    if temp.empty:
        return pd.Series(dtype=float)

    latest_date = temp["Date"].max()
    cutoff = latest_date - pd.DateOffset(years=years)
    temp = temp[temp["Date"] >= cutoff]
    if temp.empty:
        return pd.Series(dtype=float)

    monthly_close = (
        temp.set_index("Date")[column]
        .resample("ME")
        .last()
        .dropna()
    )

    monthly_returns = monthly_close.pct_change().dropna() * 100
    if monthly_returns.empty:
        return pd.Series(dtype=float)

    seasonality = monthly_returns.groupby(monthly_returns.index.month).mean()

    return seasonality.reindex(range(1, 13))


def render_seasonality_chart(df: pd.DataFrame, column: str, label: str, years: int = 15):
    """بار-چارت seasonality رو برای یه دارایی رسم می‌کنه — یه چارت
    جدا برای هر دارایی، دقیقاً مثل الگوی این تصویر: عنوان + محور X
    = ماه‌ها + میله‌ی سبز/قرمز + ماه جاری آبی."""

    seasonality = _monthly_seasonality(df, column, years=years)

    if seasonality.empty or seasonality.isna().all():
        st.info(f"داده‌ی کافی برای seasonality «{label}» نیست.")
        return

    current_month = pd.Timestamp.now().month

    colors = []
    for month in range(1, 13):
        value = seasonality.get(month, np.nan)
        if month == current_month:
            colors.append("#5B8DEF")
        elif pd.isna(value):
            colors.append("rgba(255,255,255,0.12)")
        elif value >= 0:
            colors.append("#3fb968")
        else:
            colors.append("#d9534f")

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=MONTH_LABELS_EN,
            y=seasonality.values,
            marker_color=colors,
            hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        template="plotly_dark",
        title=f"{label} · Average Calendar-Month Return (~{years}y) · current month in blue",
        height=340,
        hovermode="x",
        yaxis_title="%",
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)


# ==========================================================
# STOCK-BOND ROLLING CORRELATION
# ==========================================================
# همبستگی غلتان بین بازدهی روزانه‌ی سهام (SP500) و اوراق (TLT) —
# روی دو پنجره‌ی ۳۰ و ۹۰ روزه، دقیقاً مثل عکس مرجع. زیر صفر یعنی
# رفتار سنتی hedge (سهام و اوراق خلاف جهت هم)، بالای صفر یعنی
# هم‌جهت شدن (که خودش یه سیگنال رژیمیه — معمولاً با تورم بالا مرتبطه).

def _rolling_stock_bond_correlation(
    df: pd.DataFrame,
    stock_col: str = "SP500",
    bond_col: str = "TLT",
    windows: tuple = (30, 90),
) -> pd.DataFrame:

    if stock_col not in df.columns or bond_col not in df.columns:
        return pd.DataFrame()

    temp = df[["Date", stock_col, bond_col]].dropna().copy()
    if temp.empty:
        return pd.DataFrame()

    temp["Date"] = pd.to_datetime(temp["Date"], errors="coerce")
    temp = temp.dropna(subset=["Date"]).sort_values("Date")
    temp = temp.drop_duplicates(subset="Date")

    if temp.empty:
        return pd.DataFrame()

    stock_ret = temp[stock_col].pct_change()
    bond_ret = temp[bond_col].pct_change()

    result = pd.DataFrame({"Date": temp["Date"].values})

    corr_columns = []
    for w in windows:
        col_name = f"corr_{w}d"
        result[col_name] = stock_ret.rolling(w).corr(bond_ret).values
        corr_columns.append(col_name)

    result = result.dropna(how="all", subset=corr_columns)

    return result


def render_stock_bond_correlation_chart(
    df: pd.DataFrame,
    stock_col: str = "SP500",
    bond_col: str = "TLT",
    stock_label: str = "SP500",
    bond_label: str = "TLT",
):

    corr_df = _rolling_stock_bond_correlation(df, stock_col, bond_col, windows=(30, 90))

    if corr_df.empty:
        st.info(f"داده‌ی کافی برای همبستگی {stock_label}/{bond_label} نیست.")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=corr_df["Date"],
            y=corr_df["corr_30d"],
            mode="lines",
            name="30d corr",
            line=dict(width=1.3, color="#e8983f"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=corr_df["Date"],
            y=corr_df["corr_90d"],
            mode="lines",
            name="90d corr",
            line=dict(width=2.2, color="#a78bfa"),
        )
    )

    fig.add_hline(
        y=0,
        line=dict(color="rgba(255,255,255,0.4)", dash="dash", width=1),
    )

    fig.update_layout(
        template="plotly_dark",
        title=f"Stock-Bond Correlation ({stock_label}/{bond_label}) · 30d and 90d (daily returns)",
        height=420,
        hovermode="x unified",
        yaxis=dict(title="Correlation", range=[-1, 1]),
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="top", y=-0.16, xanchor="center", x=0.5),
    )

    st.plotly_chart(fig, use_container_width=True)


# ==========================================================
# CONDITIONAL PLAYBOOK — Next-N-Session Outcomes by Regime State
# ==========================================================

FORWARD_HORIZON = 21  # جلسه‌ی معاملاتی

CURVE_STATE_ORDER = [
    "BullSteepener", "BearSteepener",
    "BullFlattener", "BearFlattener",
    "SteepenerTwist", "FlattenerTwist",
]

CURVE_STATE_LABELS = {
    "BullSteepener": "Bull Steepener",
    "BearSteepener": "Bear Steepener",
    "BullFlattener": "Bull Flattener",
    "BearFlattener": "Bear Flattener",
    "SteepenerTwist": "Steepener Twist",
    "FlattenerTwist": "Flattener Twist",
}


STOCK_BOND_CORR_WINDOW = 30


def _derive_curve_state_series(df: pd.DataFrame) -> pd.Series:
    """همیشه از ستون‌های flag (که خودمون توی updater.py/bond_plot.py می‌شناسیم
    و مطمئنیم پر می‌شن) مشتق می‌کنیم — نه از ستون CurveRegime که فرمت دقیقش
    برامون ناشناخته‌ست و ممکنه خالی یا فرمتش متفاوت باشه."""

    if "2s10s" not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype=object)

    state = pd.Series(np.nan, index=df.index, dtype=object)
    for flag_col in CURVE_STATE_ORDER:
        if flag_col in df.columns:
            match = df[flag_col] == df["2s10s"]
            state[match] = flag_col

    return state.ffill()


def _stock_bond_corr_state_series(df: pd.DataFrame, stock_col="SP500", bond_col="TLT", window=STOCK_BOND_CORR_WINDOW) -> pd.Series:

    state = pd.Series(np.nan, index=df.index, dtype=object)

    if stock_col not in df.columns or bond_col not in df.columns:
        return state

    stock_ret = pd.to_numeric(df[stock_col], errors="coerce").pct_change()
    bond_ret = pd.to_numeric(df[bond_col], errors="coerce").pct_change()
    corr = stock_ret.rolling(window).corr(bond_ret)

    state[corr > 0] = "POSITIVE"
    state[corr <= 0] = "NEGATIVE"

    return state


def _dimension_diagnostics(df: pd.DataFrame) -> list[str]:
    """اگه بعضی بُعدها هیچ داده‌ای ندن، دلیل محتمل رو برمی‌گردونه — تا به‌جای
    حذف بی‌صدا، بدونیم دقیقاً کدوم ستون مشکل داره."""

    notes = []

    if "2s10s" not in df.columns or not any(c in df.columns for c in CURVE_STATE_ORDER):
        notes.append("Curve regime: ستون‌های 2s10s/BullSteepener و مشابهشون توی دیتابیس نیستن.")

    if "TLT" not in df.columns:
        notes.append("Stock-bond corr: ستون TLT توی دیتابیس نیست.")
    elif df["TLT"].notna().sum() < STOCK_BOND_CORR_WINDOW:
        notes.append(f"Stock-bond corr: ستون TLT کمتر از {STOCK_BOND_CORR_WINDOW} مقدار معتبر داره.")

    if "NFCI" not in df.columns:
        notes.append("Financial conditions: ستون NFCI توی دیتابیس نیست.")

    return notes


def _stock_bond_corr_state_series(df: pd.DataFrame, stock_col="SP500", bond_col="TLT", window=90) -> pd.Series:
    """علامت همبستگی غلتان بین بازدهی روزانه‌ی سهام و اوراق — یه سری روزانه
    هم‌تراز با کل دیتابیس (نه فقط ردیف‌های بدون‌گپ)."""

    state = pd.Series(np.nan, index=df.index, dtype=object)

    if stock_col not in df.columns or bond_col not in df.columns:
        return state

    stock_ret = pd.to_numeric(df[stock_col], errors="coerce").pct_change()
    bond_ret = pd.to_numeric(df[bond_col], errors="coerce").pct_change()
    corr = stock_ret.rolling(window).corr(bond_ret)

    state[corr > 0] = "POSITIVE"
    state[corr <= 0] = "NEGATIVE"

    return state


def _nfci_state_series(df: pd.DataFrame) -> pd.Series:
    """علامت NFCI شیکاگو فد — منفی یعنی شرایط مالی «شل‌تر از میانگین
    تاریخی»، مثبت/صفر یعنی «سفت‌تر». چون NFCI هفتگیه، بین دو انتشار
    forward-fill می‌شه."""

    state = pd.Series(np.nan, index=df.index, dtype=object)

    if "NFCI" not in df.columns:
        return state

    nfci = pd.to_numeric(df["NFCI"], errors="coerce").ffill()
    state[nfci < 0] = "LOOSE"
    state[nfci >= 0] = "TIGHT"

    return state


def _forward_pct_return(series: pd.Series, horizon: int = FORWARD_HORIZON) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce")
    future = series.shift(-horizon)
    return (future / series - 1) * 100


def _forward_bps_change(series: pd.Series, horizon: int = FORWARD_HORIZON) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce")
    future = series.shift(-horizon)
    return (future - series) * 100


def _build_dimension_rows(dimension_label, state_series, state_order, state_labels, spx_fwd, gold_fwd, y10_fwd_bps):

    rows = []
    current_valid = state_series.dropna()
    current_state = current_valid.iloc[-1] if not current_valid.empty else None

    for state in state_order:
        mask = state_series == state
        n = int(mask.sum())
        if n == 0:
            continue

        spx_vals = spx_fwd[mask].dropna()
        gold_vals = gold_fwd[mask].dropna()
        y10_vals = y10_fwd_bps[mask].dropna()

        rows.append({
            "dimension": dimension_label,
            "state_label": state_labels.get(state, state),
            "obs": n,
            "spx_avg": spx_vals.mean() if not spx_vals.empty else np.nan,
            "spx_pos": (spx_vals > 0).mean() * 100 if not spx_vals.empty else np.nan,
            "gold_avg": gold_vals.mean() if not gold_vals.empty else np.nan,
            "y10_avg_bps": y10_vals.mean() if not y10_vals.empty else np.nan,
            "is_current": state == current_state,
        })

    return rows


def render_conditional_playbook_table(df: pd.DataFrame, horizon: int = FORWARD_HORIZON):

    if "SP500" not in df.columns:
        st.info("ستون SP500 برای این جدول لازمه و پیدا نشد.")
        return

    work = df.sort_values("Date").reset_index(drop=True)

    spx_fwd = _forward_pct_return(work["SP500"], horizon)
    gold_fwd = _forward_pct_return(work["GOLD"], horizon) if "GOLD" in work.columns else pd.Series(np.nan, index=work.index)
    y10_fwd_bps = _forward_bps_change(work["10Y"], horizon) if "10Y" in work.columns else pd.Series(np.nan, index=work.index)

    curve_state = _derive_curve_state_series(work)
    corr_state = _stock_bond_corr_state_series(work, window=STOCK_BOND_CORR_WINDOW)
    nfci_state = _nfci_state_series(work)

    rows = []
    rows += _build_dimension_rows("Curve regime", curve_state, CURVE_STATE_ORDER, CURVE_STATE_LABELS, spx_fwd, gold_fwd, y10_fwd_bps)
    rows += _build_dimension_rows(
        "Stock-bond corr", corr_state, ["NEGATIVE", "POSITIVE"],
        {"NEGATIVE": "NEGATIVE (hedge on)", "POSITIVE": "POSITIVE (no hedge)"},
        spx_fwd, gold_fwd, y10_fwd_bps,
    )
    rows += _build_dimension_rows(
        "Financial conditions (NFCI)", nfci_state, ["LOOSE", "TIGHT"],
        {"LOOSE": "LOOSE (<0)", "TIGHT": "TIGHT (≥0)"},
        spx_fwd, gold_fwd, y10_fwd_bps,
    )

    diagnostics = _dimension_diagnostics(work)
    if diagnostics and len(rows) < 10:
        st.caption("⚠️ " + " | ".join(diagnostics))

    if not rows:
        st.info("داده‌ی کافی برای این جدول نیست.")
        return

    valid_dates = work["Date"].dropna()
    years_span = (valid_dates.max() - valid_dates.min()).days / 365.25 if len(valid_dates) > 1 else 0

    def _fmt_pct(v): return "—" if pd.isna(v) else f"{v:+.2f}%"
    def _fmt_pos(v): return "—" if pd.isna(v) else f"{v:.0f}%"
    def _fmt_bps(v): return "—" if pd.isna(v) else f"{v:+.0f}bp"

    header_cells = ["dimension", "state", "obs", f"SPX +{horizon}d avg", "SPX %pos", f"Gold +{horizon}d avg", f"10Y +{horizon}d avg"]
    header_html = "".join(
        f"<th style='padding:8px 12px;border:1px solid rgba(255,255,255,0.09);"
        f"background:rgba(255,255,255,0.05);color:#e8e8e8;text-align:left;font-family:Consolas,monospace;font-size:12px;'>{h}</th>"
        for h in header_cells
    )

    rows_html = ""
    for row in rows:
        highlight = row["is_current"]
        bg = "rgba(46,196,182,0.14)" if highlight else "transparent"
        state_text = row["state_label"] + (" ◄ NOW" if highlight else "")

        def _cell(value, align="left", color="#d8d8d8"):
            return (
                f"<td style='padding:7px 12px;border:1px solid rgba(255,255,255,0.09);"
                f"background:{bg};color:{color};text-align:{align};font-family:Consolas,monospace;font-size:12px;'>{value}</td>"
            )

        spx_color = "#3fb968" if pd.notna(row["spx_avg"]) and row["spx_avg"] >= 0 else "#d9534f"
        gold_color = "#3fb968" if pd.notna(row["gold_avg"]) and row["gold_avg"] >= 0 else "#d9534f"
        y10_color = "#3fb968" if pd.notna(row["y10_avg_bps"]) and row["y10_avg_bps"] >= 0 else "#d9534f"

        rows_html += (
            "<tr>"
            + _cell(row["dimension"])
            + _cell(state_text, color="#2ec4b6" if highlight else "#d8d8d8")
            + _cell(row["obs"], align="right")
            + _cell(_fmt_pct(row["spx_avg"]), align="right", color=spx_color)
            + _cell(_fmt_pos(row["spx_pos"]), align="right")
            + _cell(_fmt_pct(row["gold_avg"]), align="right", color=gold_color)
            + _cell(_fmt_bps(row["y10_avg_bps"]), align="right", color=y10_color)
            + "</tr>"
        )

    table_html = f"""
    <div style="border:1px solid rgba(255,255,255,0.09);border-radius:10px;padding:14px 16px;background:rgba(255,255,255,0.02);">
        <div style="font-weight:800;font-size:14px;color:#f0f0f0;margin-bottom:10px;">
            CONDITIONAL PLAYBOOK · NEXT-{horizon}-SESSION OUTCOMES BY REGIME STATE (≈{years_span:.1f}y sample)
        </div>
        <table style="width:100%;border-collapse:collapse;">
            <tr>{header_html}</tr>
            {rows_html}
        </table>
        <div style="margin-top:8px;font-size:11px;color:#8f949e;">
            overlapping daily observations · highlighted rows = today's active states · history, not prophecy: regimes describe the playing field, not the play
        </div>
    </div>
    """

    st.markdown(table_html, unsafe_allow_html=True)


# ==========================================================
# MACRO × BOND REGIME — COLLAPSIBLE RESEARCH NOTES
# ==========================================================

def render_research_notes():

    research_html = f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <style>

            * {{
                box-sizing: border-box;
            }}

            html,
            body {{
                margin: 0;
                padding: 0;
                background: transparent;
            }}

            body {{
                font-family:
                    -apple-system,
                    BlinkMacSystemFont,
                    "Segoe UI",
                    Arial,
                    sans-serif;

                color: #cfcfcf;

                font-size: 13px;

                line-height: 1.8;
            }}

            .research-wrap {{
                width: 100%;
                padding: 4px 0 20px 0;
            }}

            .research-title {{
                font-size: 24px;
                font-weight: 800;
                color: #f2f2f2;
                margin: 0 0 14px 0;
            }}

            details.research-box {{
                border: 1px solid rgba(255,255,255,0.09);
                border-radius: 14px;
                background: rgba(255,255,255,0.025);
                margin-bottom: 10px;
                overflow: hidden;
            }}

            details.research-box > summary {{
                cursor: pointer;
                list-style: none;
                padding: 16px 18px;
                font-size: 14px;
                font-weight: 800;
                color: #f0f0f0;
                user-select: none;
                outline: none;
            }}

            details.research-box > summary::-webkit-details-marker {{
                display: none;
            }}

            details.research-box > summary::after {{
                content: "＋";
                float: right;
                color: #8f949e;
                font-size: 16px;
            }}

            details.research-box[open] > summary::after {{
                content: "−";
            }}

            details.research-box > summary:hover {{
                background: rgba(255,255,255,0.025);
            }}

            .research-content {{
                padding: 0 18px 22px 18px;
                color: #cfcfcf;
            }}

            .research-content p {{
                margin: 8px 0;
            }}

            .research-content h3 {{
                color: #f2f2f2;
                font-size: 17px;
                margin: 20px 0 8px 0;
                line-height: 1.4;
            }}

            .research-content h4 {{
                color: #e8e8e8;
                font-size: 14px;
                margin: 16px 0 5px 0;
            }}

            .research-content strong {{
                color: #f0f0f0;
            }}

            .research-content code {{
                background: rgba(255,255,255,0.06);
                padding: 2px 6px;
                border-radius: 5px;
                color: #e6e6e6;
                font-family: Consolas, monospace;
                font-size: 12px;
            }}

            .research-note {{
                border-left: 3px solid rgba(255,255,255,0.20);
                padding: 11px 14px;
                margin: 14px 0;
                background: rgba(255,255,255,0.018);
                border-radius: 0 8px 8px 0;
            }}

            .research-warning {{
                border-left: 3px solid #c9a24b;
                padding: 11px 14px;
                margin: 14px 0;
                background: rgba(201,162,75,0.07);
                border-radius: 0 8px 8px 0;
            }}

            .research-table-wrap {{
                overflow-x: auto;
                margin: 14px 0;
            }}

            .research-table {{
                width: 100%;
                border-collapse: collapse;
                min-width: 720px;
                font-size: 12px;
            }}

            .research-table th,
            .research-table td {{
                border: 1px solid rgba(255,255,255,0.09);
                padding: 9px 10px;
                text-align: left;
                vertical-align: middle;
            }}

            .research-table th {{
                background: rgba(255,255,255,0.05);
                color: #f0f0f0;
                font-weight: 800;
            }}

            .research-table td {{
                color: #d0d0d0;
            }}

            .asset-card {{
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                padding: 12px;
                margin: 9px 0;
                background: rgba(255,255,255,0.018);
            }}

            .asset-name {{
                font-weight: 800;
                color: #f2f2f2;
                margin-bottom: 4px;
            }}

            .source {{
                color: #9ea4ad;
                font-size: 12px;
                margin-top: 8px;
            }}

            .source a {{
                color: #b7c9ff;
                text-decoration: none;
            }}

            .source a:hover {{
                text-decoration: underline;
            }}

            .formula-box {{
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                padding: 12px 14px;
                background: rgba(255,255,255,0.018);
                margin: 12px 0;
                font-family: Consolas, monospace;
                color: #e1e1e1;
            }}

        </style>

    </head>

    <body>

        <div class="research-wrap">

            <div class="research-title">
                📚 Macro × Bond Regime — Research Notes
            </div>


            <!-- ================================================= -->
            <!-- 1 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    1️⃣ هدف و ساختار مدل
                </summary>

                <div class="research-content">

                    <p>
                    این داشبورد یک
                    <strong>Macro × Bond Regime Framework</strong>
                    است که برای قرار دادن بازارهای مالی در context اقتصادی
                    ساخته شده است.
                    </p>

                    <h3>سه لایه اصلی</h3>

                    <p>
                    <strong>1. Growth Momentum</strong><br>
                    آیا فعالیت اقتصادی در حال تقویت شدن است یا تضعیف شدن؟
                    </p>

                    <p>
                    <strong>2. Inflation Momentum</strong><br>
                    آیا فشارهای تورمی در حال افزایش هستند یا کاهش؟
                    </p>

                    <p>
                    <strong>3. Treasury Yield Curve</strong><br>
                    آیا منحنی 2Y–10Y در حال Bull/Bear Flattening یا
                    Bull/Bear Steepening است؟
                    </p>

                    <p>
                    سپس این سه لایه با هم ترکیب می‌شوند تا regime فعلی ساخته شود.
                    </p>

                    <div class="research-note">
                        <strong>نکته مهم:</strong>
                        افزایش 10Y Yield به تنهایی علت حرکت بازار را مشخص نمی‌کند.
                        افزایش 10Y می‌تواند ناشی از رشد قوی‌تر، تورم،
                        inflation expectations، term premium، عرضه Treasury
                        یا عوامل مالی باشد.
                    </div>

                    <p>
                    بنابراین هدف Matrix این نیست که فقط بگوید
                    «Bond بالا/پایین»، بلکه می‌خواهد پاسخ دهد:
                    </p>

                    <p>
                    <strong>
                    «Bond market در چه محیط اقتصادی قرار دارد و این محیط
                    معمولاً برای چه assetهایی مناسب‌تر است؟»
                    </strong>
                    </p>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 2 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    2️⃣ Growth چگونه تعریف می‌شود؟
                </summary>

                <div class="research-content">

                    <h3>GDP مثبت به معنی Growth مثبت نیست</h3>

                    <p>
                    در این مدل Growth به معنی ساده‌ی
                    <code>GDP &gt; 0</code> یا
                    <code>GDP &lt; 0</code>
                    نیست.
                    </p>

                    <p>
                    چیزی که برای بازار مهم‌تر است،
                    <strong>جهت و momentum فعالیت اقتصادی</strong>
                    است.
                    </p>

                    <p>
                    مثال:
                    </p>

                    <div class="formula-box">
                        +4% → +3% → +2%
                    </div>

                    <p>
                    GDP هنوز مثبت است ولی Growth Momentum در حال کاهش است.
                    بنابراین چنین محیطی می‌تواند
                    <strong>Growth ↓</strong>
                    تلقی شود.
                    </p>

                    <h3>متغیرهای مورد استفاده</h3>

                    <h4>OECD US Composite Leading Indicator</h4>

                    <p>
                    ستون:
                    <code>USALOLITOAASTSAM</code>
                    </p>

                    <p>
                    CLI برای تشخیص turning pointهای چرخه اقتصادی و
                    تغییر در momentum فعالیت اقتصادی طراحی شده است.
                    </p>

                    <h4>Chicago Fed National Activity Index — 3M MA</h4>

                    <p>
                    ستون:
                    <code>CFNAIMA3</code>
                    </p>

                    <p>
                    این شاخص برای بررسی وضعیت گسترده فعالیت اقتصادی آمریکا
                    استفاده می‌شود.
                    </p>

                    <h4>Real GDP</h4>

                    <p>
                    ستون:
                    <code>A191RO1Q156NBEA</code>
                    </p>

                    <p>
                    Real GDP برای تأیید وضعیت واقعی اقتصاد استفاده می‌شود.
                    </p>

                    <h3>Growth Score در این پروژه</h3>

                    <div class="research-table-wrap">

                        <table class="research-table">

                            <thead>
                                <tr>
                                    <th>Signal</th>
                                    <th>Weight</th>
                                </tr>
                            </thead>

                            <tbody>

                                <tr>
                                    <td>OECD CLI 3M</td>
                                    <td>+1 / −1</td>
                                </tr>

                                <tr>
                                    <td>OECD CLI 6M</td>
                                    <td>+1 / −1</td>
                                </tr>

                                <tr>
                                    <td>CFNAI MA3 3M</td>
                                    <td>+1 / −1</td>
                                </tr>

                                <tr>
                                    <td>Real GDP trend</td>
                                    <td>+1 / −1</td>
                                </tr>

                            </tbody>

                        </table>

                    </div>

                    <p>
                    اگر مجموع سیگنال‌ها مثبت باشد:
                    <strong>Growth ↑</strong>
                    </p>

                    <p>
                    اگر مجموع منفی باشد:
                    <strong>Growth ↓</strong>
                    </p>

                    <div class="research-warning">

                        این scoring rule یک
                        <strong>قانون مخصوص این پروژه</strong>
                        است.

                        OECD یا Federal Reserve چنین فرمول امتیازدهی خاصی را
                        به‌عنوان قانون رسمی معرفی نکرده‌اند.

                    </div>

                    <h3>NBER چیست؟</h3>

                    <p>
                    NBER recession را صرفاً با «دو فصل GDP منفی» تعریف نمی‌کند.
                    معیار آن یک کاهش قابل‌توجه و فراگیر در فعالیت اقتصادی است
                    که مجموعه‌ای از شاخص‌ها را در نظر می‌گیرد.
                    </p>

                    <p>
                    بنابراین NBER برای
                    <strong>historical classification</strong>
                    بسیار مفید است ولی برای live trading مناسب نیست،
                    چون official dating آن retrospective است.
                    </p>

                    <p class="source">
                        NBER:
                        <a
                            href="https://www.nber.org/research/business-cycle-dating"
                            target="_blank"
                        >
                            Business Cycle Dating
                        </a>
                    </p>

                    <p class="source">
                        OECD:
                        <a
                            href="https://www.oecd.org/en/data/indicators/composite-leading-indicator-cli.html"
                            target="_blank"
                        >
                            Composite Leading Indicator
                        </a>
                    </p>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 3 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    3️⃣ Inflation چگونه تعریف می‌شود؟
                </summary>

                <div class="research-content">

                    <h3>
                        Inflation Level با Inflation Momentum فرق دارد
                    </h3>

                    <p>
                    مثلاً اگر Core CPI برابر 3.5% باشد،
                    این به تنهایی نمی‌گوید Inflation ↑ است.
                    </p>

                    <p>
                    اگر:
                    </p>

                    <div class="formula-box">
                        5.0% → 4.3% → 3.5%
                    </div>

                    <p>
                    سطح تورم هنوز نسبتاً بالا است ولی
                    <strong>Inflation Momentum ↓</strong>
                    است.
                    </p>

                    <h3>متغیرهای مورد استفاده</h3>

                    <div class="asset-card">

                        <div class="asset-name">
                            Core CPI
                        </div>

                        <div>
                            <code>CPILFESL</code>
                        </div>

                        <div>
                            از level شاخص، نرخ YoY ساخته می‌شود.
                        </div>

                    </div>

                    <div class="asset-card">

                        <div class="asset-name">
                            Core PCE
                        </div>

                        <div>
                            <code>PCEPILFE</code>
                        </div>

                    </div>

                    <div class="asset-card">

                        <div class="asset-name">
                            10Y Breakeven Inflation
                        </div>

                        <div>
                            <code>T10YIE</code>
                        </div>

                    </div>

                    <div class="asset-card">

                        <div class="asset-name">
                            5Y5Y Forward Inflation Expectation
                        </div>

                        <div>
                            <code>T5YIFR</code>
                        </div>

                    </div>

                    <h3>چرا چند سنجه؟</h3>

                    <p>
                    چون realized inflation و inflation expectations الزاماً
                    هم‌زمان حرکت نمی‌کنند.
                    </p>

                    <p>
                    مثلاً ممکن است:
                    </p>

                    <div class="formula-box">
                        Actual Inflation ↓
                    </div>

                    <p>
                    ولی:
                    </p>

                    <div class="formula-box">
                        Inflation Expectations ↑
                    </div>

                    <p>
                    این وضعیت اطلاعات متفاوتی نسبت به زمانی دارد که هر دو
                    همزمان در حال کاهش باشند.
                    </p>

                    <div class="research-warning">
                        در نسخه فعلی، Inflation regime یک
                        <strong>momentum score</strong>
                        است، نه قضاوت درباره اینکه تورم در سطح «خوب» یا «بد» قرار دارد.
                    </div>

                    <p class="source">
                        Cieślak & Pflueger:
                        <a
                            href="https://www.nber.org/papers/w30982"
                            target="_blank"
                        >
                            Inflation and Asset Returns
                        </a>
                    </p>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 4 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    4️⃣ Yield Curve و چهار رژیم Bond
                </summary>

                <div class="research-content">

                    <h3>تعریف 2s10s</h3>

                    <div class="formula-box">
                        2s10s = 10Y Yield − 2Y Yield
                    </div>

                    <p>
                    اگر spread افزایش یابد:
                    <strong>Steepening</strong>
                    </p>

                    <p>
                    اگر spread کاهش یابد:
                    <strong>Flattening</strong>
                    </p>

                    <h3>چهار حالت کلاسیک</h3>

                    <div class="research-table-wrap">

                        <table class="research-table">

                            <thead>

                                <tr>
                                    <th>Regime</th>
                                    <th>2Y</th>
                                    <th>10Y</th>
                                    <th>2s10s</th>
                                </tr>

                            </thead>

                            <tbody>

                                <tr>
                                    <td><strong>Bull Steepening</strong></td>
                                    <td>↓↓</td>
                                    <td>↓</td>
                                    <td>↑</td>
                                </tr>

                                <tr>
                                    <td><strong>Bear Steepening</strong></td>
                                    <td>↑</td>
                                    <td>↑↑</td>
                                    <td>↑</td>
                                </tr>

                                <tr>
                                    <td><strong>Bull Flattening</strong></td>
                                    <td>↓</td>
                                    <td>↓↓</td>
                                    <td>↓</td>
                                </tr>

                                <tr>
                                    <td><strong>Bear Flattening</strong></td>
                                    <td>↑↑</td>
                                    <td>↑</td>
                                    <td>↓</td>
                                </tr>

                            </tbody>

                        </table>

                    </div>

                    <h3>Bull Steepening</h3>

                    <p>
                    هر دو yield کاهش می‌یابند ولی 2Y سریع‌تر پایین می‌آید.
                    اغلب با انتظار easing پولی یا deterioration در outlook
                    اقتصادی سازگار است.
                    </p>

                    <h3>Bear Steepening</h3>

                    <p>
                    هر دو yield افزایش می‌یابند ولی 10Y سریع‌تر افزایش می‌یابد.
                    علت آن می‌تواند growth، inflation expectations،
                    term premium، fiscal risk یا supply باشد.
                    </p>

                    <h3>Bull Flattening</h3>

                    <p>
                    هر دو yield کاهش می‌یابند ولی 10Y سریع‌تر کاهش می‌یابد.
                    این حالت می‌تواند با disinflation و long-duration rally
                    سازگار باشد.
                    </p>

                    <h3>Bear Flattening</h3>

                    <p>
                    هر دو yield افزایش می‌یابند ولی 2Y سریع‌تر بالا می‌رود.
                    این حالت اغلب با tightening پولی و inflation pressure
                    همراه است.
                    </p>

                    <div class="research-warning">

                        <strong>نکته کلیدی:</strong>

                        اسم Curve Regime به‌تنهایی علت حرکت را مشخص نمی‌کند.

                        برای مثال Bear Steepening می‌تواند growth-driven
                        یا inflation/term-premium-driven باشد.

                    </div>

                    <p class="source">
                        Litterman & Scheinkman:
                        <a
                            href="https://doi.org/10.3905/jfi.1991.692347"
                            target="_blank"
                        >
                            Common Factors Affecting Bond Returns
                        </a>
                    </p>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 5 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    5️⃣ چهار Macro Regime اصلی
                </summary>

                <div class="research-content">

                    <div class="research-table-wrap">

                        <table class="research-table">

                            <thead>

                                <tr>
                                    <th>Growth</th>
                                    <th>Inflation</th>
                                    <th>Macro Regime</th>
                                    <th>General Bias</th>
                                </tr>

                            </thead>

                            <tbody>

                                <tr>
                                    <td>↑</td>
                                    <td>↓</td>
                                    <td><strong>Goldilocks</strong></td>
                                    <td>Equities / Growth</td>
                                </tr>

                                <tr>
                                    <td>↑</td>
                                    <td>↑</td>
                                    <td><strong>Reflation / Overheating</strong></td>
                                    <td>Commodities / Cyclicals</td>
                                </tr>

                                <tr>
                                    <td>↓</td>
                                    <td>↓</td>
                                    <td><strong>Disinflation / Recession</strong></td>
                                    <td>Duration / Defensive</td>
                                </tr>

                                <tr>
                                    <td>↓</td>
                                    <td>↑</td>
                                    <td><strong>Stagflation</strong></td>
                                    <td>Gold / Inflation hedges</td>
                                </tr>

                            </tbody>

                        </table>

                    </div>

                    <h3>Goldilocks</h3>

                    <p>
                    Growth در حال بهبود است و Inflation Momentum کاهش می‌یابد.
                    </p>

                    <h3>Reflation</h3>

                    <p>
                    Growth و Inflation هر دو در حال افزایش‌اند.
                    این محیط معمولاً برای commodities و cyclical assets
                    مساعدتر است.
                    </p>

                    <h3>Disinflation / Recession</h3>

                    <p>
                    Growth تضعیف می‌شود و inflation نیز پایین می‌آید.
                    این محیط معمولاً به نفع duration و nominal Treasury است.
                    </p>

                    <h3>Stagflation</h3>

                    <p>
                    Growth ضعیف و Inflation قوی است.
                    این یکی از دشوارترین محیط‌ها برای portfolioهای سنتی
                    سهام + nominal bonds است.
                    </p>

                    <p class="source">
                        Baltussen et al.:
                        <a
                            href="https://www.tandfonline.com/doi/full/10.1080/0015198X.2023.2185066"
                            target="_blank"
                        >
                            Investing in Deflation, Inflation, and Stagflation Regimes
                        </a>
                    </p>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 6 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    6️⃣ چرا Matrix دقیقاً 16 خانه دارد؟
                </summary>

                <div class="research-content">

                    <p>
                    چهار Macro Regime داریم:
                    </p>

                    <div class="formula-box">
                        Growth ↑ / Inflation ↓<br>
                        Growth ↑ / Inflation ↑<br>
                        Growth ↓ / Inflation ↓<br>
                        Growth ↓ / Inflation ↑
                    </div>

                    <p>
                    و چهار Bond Curve Regime:
                    </p>

                    <div class="formula-box">
                        Bull Flattening<br>
                        Bull Steepening<br>
                        Bear Flattening<br>
                        Bear Steepening
                    </div>

                    <p>
                    بنابراین:
                    </p>

                    <div class="formula-box">
                        4 × 4 = 16 Regimes
                    </div>

                    <div class="research-warning">

                        Matrix فعلی یک
                        <strong>research-backed framework</strong>
                        است؛

                        نه یک مدل دانشگاهی واحد که دقیقاً همین 16 خانه
                        را با همین وزن‌ها منتشر کرده باشد.

                    </div>

                    <p>
                    ترکیب Macro Regime و Curve Regime در این پروژه یک
                    <strong>synthesis</strong>
                    از ادبیات macro، fixed income و asset allocation است.
                    </p>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 7 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    7️⃣ جدول راهنمای 16 رژیم
                </summary>

                <div class="research-content">

                    <p>
                    علائم زیر جهت کلی مورد انتظار را نشان می‌دهند،
                    نه probability قطعی:
                    </p>

                    <p>
                    <strong>+++</strong> بسیار مساعد،
                    <strong>++</strong> مساعد،
                    <strong>+</strong> کمی مساعد،
                    <strong>0</strong> mixed،
                    <strong>−</strong> کمی منفی،
                    <strong>−−</strong> منفی،
                    <strong>−−−</strong> بسیار منفی
                    </p>


                    <h3>
                        Growth ↑ / Inflation ↓ — Goldilocks
                    </h3>

                    <div class="research-table-wrap">

                        <table class="research-table">

                            <thead>
                                <tr>
                                    <th>Curve</th>
                                    <th>Stocks</th>
                                    <th>NASDAQ</th>
                                    <th>Gold</th>
                                    <th>Oil / Copper</th>
                                    <th>Long UST</th>
                                    <th>USD</th>
                                </tr>
                            </thead>

                            <tbody>

                                <tr>
                                    <td><strong>Bull Flattening</strong></td>
                                    <td>++</td>
                                    <td>+++</td>
                                    <td>+</td>
                                    <td>−−</td>
                                    <td>+++</td>
                                    <td>−−</td>
                                </tr>

                                <tr>
                                    <td><strong>Bull Steepening</strong></td>
                                    <td>++</td>
                                    <td>++</td>
                                    <td>+</td>
                                    <td>−</td>
                                    <td>++</td>
                                    <td>−−</td>
                                </tr>

                                <tr>
                                    <td><strong>Bear Flattening</strong></td>
                                    <td>++</td>
                                    <td>++</td>
                                    <td>0</td>
                                    <td>+</td>
                                    <td>−−</td>
                                    <td>0</td>
                                </tr>

                                <tr>
                                    <td><strong>Bear Steepening</strong></td>
                                    <td>+</td>
                                    <td>+</td>
                                    <td>−−</td>
                                    <td>+++</td>
                                    <td>−−−</td>
                                    <td>+</td>
                                </tr>

                            </tbody>

                        </table>

                    </div>


                    <h3>
                        Growth ↑ / Inflation ↑ — Reflation
                    </h3>

                    <div class="research-table-wrap">

                        <table class="research-table">

                            <thead>
                                <tr>
                                    <th>Curve</th>
                                    <th>Stocks</th>
                                    <th>NASDAQ</th>
                                    <th>Gold</th>
                                    <th>Oil / Copper</th>
                                    <th>Long UST</th>
                                    <th>USD</th>
                                </tr>
                            </thead>

                            <tbody>

                                <tr>
                                    <td><strong>Bull Flattening</strong></td>
                                    <td>+</td>
                                    <td>++</td>
                                    <td>+</td>
                                    <td>+</td>
                                    <td>++</td>
                                    <td>−−</td>
                                </tr>

                                <tr>
                                    <td><strong>Bull Steepening</strong></td>
                                    <td>++</td>
                                    <td>+</td>
                                    <td>0/+</td>
                                    <td>++</td>
                                    <td>+</td>
                                    <td>−−</td>
                                </tr>

                                <tr>
                                    <td><strong>Bear Flattening</strong></td>
                                    <td>++</td>
                                    <td>0/+</td>
                                    <td>0</td>
                                    <td>+++</td>
                                    <td>−−</td>
                                    <td>+</td>
                                </tr>

                                <tr>
                                    <td><strong>Bear Steepening</strong></td>
                                    <td>++</td>
                                    <td>0/+</td>
                                    <td>−−</td>
                                    <td>+++</td>
                                    <td>−−−</td>
                                    <td>+</td>
                                </tr>

                            </tbody>

                        </table>

                    </div>


                    <h3>
                        Growth ↓ / Inflation ↓ — Disinflation / Recession
                    </h3>

                    <div class="research-table-wrap">

                        <table class="research-table">

                            <thead>
                                <tr>
                                    <th>Curve</th>
                                    <th>Stocks</th>
                                    <th>NASDAQ</th>
                                    <th>Gold</th>
                                    <th>Oil / Copper</th>
                                    <th>Long UST</th>
                                    <th>USD</th>
                                </tr>
                            </thead>

                            <tbody>

                                <tr>
                                    <td><strong>Bull Flattening</strong></td>
                                    <td>−</td>
                                    <td>0</td>
                                    <td>++</td>
                                    <td>−−</td>
                                    <td>+++</td>
                                    <td>+</td>
                                </tr>

                                <tr>
                                    <td><strong>Bull Steepening</strong></td>
                                    <td>−−−</td>
                                    <td>−−</td>
                                    <td>++</td>
                                    <td>−−−</td>
                                    <td>+++</td>
                                    <td>++</td>
                                </tr>

                                <tr>
                                    <td><strong>Bear Flattening</strong></td>
                                    <td>−−</td>
                                    <td>−−</td>
                                    <td>+++</td>
                                    <td>−−</td>
                                    <td>−−</td>
                                    <td>+++</td>
                                </tr>

                                <tr>
                                    <td><strong>Bear Steepening</strong></td>
                                    <td>−−−</td>
                                    <td>−−−</td>
                                    <td>++</td>
                                    <td>−−−</td>
                                    <td>−−</td>
                                    <td>+++</td>
                                </tr>

                            </tbody>

                        </table>

                    </div>


                    <h3>
                        Growth ↓ / Inflation ↑ — Stagflation
                    </h3>

                    <div class="research-table-wrap">

                        <table class="research-table">

                            <thead>
                                <tr>
                                    <th>Curve</th>
                                    <th>Stocks</th>
                                    <th>NASDAQ</th>
                                    <th>Gold</th>
                                    <th>Oil / Copper</th>
                                    <th>Long UST</th>
                                    <th>USD</th>
                                </tr>
                            </thead>

                            <tbody>

                                <tr>
                                    <td><strong>Bull Flattening</strong></td>
                                    <td>−−</td>
                                    <td>−−</td>
                                    <td>+++</td>
                                    <td>0/+</td>
                                    <td>+</td>
                                    <td>++</td>
                                </tr>

                                <tr>
                                    <td><strong>Bull Steepening</strong></td>
                                    <td>−−</td>
                                    <td>−−</td>
                                    <td>+++</td>
                                    <td>+</td>
                                    <td>0/−</td>
                                    <td>++</td>
                                </tr>

                                <tr>
                                    <td><strong>Bear Flattening</strong></td>
                                    <td>−−−</td>
                                    <td>−−−</td>
                                    <td>+++</td>
                                    <td>+</td>
                                    <td>−−−</td>
                                    <td>+++</td>
                                </tr>

                                <tr>
                                    <td><strong>Bear Steepening</strong></td>
                                    <td>−−−</td>
                                    <td>−−−</td>
                                    <td>+++</td>
                                    <td>++</td>
                                    <td>−−−</td>
                                    <td>++</td>
                                </tr>

                            </tbody>

                        </table>

                    </div>

                    <div class="research-warning">

                        این جدول یک
                        <strong>directional framework</strong>
                        است.

                        علائم +/− به معنی probability آماری مشخص نیستند.

                    </div>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 8 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    8️⃣ TLT / IEF / TIP / HYG / LQD
                </summary>

                <div class="research-content">

                    <div class="asset-card">

                        <div class="asset-name">
                            TLT
                        </div>

                        <div>
                            iShares 20+ Year Treasury Bond ETF
                        </div>

                        <div>
                            Proxy برای long-duration Treasury.
                            نسبت به تغییرات long-end yield حساسیت زیادی دارد.
                        </div>

                    </div>


                    <div class="asset-card">

                        <div class="asset-name">
                            IEF
                        </div>

                        <div>
                            iShares 7–10 Year Treasury Bond ETF
                        </div>

                        <div>
                            Proxy برای intermediate-duration Treasury.
                        </div>

                    </div>


                    <div class="asset-card">

                        <div class="asset-name">
                            TIP
                        </div>

                        <div>
                            iShares TIPS Bond ETF
                        </div>

                        <div>
                            Proxy برای inflation-linked Treasury.
                        </div>

                    </div>


                    <div class="asset-card">

                        <div class="asset-name">
                            LQD
                        </div>

                        <div>
                            iShares iBoxx Investment Grade Corporate Bond ETF
                        </div>

                        <div>
                            Proxy برای Investment Grade credit.
                        </div>

                    </div>


                    <div class="asset-card">

                        <div class="asset-name">
                            HYG
                        </div>

                        <div>
                            iShares iBoxx High Yield Corporate Bond ETF
                        </div>

                        <div>
                            Proxy برای High Yield / lower-rated corporate credit.
                        </div>

                    </div>


                    <h3>
                        چرا این پنج ETF مهم‌اند؟
                    </h3>

                    <p>
                    اکنون فقط Treasury Yield نداریم.

                    می‌توانیم همزمان رفتار:
                    </p>

                    <div class="formula-box">
                        Nominal Treasury<br>
                        Inflation-linked Treasury<br>
                        Investment Grade Credit<br>
                        High Yield Credit
                    </div>

                    <p>
                    را بررسی کنیم.
                    </p>


                    <h3>
                        روابط مهم
                    </h3>

                    <p>
                    <code>TLT / IEF</code>
                    → relative duration
                    </p>

                    <p>
                    <code>TIP / TLT</code>
                    → relative inflation protection
                    </p>

                    <p>
                    <code>HYG / IEF</code>
                    → credit / risk appetite proxy
                    </p>

                    <p>
                    <code>LQD / IEF</code>
                    → Investment Grade credit conditions
                    </p>


                    <div class="research-note">

                        قیمت ETF فقط تابع Treasury yield نیست.

                        مخصوصاً HYG و LQD به credit spread نیز حساس هستند.

                    </div>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 9 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    9️⃣ چرا Treasury همیشه Safe Haven نیست؟
                </summary>

                <div class="research-content">

                    <p>
                    این یکی از مهم‌ترین نکات مدل است.
                    </p>

                    <h3>
                        Recession + Falling Inflation
                    </h3>

                    <p>
                    اگر:
                    <code>Growth ↓ + Inflation ↓</code>
                    </p>

                    <p>
                    فشار downward روی growth و inflation می‌تواند
                    باعث کاهش expected future short rates شود.
                    در این محیط Long Treasury معمولاً hedge بهتری است.
                    </p>

                    <h3>
                        Recession + Rising Inflation
                    </h3>

                    <p>
                    اگر:
                    <code>Growth ↓ + Inflation ↑</code>
                    </p>

                    <p>
                    ضعف اقتصاد لزوماً باعث rally اوراق نمی‌شود،
                    چون inflation/rate risk همچنان می‌تواند yield را بالا نگه دارد.
                    </p>

                    <div class="research-warning">

                        بنابراین:
                        <strong>Recession = Long Bonds ↑</strong>
                        یک قانون همیشگی نیست.

                        باید inflation regime نیز مشخص شود.

                    </div>

                    <p class="source">
                        Campbell, Sunderam & Viceira:
                        <a
                            href="https://www.nber.org/papers/w14701"
                            target="_blank"
                        >
                            Inflation Bets or Deflation Hedges?
                        </a>
                    </p>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 10 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    🔟 Term Premium چیست و چرا مهم است؟
                </summary>

                <div class="research-content">

                    <p>
                    یک تقریب مفهومی مهم برای 10Y Yield:
                    </p>

                    <div class="formula-box">
                        10Y Yield ≈ Expected Future Short Rates + Term Premium
                    </div>

                    <p>
                    بنابراین اگر 10Y بالا برود، لزوماً به این معنی نیست
                    که بازار انتظار دارد Fed نرخ policy را به همان اندازه بالا ببرد.
                    </p>

                    <h3>مثال</h3>

                    <div class="formula-box">
                        Fed expectations → تقریباً ثابت<br>
                        Term Premium → ↑↑
                    </div>

                    <p>
                    نتیجه:
                    <code>10Y Yield ↑</code>
                    </p>

                    <p>
                    ولی علت اصلی حرکت long-end الزاماً monetary tightening نیست.
                    </p>

                    <h3>
                        متغیر موجود در دیتابیس
                    </h3>

                    <p>
                    <code>THREEFYTP10</code>
                    </p>

                    <p>
                    این متغیر برای تشخیص اینکه Bear Steepening
                    ناشی از term premium است یا نه، مفید است.
                    </p>

                    <div class="research-note">
                        برای نسخه حرفه‌ای‌تر مدل باید همزمان
                        2Y، 10Y، real yield، inflation expectations
                        و term premium بررسی شوند.
                    </div>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 11 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    1️⃣1️⃣ Curve Regime در کنار Rate Driver
                </summary>

                <div class="research-content">

                    <p>
                    این بخش یکی از مهم‌ترین extensionهای آینده‌ی Matrix است.
                    </p>

                    <h3>
                        Bear Steepening — Growth Driven
                    </h3>

                    <p>
                    اگر:
                    </p>

                    <div class="formula-box">
                        Growth ↑<br>
                        Inflation ↑
                    </div>

                    <p>
                    و 10Y در واکنش به growth/reflation بالا برود،
                    bias می‌تواند به نفع:
                    </p>

                    <p>
                    <strong>
                        Oil / Copper / Cyclicals
                    </strong>
                    </p>

                    <h3>
                        Bear Steepening — Term Premium / Fiscal Driven
                    </h3>

                    <p>
                    اگر:
                    </p>

                    <div class="formula-box">
                        Growth ↓<br>
                        Term Premium ↑↑
                    </div>

                    <p>
                    همان Bear Steepening می‌تواند معنای کاملاً متفاوتی داشته باشد:
                    </p>

                    <p>
                    <strong>
                    Long Bonds ضعیف‌تر، USD قوی‌تر و risk assets تحت فشار
                    </strong>
                    </p>

                    <div class="research-warning">
                        بنابراین در نسخه حرفه‌ای‌تر:
                        <strong>
                        Curve Regime + Rate Driver
                        </strong>
                        باید با هم دیده شوند.
                    </div>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 12 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    1️⃣2️⃣ Limitations — محدودیت‌های مدل
                </summary>

                <div class="research-content">

                    <h3>
                        1. Correlation ≠ Causation
                    </h3>

                    <p>
                    اگر Gold در یک regime تاریخی بهتر عمل کرده باشد،
                    به این معنی نیست که آن regime علت افزایش Gold بوده است.
                    </p>

                    <h3>
                        2. Regimeها مرز دقیق ندارند
                    </h3>

                    <p>
                    اقتصاد ممکن است در یک transition بین دو regime قرار گرفته باشد.
                    </p>

                    <h3>
                        3. Market از Data جلوتر است
                    </h3>

                    <p>
                    ممکن است بازار recession را ماه‌ها قبل از اینکه
                    داده‌های رسمی آن را نشان دهند price کرده باشد.
                    </p>

                    <h3>
                        4. Asset-specific shocks
                    </h3>

                    <p>
                    WTI می‌تواند با supply shock حرکت کند.
                    Gold می‌تواند با geopolitical risk حرکت کند.
                    USD می‌تواند در funding stress جدا از Growth حرکت کند.
                    </p>

                    <h3>
                        5. Matrix فعلی هنوز predictive model نیست
                    </h3>

                    <p>
                    خروجی فعلی باید بیشتر به‌عنوان:
                    </p>

                    <p>
                    <strong>
                    Regime Filter / Context
                    </strong>
                    </p>

                    <p>
                    استفاده شود، نه:
                    </p>

                    <p>
                    <strong>
                    Standalone Buy / Sell Signal
                    </strong>
                    </p>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 13 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    1️⃣3️⃣ مرحله بعدی: Historical Backtest
                </summary>

                <div class="research-content">

                    <p>
                    مرحله بعدی پروژه باید Matrix نظری را با
                    historical data دیتابیس آزمایش کند.
                    </p>

                    <h3>
                        Metrics
                    </h3>

                    <div class="research-table-wrap">

                        <table class="research-table">

                            <thead>

                                <tr>
                                    <th>Metric</th>
                                    <th>Meaning</th>
                                </tr>

                            </thead>

                            <tbody>

                                <tr>
                                    <td><strong>Average Return</strong></td>
                                    <td>میانگین بازده در regime</td>
                                </tr>

                                <tr>
                                    <td><strong>Median Return</strong></td>
                                    <td>بازده میانه؛ مقاوم‌تر در برابر outlier</td>
                                </tr>

                                <tr>
                                    <td><strong>Win Rate</strong></td>
                                    <td>درصد دوره‌های مثبت</td>
                                </tr>

                                <tr>
                                    <td><strong>Volatility</strong></td>
                                    <td>ریسک / نوسان بازده</td>
                                </tr>

                                <tr>
                                    <td><strong>Maximum Drawdown</strong></td>
                                    <td>بدترین افت تجمعی</td>
                                </tr>

                                <tr>
                                    <td><strong>Number of Observations</strong></td>
                                    <td>تعداد نمونه‌ها</td>
                                </tr>

                            </tbody>

                        </table>

                    </div>

                    <h3>
                        Asset Universe
                    </h3>

                    <div class="formula-box">
                        SP500<br>
                        NASDAQ<br>
                        GOLD<br>
                        WTI<br>
                        XCUUSD<br>
                        DXY<br>
                        TLT<br>
                        IEF<br>
                        TIP<br>
                        HYG<br>
                        LQD
                    </div>

                    <div class="research-warning">

                        این مرحله بسیار مهم است، چون مشخص خواهد کرد
                        کدام روابط Matrix واقعاً پشتوانه تاریخی قوی دارند
                        و کدام‌ها صرفاً منطق اقتصادی هستند.

                    </div>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 14 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    1️⃣4️⃣ مقالات و منابع اصلی
                </summary>

                <div class="research-content">

                    <h3>
                        1. Litterman & Scheinkman — 1991
                    </h3>

                    <p>
                    <strong>
                    Common Factors Affecting Bond Returns
                    </strong><br>

                    Robert B. Litterman & José Scheinkman<br>

                    The Journal of Fixed Income
                    </p>

                    <p class="source">
                        <a
                            href="https://doi.org/10.3905/jfi.1991.692347"
                            target="_blank"
                        >
                            Article / DOI
                        </a>
                    </p>


                    <h3>
                        2. Cochrane & Piazzesi — 2005
                    </h3>

                    <p>
                    <strong>Bond Risk Premia</strong><br>

                    John H. Cochrane & Monika Piazzesi<br>

                    American Economic Review
                    </p>

                    <p class="source">
                        <a
                            href="https://www.aeaweb.org/articles?id=10.1257/0002828053828581"
                            target="_blank"
                        >
                            American Economic Association
                        </a>
                    </p>


                    <h3>
                        3. Campbell, Sunderam & Viceira
                    </h3>

                    <p>
                    <strong>
                    Inflation Bets or Deflation Hedges?
                    The Changing Risks of Nominal Bonds
                    </strong>
                    </p>

                    <p>
                    John Y. Campbell, Adi Sunderam & Luis M. Viceira
                    </p>

                    <p class="source">
                        <a
                            href="https://www.nber.org/papers/w14701"
                            target="_blank"
                        >
                            NBER Working Paper
                        </a>
                    </p>


                    <h3>
                        4. Cieślak & Pflueger — 2023
                    </h3>

                    <p>
                    <strong>Inflation and Asset Returns</strong><br>

                    Anna Cieślak & Carolin Pflueger<br>

                    Annual Review of Financial Economics
                    </p>

                    <p class="source">
                        <a
                            href="https://doi.org/10.1146/annurev-financial-110921-104726"
                            target="_blank"
                        >
                            Annual Review
                        </a>
                    </p>

                    <p class="source">
                        <a
                            href="https://www.nber.org/papers/w30982"
                            target="_blank"
                        >
                            NBER Working Paper 30982
                        </a>
                    </p>


                    <h3>
                        5. Baltussen et al. — 2023
                    </h3>

                    <p>
                    <strong>
                    Investing in Deflation, Inflation, and Stagflation Regimes
                    </strong><br>

                    Guido Baltussen, Laurens Swinkels,
                    Bart van Vliet & Pim van Vliet<br>

                    Financial Analysts Journal
                    </p>

                    <p class="source">
                        <a
                            href="https://www.tandfonline.com/doi/full/10.1080/0015198X.2023.2185066"
                            target="_blank"
                        >
                            Full Article
                        </a>
                    </p>


                    <h3>
                        6. Molenaar et al. — 2024
                    </h3>

                    <p>
                    <strong>
                    Empirical Evidence on the Stock–Bond Correlation
                    </strong><br>

                    Roderick Molenaar, Edouard Sénéchal,
                    Laurens Swinkels & Zhenping Wang<br>

                    Financial Analysts Journal
                    </p>

                    <p class="source">
                        <a
                            href="https://www.tandfonline.com/doi/full/10.1080/0015198X.2024.2317333"
                            target="_blank"
                        >
                            Full Article
                        </a>
                    </p>


                    <h3>
                        7. OECD
                    </h3>

                    <p>
                    <strong>
                    Composite Leading Indicator
                    </strong>
                    </p>

                    <p class="source">
                        <a
                            href="https://www.oecd.org/en/data/indicators/composite-leading-indicator-cli.html"
                            target="_blank"
                        >
                            OECD CLI
                        </a>
                    </p>


                    <h3>
                        8. NBER
                    </h3>

                    <p>
                    <strong>
                    Business Cycle Dating
                    </strong>
                    </p>

                    <p class="source">
                        <a
                            href="https://www.nber.org/research/business-cycle-dating"
                            target="_blank"
                        >
                            NBER
                        </a>
                    </p>

                </div>

            </details>


            <!-- ================================================= -->
            <!-- 15 -->
            <!-- ================================================= -->

            <details class="research-box">

                <summary>
                    1️⃣5️⃣ چطور رژیم فعلی داشبورد را بخوانم؟
                </summary>

                <div class="research-content">

                    <h3>
                        مرحله اول — Growth
                    </h3>

                    <p>
                    <strong>Growth ↑</strong>
                    یعنی مجموعه signalهای مورد استفاده در مدل،
                    momentum نسبتاً قوی‌تری را نشان می‌دهند.
                    </p>

                    <p>
                    <strong>Growth ↓</strong>
                    یعنی momentum فعالیت اقتصادی تضعیف شده است.
                    </p>

                    <h3>
                        مرحله دوم — Inflation
                    </h3>

                    <p>
                    <strong>Inflation ↑</strong>
                    یعنی inflation momentum / expectations
                    در جهت صعودی هستند.
                    </p>

                    <p>
                    <strong>Inflation ↓</strong>
                    یعنی inflation momentum در جهت نزولی است.
                    </p>

                    <h3>
                        مرحله سوم — Curve
                    </h3>

                    <div class="formula-box">
                        Bull Flattening<br>
                        Bull Steepening<br>
                        Bear Flattening<br>
                        Bear Steepening
                    </div>

                    <h3>
                        در نهایت هر سه را با هم بخوان
                    </h3>

                    <p>
                    مثال:
                    </p>

                    <div class="formula-box">
                        Growth ↓<br>
                        Inflation ↓<br>
                        Bull Steepening
                    </div>

                    <p>
                    این ترکیب با محیط
                    <strong>
                    Disinflation / Recession + monetary easing expectations
                    </strong>
                    سازگار است.
                    </p>

                    <p>
                    بنابراین از دید framework می‌توان انتظار داشت
                    duration و defensive assets اهمیت بیشتری پیدا کنند.
                    </p>

                    <div class="research-warning">

                        اما برای اینکه این expectation را به یک
                        <strong>trading signal</strong>
                        تبدیل کنیم،
                        باید historical backtest آن را انجام دهیم.

                    </div>

                </div>

            </details>

        </div>

    </body>

    </html>
    """

    components.html(
        research_html,
        height=1200,
        scrolling=True
    )

# ==========================================================
# SHOW
# ==========================================================

def show():

    inject_global_style()

    # ======================================================
    # GLOBAL CSS
    # ======================================================

    st.markdown(
        f"""
        <style>

        .stat-card{{
            border:
                1px solid
                rgba(255,255,255,0.09);

            background:
                rgba(255,255,255,0.025);

            border-radius:14px;

            padding:16px 18px;

            transition:
                border-color .25s ease,
                transform .25s ease;
        }}

        .stat-card:hover{{
            border-color:{ACCENT};

            transform:
                translateY(-3px);
        }}

        .stat-label{{
            font-size:13px;

            color:#8a8f98;

            margin-bottom:6px;
        }}

        .stat-value{{
            font-size:28px;

            font-weight:800;

            color:#f2f2f2;
        }}

        </style>
        """,
        unsafe_allow_html=True
    )


    # ======================================================
    # TITLE
    # ======================================================

    st.title("🌍 Global Market Dashboard")
    st.divider()

    # ======================================================
    # LOAD DATABASE
    # ======================================================

    if os.path.exists(DB_PATH):

        try:

            df = pd.read_csv(
                DB_PATH
            )

            df = _prepare_df(
                df
            )

        except Exception as e:

            st.error(
                f"Database read error: {e}"
            )

            df = pd.DataFrame()

    else:

        df = pd.DataFrame()

        st.warning(
            f"فایل دیتابیس پیدا نشد: {DB_PATH}"
        )


    # ======================================================
    # DATABASE INFORMATION
    # ======================================================

    if not df.empty:

        last_date = (
            df["Date"]
            .max()
            .strftime("%Y-%m-%d")
        )

        rows = len(df)

        last_index = df.index[-1]

        update_time = time.strftime(
            "%Y-%m-%d %H:%M",
            time.localtime(
                os.path.getmtime(
                    DB_PATH
                )
            )
        )

    else:

        last_date = "-"
        rows = "-"
        last_index = "-"
        update_time = "-"


    col1, col2, col3, col4 = st.columns(4)


    col1.markdown(
        _stat_card(
            "Last Data",
            last_date
        ),
        unsafe_allow_html=True
    )

    col2.markdown(
        _stat_card(
            "Rows",
            f"{rows:,}"
            if isinstance(
                rows,
                int
            )
            else rows
        ),
        unsafe_allow_html=True
    )

    col3.markdown(
        _stat_card(
            "Last Update",
            update_time
        ),
        unsafe_allow_html=True
    )

    col4.markdown(
        _stat_card(
            "Last Index",
            last_index
        ),
        unsafe_allow_html=True
    )


    st.write("")

    st.divider()


    # ======================================================
    # MACRO REGIME
    # ======================================================

    if not df.empty:

        try:
            growth_regime = (
                detect_growth_regime(
                    df
                )
            )
            inflation_regime = (
                detect_inflation_regime(
                    df
                )
            )
            curve_regime = (
                detect_current_curve_regime(
                    df
                )
            )


            # ------------------------------------------------
            # CURRENT REGIME HEADER
            # ------------------------------------------------

            st.subheader(
                "💵 Macro × Bond Regime Matrix"
            )
            st.caption(
                "Growth = momentum of leading/current activity; "
                "Inflation = inflation-rate momentum; "
                "Curve = 20-day 2Y/10Y move."
            )


            # ------------------------------------------------
            # CURRENT REGIME CARDS
            # ------------------------------------------------

            c1, c2, c3 = st.columns(3)

            c1.markdown(
                _stat_card(
                    "Growth Regime",
                    growth_regime
                ),
                unsafe_allow_html=True
            )

            c2.markdown(
                _stat_card(
                    "Inflation Regime",
                    inflation_regime
                ),
                unsafe_allow_html=True
            )

            c3.markdown(
                _stat_card(
                    "Bond Curve",
                    curve_regime
                ),
                unsafe_allow_html=True
            )

            st.write("")


            # ------------------------------------------------
            # MATRIX
            # ------------------------------------------------

            if (
                growth_regime
                in [
                    "Growth ↑",
                    "Growth ↓"
                ]
                and
                inflation_regime
                in [
                    "Inflation ↑",
                    "Inflation ↓"
                ]
                and
                curve_regime
                in [
                    "Bull Flattening",
                    "Bull Steepening",
                    "Bear Flattening",
                    "Bear Steepening"
                ]
            ):
                st.write("")

                render_score_breakdown(df, df["Date"].max())

                st.write("")

                render_regime_matrix( growth_regime, inflation_regime, curve_regime )
                # ------------------------------------------------
                # RESEARCH NOTES
                # ------------------------------------------------
                render_research_notes()


            else:

                st.warning(
                    "Current conditions do not map "
                    "cleanly to one of the four "
                    "classical curve regimes."
                )
                render_research_notes()

        except Exception as e:

            st.error(
                f"Regime Matrix Error: {e}"
            )


    # ======================================================
    # SEASONALITY
    # ======================================================

    if not df.empty:

        st.divider()

        st.subheader(
            "📅 Seasonality — میانگین بازدهی ماهانه (۱۵ سال اخیر)"
        )

        st.caption(
            "برای هر ماه تقویمی، میانگین بازدهی همون ماه طی ۱۵ سال "
            "اخیر محاسبه شده. ماه جاری با رنگ آبی مشخصه."
        )

        for column, label in SEASONALITY_ASSETS:
            render_seasonality_chart(df, column, label, years=15)

        st.divider()

        st.subheader("🔗 Stock-Bond Correlation")

        st.caption(
            "همبستگی غلتان بین بازدهی روزانه‌ی S&P 500 و TLT (اوراق ۲۰+ ساله)، "
            "روی دو پنجره‌ی ۳۰ و ۹۰ روزه. زیر صفر یعنی رفتار سنتی hedge "
            "(سهام و اوراق خلاف جهت هم)؛ بالای صفر یعنی هم‌جهت شدن‌شون."
        )

        render_stock_bond_correlation_chart(df)

    if not df.empty:
        st.divider()
        st.subheader("📋 Conditional Playbook")
        render_conditional_playbook_table(df)

    # ======================================================
    # UPDATE DATABASE
    # ======================================================

    st.divider()

    st.subheader(
        "Database"
    )


    if st.button(
        "🔄 Update Database",
        use_container_width=True
    ):

        st.info(
            "Updating database..."
        )

        log_box = st.empty()

        logs = ""


        try:

            process = subprocess.Popen(
                [
                    sys.executable,
                    UPDATER_PATH
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:

                logs += line

                log_box.code(
                    logs
                )

            process.wait()


            if process.returncode == 0:

                st.success(
                    "Database Updated Successfully ✅"
                )

                time.sleep(2)

                log_box.empty()

                st.rerun()

            else:

                st.error(
                    "Database Update Failed ❌"
                )

                time.sleep(2)

                log_box.empty()

        except Exception as e:

            st.error(
                f"Update process error: {e}"
            )

            log_box.empty()


# ==========================================================
# OPTIONAL DIRECT RUN
# ==========================================================

if __name__ == "__main__":
    show()