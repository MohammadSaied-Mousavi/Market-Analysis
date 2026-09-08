"""
==========================================================================
 Summary — نمای کلی بازار جهانی
==========================================================================
فرض مهم: چون فقط فایل خیلی اولیه‌ی summary.py (یه stub خالی) رو توی
سابقه دارم، این فایل رو کامل از نو ساختم. اگه نسخه‌ی واقعی‌ای که الان
داری چیز دیگه‌ای هم توش داشته، بگو تا با هم ادغامش کنیم.

بخش ۵ (تجزیه‌ی نرخ ۱۰ساله) اضافه شده: همون منطق چارت "NOM = REAL + INF
SWAP" که قبلاً بررسی کردیم، ولی روی ۱۰ساله (نه ۳۰ساله) چون DFII10/T10YIE
تاریخچه‌ی کامل و پیوسته دارن (برخلاف DFII30 که فقط از ۲۰۱۰ به بعده).
اینجا "INF SWAP" واقعی نداریم، پس از Breakeven (T10YIE) به‌عنوان معادل
نزدیک‌ترش استفاده شده — طبق بحثی که قبلاً داشتیم.
"""

import os
import re

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from bs4 import BeautifulSoup

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


# ==========================================================================
# اسکرپ زنده — GDPNow (رشد) و Cleveland Fed Inflation Nowcasting (تورم)
# ==========================================================================
# TTL (نه mtime دیتابیس) چون این دو تا هر روز کاری عوض می‌شن، مستقل از
# اینکه کی updater.py اجرا شده. هرکدوم اگه شکست بخوره، None برمی‌گردونه
# (نه خطا) — تا صفحه/نمودار crash نکنه، فقط نقطه‌ی nowcast رو نشون نده.

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_gdpnow() -> float | None:
    """
    ⚠️ شکننده‌ترین بخش این فیچره: صفحه‌ی Atlanta Fed جدول HTML نداره،
    فقط توی متن صفحه یه عدد نوشته. این regex بر اساس متن صفحه در زمان
    نوشتن این کد کار می‌کنه؛ اگه Atlanta Fed قالب صفحه رو عوض کنه،
    ممکنه دیگه match نده — برای همینه که کل این تابع try/except شده و
    شکستش نباید هیچ‌جای دیگه رو بشکنه.
    """
    try:
        resp = requests.get(
            "https://www.atlantafed.org/cqer/research/gdpnow",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        text = resp.text
        print(resp.status_code, len(resp.text))  # اگه status != 200 یا متن خیلی کوتاهه → مورد ۱

        patterns = [
            r"([\-\d]+\.\d+)%.{0,120}?GDPNow Estimate for",  # فرمت فعلی صفحه
            r"GDPNow model estimate[^0-9\-]{0,80}([\-\d]+\.\d+)\s*percent",  # fallback قدیمی
            r"Latest forecast:?\s*</?\w*>?\s*([\-\d]+\.\d+)",  # fallback قدیمی‌تر
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
            if m:
                return float(m.group(1))
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def scrape_core_cpi_nowcast(target_month_str: str) -> float | None:
    """
    target_month_str دقیقاً به فرمت خودِ جدول Cleveland Fed — مثلاً
    "October 2026". جدول HTML واقعی داره، پس این بخش پایدارتره.
    """
    try:
        resp = requests.get(
            "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        print("CPI:", resp.status_code, len(resp.text))
        print("target:", target_month_str)

        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            if "Core CPI" not in headers or "Month" not in headers:
                continue
            month_idx = headers.index("Month")
            cpi_idx = headers.index("Core CPI")
            for row in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) > max(month_idx, cpi_idx) and cells[month_idx].strip() == target_month_str:
                    return float(cells[cpi_idx])
    except Exception:
        pass
    return None


# ==========================================================================
# نمودار Growth vs Prices (ربعی) — REAL-GDP (فصلی، forward-fill روی ۳ ماه)
# در برابر CPILFESL MoM (ماهانه)
# ==========================================================================

QUADRANT_COLORS = {
    "pp": "#d9534f",  # + رشد, + تورم
    "pm": "#c9a24b",  # - رشد, + تورم
    "mp": "#4caf50",  # + رشد, - تورم
    "mm": "#2f9bd6",  # - رشد, - تورم
}
QUADRANT_LABELS = {
    "pp": "+ Inflation | + Growth",
    "pm": "+ Inflation | - Growth",
    "mp": "- Inflation | + Growth",
    "mm": "- Inflation | - Growth",
}


def _quadrant_key(growth: float, inflation: float) -> str:
    g = "p" if growth >= 0 else "m"
    i = "p" if inflation >= 0 else "m"
    return i + g  # ("pp","pm","mp","mm") -> ترتیب: تورم سپس رشد


def render_growth_vs_prices(db_path: str, mtime: float) -> None:
    st.markdown("### Growth vs Prices — REAL GDP × Core CPI (MoM)")

    raw = load_columns(db_path, mtime, ("A191RO1Q156NBEA", "CPILFESL"))
    if "A191RO1Q156NBEA" not in raw.columns or "CPILFESL" not in raw.columns:
        st.warning("ستون REAL-GDP یا CPILFESL توی دیتابیس نیست.")
        return

    gdp = raw["A191RO1Q156NBEA"].dropna()
    cpi = raw["CPILFESL"].dropna()
    gap_days = cpi.index.to_series().diff().dt.days
    cpi_mom = cpi.pct_change() * 100
    cpi_mom = cpi_mom.where(gap_days <= 40)  # جهش‌های چندماهه رو NaN می‌کنه، نه یه عدد غلط

    if gdp.empty or cpi.empty:
        st.warning("داده‌ی کافی برای این نمودار نیست.")
        return

    # تورم ماهانه (MoM ٪) از سطح شاخص CPILFESL
    cpi_mom = cpi.pct_change().dropna() * 100

    # رشد: هر ماه به فصل تقویمی خودش map می‌شه (نه ffill بر مبنای تاریخ،
    # چون به قرارداد تاریخ‌گذاری GDP در دیتابیس وابسته نمی‌مونه)
    gdp_by_quarter = gdp.groupby(gdp.index.to_period("Q")).last()
    growth_aligned = cpi_mom.index.to_period("Q").map(gdp_by_quarter)

    points = pd.DataFrame({"inflation": cpi_mom.values, "growth": growth_aligned}, index=cpi_mom.index).dropna()
    if len(points) < 5:
        st.warning("داده‌ی هم‌پوشانِ کافی بین REAL-GDP و CPILFESL نیست.")
        return

    points["quadrant"] = [_quadrant_key(g, i) for g, i in zip(points["growth"], points["inflation"])]

    fig = go.Figure()

    # نقاط عادی (همه بجز ۲ ماه آخر)
    older = points.iloc[:-2] if len(points) > 2 else points.iloc[0:0]
    for key, color in QUADRANT_COLORS.items():
        sub = older[older["quadrant"] == key]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["inflation"], y=sub["growth"], mode="markers",
            marker=dict(color=color, size=7),
            name=QUADRANT_LABELS[key],
        ))

    # ۲ ماه آخرِ *واقعی* — با نشونه‌ی مشکی روی همون رنگِ ربعشون
    last2 = points.iloc[-2:]
    marker_defs = [("second_recent", "circle-open", 12), ("most_recent", "x", 11)]
    for (label_key, symbol, size), (date, row) in zip(marker_defs, last2.iterrows()):
        fig.add_trace(go.Scatter(
            x=[row["inflation"]], y=[row["growth"]], mode="markers",
            marker=dict(color="white", size=size,
                        symbol=symbol, line=dict(color="black", width=2)),
            name=("Second Most Recent Data" if label_key == "second_recent" else "Most Recent Data"),
        ))

    # ---- تلاش برای nowcast (اسکرپ زنده) — اگه هرکدوم شکست بخوره، فقط رد می‌شیم ----
    last_cpi_month = cpi.index.max()
    target_month = (last_cpi_month + pd.DateOffset(months=1)).strftime("%B %Y")

    gdpnow_val = scrape_gdpnow()
    cpi_nowcast_val = scrape_core_cpi_nowcast(target_month)

    if gdpnow_val is not None and cpi_nowcast_val is not None:
        fig.add_trace(go.Scatter(
            x=[cpi_nowcast_val], y=[gdpnow_val], mode="markers+text",
            marker=dict(color="white", size=13, symbol="circle", line=dict(color="black", width=2)),
            text=["Nowcast"], textposition="top center", textfont=dict(color="white"),
            name=f"Nowcast ({target_month})",
        ))
        st.caption(f"نقطه‌ی سفید = nowcast برای {target_month} — رشد از GDPNow، تورم از Cleveland Fed.")
    else:
        missing = []
        if gdpnow_val is None:
            missing.append("GDPNow")
        if cpi_nowcast_val is None:
            missing.append("Cleveland Fed Core CPI")
        st.caption(f"⚠️ اسکرپ {' و '.join(missing)} ناموفق بود — فقط ۲ ماه واقعی نمایش داده می‌شه.")

    fig.add_vline(x=0, line_dash="dash", line_color="white", opacity=0.5)
    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
    fig.update_layout(
        template="plotly_dark", height=520,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="Core CPI MoM (%)"),
        yaxis=dict(title="REAL GDP (فصلی، %)"),
        legend=dict(orientation="v", x=1.02, y=1),
    )
    st.plotly_chart(fig, use_container_width=True, key="summary_growth_vs_prices")


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

    # ==================================================================
    # ۵) تجزیه‌ی نرخ اسمی ۱۰ساله: نرخ واقعی (Real) + برابری تورمی (Breakeven)
    # ==================================================================
    st.divider()
    st.markdown("### تجزیه‌ی نرخ ۱۰ساله — NOM = REAL + BREAKEVEN")

    decomp_lookback = st.number_input(
        "لوک‌بک این نمودار (روز معاملاتی)",
        min_value=20, max_value=2520, value=252, step=20, key="decomp_lookback",
    )

    decomp_df = load_columns(DB_PATH, os.path.getmtime(DB_PATH), ("10Y", "DFII10", "T10YIE"))
    required_cols = {"10Y", "DFII10", "T10YIE"}
    missing_cols = required_cols - set(decomp_df.columns)

    if missing_cols:
        st.warning(f"ستون‌های لازم برای این نمودار توی دیتابیس نیست: {', '.join(sorted(missing_cols))}")
    else:
        clean_decomp = decomp_df[["10Y", "DFII10", "T10YIE"]].dropna(how="any")
        if len(clean_decomp) < decomp_lookback + 1:
            st.warning(
                f"فقط {len(clean_decomp)} ردیف داده‌ی هم‌زمان هست، برای لوک‌بک {decomp_lookback} روزه کافی نیست."
            )
        else:
            window = clean_decomp.tail(decomp_lookback + 1)
            base = window.iloc[0]
            latest = window.iloc[-1]
            latest_date = window.index[-1]

            # تغییر تجمعی از ابتدای بازه (bps) — چون NOM ≈ REAL + BREAKEVEN در هر نقطه،
            # جمع دو تغییر هم تقریباً برابر تغییر NOM می‌شه (همون منطق چارت مرجع).
            nom_chg = (window["10Y"] - base["10Y"]) * 100
            real_chg = (window["DFII10"] - base["DFII10"]) * 100
            be_chg = (window["T10YIE"] - base["T10YIE"]) * 100

            st.caption(
                f"سطح فعلی ({latest_date.date()}): NOM {latest['10Y']:.2f}٪ "
                f"= REAL {latest['DFII10']:.2f}٪ + BREAKEVEN {latest['T10YIE']:.2f}٪ "
                f"— نمودار زیر تغییر تجمعی (bps) از {window.index[0].date()} تا امروز رو نشون می‌ده."
            )

            fig5 = go.Figure()
            fig5.add_trace(go.Bar(
                x=window.index, y=real_chg, name="REAL (DFII10)",
                marker_color="#2f9bd6", opacity=0.55,
            ))
            fig5.add_trace(go.Bar(
                x=window.index, y=be_chg, name="BREAKEVEN (T10YIE)",
                marker_color="#e8a33d", opacity=0.55,
            ))
            fig5.add_trace(go.Scatter(
                x=window.index, y=nom_chg, name="NOMINAL (10Y)",
                line=dict(color="#f4f4f4", width=1.8),
            ))
            fig5.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.3)
            fig5.update_layout(
                barmode="overlay",
                # عمداً عنوان داخل نمودار حذف شد (متن بالای چارت جایگزینش شده) —
                # ترکیب title + legend افقیِ بالای نمودار باعث روی‌هم‌افتادن می‌شد.
                template="plotly_dark", height=420,
                margin=dict(l=10, r=10, t=30, b=10),
                legend=dict(orientation="h", y=1.1),
                yaxis=dict(title="تغییر (bps)"),
            )
            st.plotly_chart(fig5, use_container_width=True, key=f"summary_decomp_{decomp_lookback}")
            st.caption(
                "دو میله‌ی هر روز روی هم قرار می‌گیرن، نه کنار هم — پس رنگ بلندتر همون عاملیه که اون روز "
                "بیشتر باعث تغییر نرخ شده: آبی یعنی نرخ بهره‌ی واقعی، نارنجی یعنی انتظار تورم. "
                "خط سفید هم همیشه برابر جمع این دوعدده، نه فقط میله‌ی بلندتر — پس اگه خط سفید بالاتر از هر دو "
                "میله باشه یعنی این دو عامل هم‌جهت بودن و اثرشون رو هم تقویت کرده؛ اگه خط سفید کوتاه یا نزدیک "
                "صفر باشه با وجود میله‌های بلند، یعنی این دو عامل برعکس هم حرکت کردن و اثر همدیگه رو خنثی کردن."
            )

    st.divider()

    # ==================================================================
    # ۶) Growth vs Prices (ربعی) — REAL-GDP × Core CPI MoM
    # ==================================================================
    render_growth_vs_prices(DB_PATH, os.path.getmtime(DB_PATH))

    st.divider()
    st.caption(f"Source: {DB_PATH} (read-only) | Generated {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")