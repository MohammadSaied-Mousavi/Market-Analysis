"""
==========================================================================
 Summary — نمای کلی بازار جهانی
==========================================================================
فرض مهم: چون فقط فایل خیلی اولیه‌ی summary.py (یه stub خالی) رو توی
سابقه دارم، این فایل رو کامل از نو ساختم. اگه نسخه‌ی واقعی‌ای که الان
داری چیز دیگه‌ای هم توش داشته، بگو تا با هم ادغامش کنیم.
"""

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from constants import ROOT_DIR
from theme import inject_global_style, ACCENT

DB_PATH = os.path.join(ROOT_DIR, "database", "macro_database.csv")

SECTOR_COLUMNS = {
    "RSP": "هم‌وزن",
    "XLK": "فناوری",
    "XLF": "مالی",
    "XLV": "بهداشت‌ودرمان",
    "XLE": "انرژی",
    "XLY": "مصرفی اختیاری",
    "XLP": "مصرفی اساسی",
    "XLB": "مواد اولیه",
    "XLU": "خدمات عمومی",
    "XLRE": "املاک",
    "XLC": "ارتباطات",
    "GDX": "طلا (معادن)",
}


@st.cache_data(show_spinner=False)
def load_columns(path: str, mtime: float, cols: tuple) -> pd.DataFrame:
    available = pd.read_csv(path, nrows=0).columns
    use = ["Date"] + [c for c in cols if c in available]
    df = pd.read_csv(path, usecols=use)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    for c in use[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _line_chart_last_n_days(df: pd.DataFrame, col: str, n_days: int, title: str, color: str = ACCENT):
    if col not in df.columns:
        st.warning(f"ستون `{col}` توی دیتابیس نیست.")
        return
    series = df[col].dropna().tail(n_days)
    if series.empty:
        st.warning(f"داده‌ای برای `{col}` موجود نیست.")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series.values, name=col, line=dict(color=color, width=1.6)))
    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"summary_{col}_{n_days}")


def show() -> None:

    inject_global_style()

    st.markdown("# 📋 Summary")
    st.caption("نمای کلی بازار جهانی — read-only")

    if not os.path.isfile(DB_PATH):
        st.error(f"دیتابیس پیدا نشد:\n`{DB_PATH}`")
        return

    # ==================================================================
    # ۱) IMP/REAL_vol — ۳۰ روز اخیر
    # ==================================================================
    st.divider()
    st.markdown("### نسبت نوسان ضمنی به واقعی (Implied / Realized Vol)")
    vol_df = load_columns(DB_PATH, os.path.getmtime(DB_PATH), ("IMP/REAL_vol",))
    _line_chart_last_n_days(vol_df, "IMP/REAL_vol", 30, "IMP/REAL Vol — 30 روز اخیر")
    st.caption(
        "بالای ۱ یعنی بازار انتظار نوسان بیشتری از آینده داره تا چیزی که واقعاً اخیراً اتفاق افتاده "
        "(vol پریمیوم/ترس)؛ زیر ۱ یعنی برعکس."
    )

    # ==================================================================
    # ۲) رشد/کاهش سکتورها — با لوک‌بک قابل‌تنظیم
    # ==================================================================
    st.divider()
    st.markdown("### رشد/کاهش شاخص‌های بخشی")

    lookback = st.number_input("لوک‌بک (روز معاملاتی)", min_value=1, max_value=500, value=20, step=1)

    sector_df = load_columns(DB_PATH, os.path.getmtime(DB_PATH), tuple(SECTOR_COLUMNS.keys()))
    available_sectors = [c for c in SECTOR_COLUMNS if c in sector_df.columns]

    if not available_sectors:
        st.warning("هیچ‌کدوم از ستون‌های شاخص بخشی توی دیتابیس نیستن.")
    else:
        clean = sector_df[available_sectors].dropna(how="all")
        if len(clean) < lookback + 1:
            st.warning(f"فقط {len(clean)} ردیف داده هست، برای لوک‌بک {lookback} روزه کافی نیست.")
        else:
            end_prices = clean.iloc[-1]
            base_prices = clean.iloc[-(lookback + 1)]
            ret = ((end_prices / base_prices - 1) * 100).dropna().sort_values(ascending=False)

            labels = [f"{t} ({SECTOR_COLUMNS[t]})" for t in ret.index]
            colors = ["#4caf50" if v >= 0 else "#d9534f" for v in ret.values]

            fig = go.Figure(go.Bar(
                x=ret.values, y=labels, orientation="h",
                marker_color=colors,
                text=[f"{v:+.1f}%" for v in ret.values], textposition="outside",
            ))
            fig.update_layout(
                title=f"بازدهی {lookback} روز اخیر ({clean.index[-(lookback+1)].date()} → {clean.index[-1].date()})",
                template="plotly_dark",
                height=420,
                margin=dict(l=10, r=60, t=40, b=10),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig, use_container_width=True, key=f"summary_sector_{lookback}")

    # ==================================================================
    # ۳) SKEW — ۳۰ روز اخیر
    # ==================================================================
    st.divider()
    st.markdown("### شاخص SKEW (ریسک دنباله‌ی چپ)")
    skew_df = load_columns(DB_PATH, os.path.getmtime(DB_PATH), ("SKEW",))
    _line_chart_last_n_days(skew_df, "SKEW", 30, "SKEW — 30 روز اخیر", color="#d9534f")
    st.caption(
        "SKEW بالا (معمولاً بالای ۱۴۰-۱۵۰) یعنی بازار قیمت ریسک بیشتری برای یه افت شدید و ناگهانی "
        "(tail risk) گذاشته، حتی اگه VIX پایین/آروم باشه."
    )

    # ==================================================================
    # ۴) ساختار تایم‌اسپرد VIX (Term Structure)
    # ==================================================================
    st.divider()
    st.markdown("### ساختار تایم‌اسپرد VIX")

    TERM_COLS = {
        "VIX": "VIX (لحظه‌ای)",
        "vx1!": "VX1 (فیوچرز ماه اول)",
        "vx2!": "VX2 (فیوچرز ماه دوم)",
        "vix3m!": "VIX3M (۳ماهه)",
    }
    term_df = load_columns(DB_PATH, os.path.getmtime(DB_PATH), tuple(TERM_COLS.keys()))
    available_term = [c for c in TERM_COLS if c in term_df.columns]

    if len(available_term) < 2:
        st.warning("ستون‌های کافی برای ساختار تایم‌اسپرد VIX توی دیتابیس نیست.")
    else:
        term_clean = term_df[available_term].dropna(how="any")
        if term_clean.empty:
            st.warning("داده‌ی هم‌زمان برای همه‌ی این ستون‌ها موجود نیست.")
        else:
            latest = term_clean.iloc[-1]
            latest_date = term_clean.index[-1]
            labels = [TERM_COLS[c] for c in available_term]
            values = [latest[c] for c in available_term]

            is_contango = values[-1] >= values[0]
            curve_color = "#4caf50" if is_contango else "#d9534f"
            curve_state = "Contango — بازار آروم" if is_contango else "Backwardation — استرس کوتاه‌مدت"

            col_a, col_b = st.columns(2)

            with col_a:
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(
                    x=labels, y=values, mode="lines+markers+text",
                    line=dict(color=curve_color, width=2),
                    marker=dict(size=9),
                    text=[f"{v:.1f}" for v in values], textposition="top center",
                ))
                fig1.update_layout(
                    title=f"منحنی امروز ({latest_date.date()}) — {curve_state}",
                    template="plotly_dark", height=350,
                    margin=dict(l=10, r=10, t=40, b=10),
                )
                st.plotly_chart(fig1, use_container_width=True, key="summary_vix_curve")

            with col_b:
                if "VIX" in available_term and "vix3m!" in available_term:
                    spread = (term_clean["vix3m!"] - term_clean["VIX"]).tail(90)
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(
                        x=spread.index, y=spread.values, name="VIX3M − VIX",
                        line=dict(color=ACCENT, width=1.6),
                    ))
                    fig2.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.4)
                    fig2.update_layout(
                        title="روند شیب منحنی (VIX3M − VIX) — 90 روز اخیر",
                        template="plotly_dark", height=350,
                        margin=dict(l=10, r=10, t=40, b=10),
                    )
                    st.plotly_chart(fig2, use_container_width=True, key="summary_vix_spread")
                    st.caption("زیر خط صفر = Backwardation (نگرانی کوتاه‌مدت بیشتر از بلندمدت).")

    st.divider()
    st.caption(f"Source: {DB_PATH} (read-only) | Generated {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")