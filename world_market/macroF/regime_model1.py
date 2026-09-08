"""
==========================================================================
 CREDIT & INFLATION REGIME DASHBOARD (FAST/TACTICAL)  —  regime_model1.py
==========================================================================

مسیر واقعی این فایل: world_market/macroF/regime_model1.py
(DB_PATH مستقیماً از constants.ROOT_DIR ساخته می‌شود، وابسته به این‌که این
فایل خودش چند پوشه پایین‌تر باشد نیست.)

نقش این مدل در کل پروژه
------------------------
این مدل عمداً یک سیگنال «سریع/تاکتیکی» است (دوچرخه)، در تضاد با مدل
Economic Regime / eco3min (کشتی) که با تأخیر ~2 ماهه و روی داده‌ی ماهانه
(CFNAI, Trimmed Mean PCE) کار می‌کند. هر دو در نهایت به‌عنوان دو فیچر
جداگانه (با دو سرعت متفاوت) وارد مدل یادگیری ماشین می‌شوند — پس رفتار
نویزی/سریع این مدل یک ویژگی است، نه باگ.

الهام این مدل مستقیماً از یک داشبورد Credit & Inflation Regime (سایت
Capital Flows) گرفته شده. محور «Growth» در این مدل در واقع «شرایط
مالی/ریسک اعتباری» (Credit Spread) را می‌سنجد، نه GDP واقعی — این دقیقاً
همان چیزی است که خودِ منبع اصلی هم می‌گوید («Spreads Falling/Rising»، نه
«GDP Up/Down»). برای یک سنجه‌ی رشد واقعی، به تب Economic Regime مراجعه کنید.

دو پنل مستقل (Rate of Change / Z-Score)
------------------------------------------
Z-Score از نظر ریاضی از روی همون ROC ساخته می‌شود (نرمال‌سازی روی یک
پنجره‌ی ۲۵۲ روزه)، پس این دو یک محاسبه‌ی مشترک نیستند که پشت یک دکمه
مخفی شوند؛ اینجا هرکدام پنل کاملاً مستقل خودشان را دارند: لوک‌بک خودشان،
کارت‌های خلاصه‌ی خودشان (با واحد درست: bps برای ROC، σ برای Z-Score) و
نمودار رژیم خودشان. بازه‌ی تاریخ (Start/End) بین دو پنل مشترک است.
پنجره‌ی نرمال‌سازی Z-Score (۲۵۲ روز) ثابت نگه داشته شده و از UI قابل
تغییر نیست (تصمیم مشترک).

آمار بازدهی/نوسان/بخشی هر رژیم (اضافه‌شده)
--------------------------------------------
سه ستون/جدول به خروجی هر پنل اضافه شده، هرکدام روی همون بازه‌ی تاریخ
انتخابی و همون سری Regime مخصوص آن پنل (RoC یا Z-Score) محاسبه می‌شوند:
  1. Avg Daily Return  — میانگین بازدهی روزانه‌ی SP500 در هر رژیم (٪)
  2. Daily Volatility   — انحراف‌معیار خامِ (غیر سالانه‌شده) بازدهی روزانه‌ی
     SP500 در هر رژیم (٪) — طبق تصمیم مشترک: خام، نه annualized.
  3. جدول جداگانه‌ی بازدهی روزانه‌ی هر زیربخش (SECTOR_COLUMNS) در هر رژیم.
بند ۱ و ۲ به جدول «Regime Statistics» موجود اضافه شدن (تابع
regime_statistics)؛ بند ۳ چون یک ماتریس رژیم×بخش است، expander جدای خودش
را دارد. ستون بازار (BENCHMARK_COL) طبق تصمیم مشترک ثابت روی "SP500" است؛
اگر دیتابیس این ستون را نداشته باشد، این دو بخش بی‌صدا (بدون خطا) نمایش
داده نمی‌شوند.

نکات فنی دیگر
--------------
- هیچ‌جای این کد دیتابیس نوشته/تغییر داده نمی‌شود؛ فقط pd.read_csv
  (read-only). کش (load_database) با mtime فایل invalidate می‌شود، پس
  اگر updater.py دیتابیس را آپدیت کند، خودش دفعه‌ی بعد دوباره خوانده
  می‌شود — نیازی به غیرفعال کردن کش نیست.
- طبق تصمیم مشترک، classify() روی مقدار دقیقاً صفر عمداً به Recession
  می‌افتد (fallback) و عمداً fix نشده: با حداقل لوک‌بک ۵ روزه، اگر داده
  ۵ روز کامل تکان نخورد احتمالاً تعطیلات است، نه یک سیگنال واقعی.
- کلید session_state این صفحه namespace دار شده (regime1_start/end) تا
  با صفحات دیگر (که همان navigation session را به اشتراک می‌گذارند)
  تداخل نکند — این تداخل قبلاً بین model1 و model2 وجود داشت.
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from constants import ROOT_DIR
from theme import inject_global_style

# ==========================================================================
# 1) تنظیمات پایه
# ==========================================================================

DB_PATH = os.path.join(ROOT_DIR, "database", "macro_database.csv")

# ستون‌های پیشنهادی برای هر محور — فقط راهنما، دراپ‌داون بسته/قفل نیست
SUGGESTED_CREDIT_COLS = ["BAMLC0A4CBBB"]
SUGGESTED_INFLATION_COLS = ["TDTF_IEI", "EXPINF2YR"]

DEFAULT_CREDIT_COL = "BAMLC0A4CBBB"
# TDTF_IEI به‌جای EXPINF2YR: فرکانس بالاتری دارد و با ROC روزانه سازگارتر
# است (EXPINF2YR معمولاً ماهانه آپدیت می‌شود و روی داده‌ی روزانه پله‌ای
# می‌شود). اگر دیتابیس شما فرق دارد، این مقدار را عوض کنید.
DEFAULT_INFLATION_COL = "TDTF_IEI"

# ستون بازار برای بند «بازدهی/نوسان روزانه‌ی هر رژیم» — طبق تصمیم مشترک: SP500.
# اگر دیتابیس این ستون را نداشته باشد، load_benchmark یک Series خالی
# برمی‌گرداند و بخش‌های مربوطه بی‌صدا از خروجی حذف می‌شوند (نه خطا).
BENCHMARK_COL = "SP500"

LOOKBACK_MIN = 5
LOOKBACK_MAX = 60
LOOKBACK_STEP = 5
LOOKBACK_DEFAULT = 60

ZSCORE_WINDOW = 252  # ثابت، طبق تصمیم مشترک از UI قابل‌تنظیم نیست

REGIME_INFO = {
    "Reflation": {
        "condition": "Spreads Falling / Inflation Rising",
        "desc": "Growth improving while inflation pressures building. Risk assets tend to perform well.",
        "color": "#c9a24b",
    },
    "Stagflation": {
        "condition": "Spreads Rising / Inflation Rising",
        "desc": "Growth deteriorating with rising inflation. Most challenging environment for portfolios.",
        "color": "#d9534f",
    },
    "Goldilocks": {
        "condition": "Spreads Falling / Inflation Falling",
        "desc": "Growth improving with easing inflation. Ideal environment for both stocks and bonds.",
        "color": "#4caf50",
    },
    "Recession": {
        "condition": "Spreads Rising / Inflation Falling",
        "desc": "Growth deteriorating with falling inflation. Flight to quality, duration outperforms.",
        "color": "#4a90d9",
    },
}


# ==========================================================================
# 2) خواندن دیتابیس — read-only، کش با mtime (نه غیرفعال، نه بی‌قید)
# ==========================================================================

@st.cache_data(show_spinner=False)
def load_database(path: str, mtime: float) -> pd.DataFrame:
    """mtime بدون آندرلاینه چون باید واقعاً در هشِ کش لحاظ بشه — با
    آندرلاین (نسخه‌ی قبلی)، Streamlit این پارامتر رو از محاسبه‌ی کش
    کنار می‌ذاره و کش هیچ‌وقت با تغییر فایل (بعد از updater.py) عوض
    نمی‌شه. خودِ مقدار مستقیم استفاده نمی‌شه، فقط برای invalidate‌شدنه."""
    df = pd.read_csv(path)
    date_col = "Date" if "Date" in df.columns else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _ordered_with_suggestions(all_cols, suggested) -> list[str]:
    """ستون‌های پیشنهادی را اول لیست می‌آورد؛ بقیه دست‌نخورده و انتخاب‌پذیر می‌مانند."""
    all_cols = list(all_cols)
    ordered = [c for c in suggested if c in all_cols]
    ordered += [c for c in all_cols if c not in suggested]
    return ordered


def _load_levels(df: pd.DataFrame, credit_col: str, inflation_col: str) -> pd.DataFrame:
    """سطح دو سری خام را به bps تبدیل می‌کند — مستقل از لوک‌بک/روش، برای نمودار سطح بالای صفحه."""
    out = df[[credit_col, inflation_col]].rename(
        columns={credit_col: "CREDIT_RAW", inflation_col: "INFLATION_RAW"}
    ).copy()
    out = out.asfreq("B").ffill()
    out["CREDIT_BPS"] = out["CREDIT_RAW"] * 100
    out["INFLATION_BPS"] = out["INFLATION_RAW"] * 100
    return out


# ==========================================================================
# اعتبارسنجی رژیم با شاخص‌های بخشی (نه لوک‌بک — فقط طول واقعیِ اپیزود
# فعلی و اپیزود قبلیِ رژیم، دقیقاً مثل بخش Asset Class Behaviour مقاله‌ی
# SSRN 3144169، ولی به‌جای میانگین روی کل تاریخچه، فقط همین دو اپیزود)
# ==========================================================================

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
def load_sector_prices(path: str, mtime: float) -> pd.DataFrame:
    """فقط ستون‌هایی از SECTOR_COLUMNS که واقعاً توی دیتابیس هستن رو
    می‌خونه (اگه updater.py هنوز اجرا نشده باشه، خالی برمی‌گرده، نه خطا)."""
    available = pd.read_csv(path, nrows=0).columns
    cols = [c for c in SECTOR_COLUMNS if c in available]
    if not cols:
        return pd.DataFrame()
    df = pd.read_csv(path, usecols=["Date"] + cols)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.asfreq("B").ffill()


@st.cache_data(show_spinner=False)
def load_benchmark(path: str, mtime: float, col: str = BENCHMARK_COL) -> pd.Series:
    """قیمت روزانه‌ی ستون بازار (پیش‌فرض SP500) را می‌خواند — پایه‌ی
    محاسبه‌ی «بازدهی/نوسان روزانه‌ی هر رژیم». اگر ستون در دیتابیس نبود،
    Series خالی برمی‌گرداند (نه خطا) و بخش‌های مربوطه در UI حذف می‌شوند."""
    available = pd.read_csv(path, nrows=0).columns
    if col not in available:
        return pd.Series(dtype=float, name=col)
    df = pd.read_csv(path, usecols=["Date", col])
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    s = pd.to_numeric(df[col], errors="coerce")
    return s.asfreq("B").ffill()


def _episode_bounds(days_in_regime: pd.Series):
    """
    برمی‌گردونه (current, previous) که هرکدوم یا None یا (start, end, length).
    current = اپیزودِ رژیمی که همین الان توش هستیم (تا امروز).
    previous = کل اپیزودِ رژیمِ درست قبل از این یکی (طول کامل خودش،
    نه یه لوک‌بکِ دلخواه).
    """
    n = len(days_in_regime)
    if n == 0:
        return None, None

    n_current = int(days_in_regime.iloc[-1])
    if n_current < 1:
        return None, None
    n_current = min(n_current, n)
    current_start_idx = n - n_current
    current = (days_in_regime.index[current_start_idx], days_in_regime.index[-1], n_current)

    prev_end_idx = current_start_idx - 1
    if prev_end_idx < 0:
        return current, None

    n_previous = int(days_in_regime.iloc[prev_end_idx])
    prev_start_idx = max(prev_end_idx - n_previous + 1, 0)
    n_previous = prev_end_idx - prev_start_idx + 1  # اگه داده کافی برای کل طول نبود، واقعی‌ش رو گزارش کن
    previous = (days_in_regime.index[prev_start_idx], days_in_regime.index[prev_end_idx], n_previous)

    return current, previous


def _sector_period_return(sector_df: pd.DataFrame, start_date, end_date) -> pd.Series:
    """بازدهی درصدی هر ستون، از روز معاملاتیِ درست قبل از start_date تا end_date."""
    idx = sector_df.index
    pos_start = idx.searchsorted(start_date)
    pos_base = max(pos_start - 1, 0)
    base_prices = sector_df.iloc[pos_base]
    end_prices = sector_df.loc[end_date]
    ret = (end_prices / base_prices - 1) * 100
    return ret.dropna().sort_values(ascending=False)


def _sector_return_html(ret: pd.Series) -> str:
    rows = []
    for ticker, value in ret.items():
        color = "#4caf50" if value >= 0 else "#d9534f"
        name = SECTOR_COLUMNS.get(ticker, ticker)
        rows.append(
            f"<div style='display:flex;justify-content:space-between;font-size:0.82rem;padding:2px 0;'>"
            f"<span>{ticker} <span style='color:#8a8f98;'>({name})</span></span>"
            f"<span style='color:{color};font-weight:600;'>{value:+.1f}%</span></div>"
        )
    return "".join(rows) if rows else "<div style='color:#8a8f98;font-size:0.82rem;'>داده‌ای موجود نیست</div>"


def render_sector_validation_table(panels: dict, sector_df: pd.DataFrame) -> None:
    """
    panels: {"RoC": valid_df_roc, "Z-Score": valid_df_zscore}
    جدول ۴ستونه‌ی رژیم فعلی/قبلی برای هر روش، مطابق چیدمانی که خودت
    طراحی کردی.
    """
    st.markdown("### 🧪 اعتبارسنجی رژیم با شاخص‌های بخشی")
    st.caption(
        "بازدهی هر شاخص فقط در طول *همین یک اپیزود* (نه یه لوک‌بک دلخواه) — "
        "طول اپیزود فعلی از «Days in Current Regime» میاد، طول اپیزود قبلی از "
        "طول کامل خودِ اون رژیم قبل از این‌که عوض بشه."
    )

    if sector_df.empty:
        st.warning(
            "هیچ‌کدوم از ستون‌های شاخص بخشی (RSP, XLK, ...) توی دیتابیس نیستن — "
            "بعد از اجرای updater.py با این ستون‌های جدید، دوباره چک کن."
        )
        return

    header_cells = "".join(
        f"<th colspan='2' style='padding:8px;border:1px solid #333;text-align:center;'>{name}</th>"
        for name in panels
    )

    def _cell(bounds, ep_kind: str) -> str:
        current, previous = bounds
        ep = current if ep_kind == "current" else previous
        if ep is None:
            return "<td style='padding:8px;border:1px solid #333;vertical-align:top;'>داده‌ی کافی نیست</td>"
        start, end, length = ep
        ret = _sector_period_return(sector_df, start, end)
        return (
            "<td style='padding:8px;border:1px solid #333;vertical-align:top;width:25%;'>"
            f"<div style='font-size:0.8rem;color:#8a8f98;'>{start.date()} → {end.date()}</div>"
            f"<div style='font-weight:700;margin:4px 0;'>{length} روز</div>"
            f"{_sector_return_html(ret)}"
            "</td>"
        )

    all_bounds = {name: _episode_bounds(df["Days_in_regime"]) for name, df in panels.items()}

    label_row = "".join(
        "<td style='padding:6px;border:1px solid #333;text-align:center;'>رژیم فعلی</td>"
        "<td style='padding:6px;border:1px solid #333;text-align:center;'>رژیم قبلی</td>"
        for _ in panels
    )
    data_row = "".join(
        _cell(all_bounds[name], "current") + _cell(all_bounds[name], "previous")
        for name in panels
    )

    st.markdown(
        f"""
        <table style="width:100%;border-collapse:collapse;">
            <tr>{header_cells}</tr>
            <tr>{label_row}</tr>
            <tr>{data_row}</tr>
        </table>
        """,
        unsafe_allow_html=True,
    )


def sector_regime_returns(valid: pd.DataFrame, sector_df: pd.DataFrame) -> pd.DataFrame:
    """میانگین بازدهی روزانه‌ی هر زیربخش (٪)، به تفکیک رژیم، محدود به
    بازه‌ی valid.index (یعنی همون بازه‌ی تاریخ انتخابی کاربر). یک سطر
    برای هر ۴ رژیم برمی‌گرداند، حتی اگه رژیمی توی این بازه رخ نداده باشه
    (NaN) — برای این‌که چیدمان جدول بین پنل‌ها یکسان بمونه."""
    if sector_df.empty:
        return pd.DataFrame()
    sub = valid.dropna(subset=["Regime"])
    if sub.empty:
        return pd.DataFrame()

    sector_ret = sector_df.pct_change().mul(100)
    aligned = sector_ret.reindex(sub.index)
    aligned["Regime"] = sub["Regime"]

    out = aligned.groupby("Regime").mean(numeric_only=True)
    cols = [c for c in SECTOR_COLUMNS if c in out.columns]
    if not cols:
        return pd.DataFrame()
    out = out[cols].round(3)
    out = out.reindex(list(REGIME_INFO.keys()))
    out.columns = [f"{c} ({SECTOR_COLUMNS[c]})" for c in out.columns]
    out.index.name = "Regime"
    return out


# ==========================================================================
# 3) طبقه‌بندی رژیم (مشترک بین دو پنل)
# ==========================================================================

def classify(c, i):
    """طبق تصمیم مشترک: حالت c==0 یا i==0 عمداً fix نشده (fallback به Recession)."""
    if pd.isna(c) or pd.isna(i):
        return np.nan
    if c < 0 and i > 0:
        return "Reflation"
    if c > 0 and i > 0:
        return "Stagflation"
    if c < 0 and i < 0:
        return "Goldilocks"
    return "Recession"


def _days_in_state(state_series: pd.Series) -> pd.Series:
    counts, run, prev = [], 0, None
    for v in state_series.tolist():
        if pd.isna(v):
            run = 0
        elif v == prev:
            run += 1
        else:
            run = 1
        counts.append(run)
        prev = v if pd.notna(v) else prev
    return pd.Series(counts, index=state_series.index)


def regime_statistics(df: pd.DataFrame, benchmark_ret: pd.Series | None = None) -> pd.DataFrame:
    """جدول آمار هر رژیم روی بازه‌ی انتخابی. اگر benchmark_ret داده بشه
    (سری بازدهی روزانه‌ی SP500، از پیش align نشده)، دو ستون اضافه می‌شن:
    میانگین بازدهی روزانه و نوسان روزانه (انحراف‌معیار خام، غیر سالانه‌شده)
    — طبق تصمیم مشترک، نه واریانس مجذوری و نه annualized."""
    sub = df.dropna(subset=["Regime"]).copy()
    has_benchmark = benchmark_ret is not None and not benchmark_ret.empty
    if has_benchmark:
        sub["BENCHMARK_RET"] = benchmark_ret.reindex(sub.index)

    total_days = len(sub)
    rows = []
    for regime in REGIME_INFO:
        mask = sub["Regime"] == regime
        days = int(mask.sum())
        occurrences = int((mask & ~mask.shift(1, fill_value=False)).sum())
        row = {
            "Regime": regime,
            "Days": days,
            "% of Period": round(100 * days / total_days, 1) if total_days else np.nan,
            "Avg Spread (bps)": round(sub.loc[mask, "CREDIT_BPS"].mean(), 0) if days else np.nan,
            "Avg Inflation (bps)": round(sub.loc[mask, "INFLATION_BPS"].mean(), 0) if days else np.nan,
            "Occurrences": occurrences,
        }
        if has_benchmark:
            row[f"Avg Daily Return ({BENCHMARK_COL}, %)"] = (
                round(sub.loc[mask, "BENCHMARK_RET"].mean(), 3) if days else np.nan
            )
            row[f"Daily Volatility ({BENCHMARK_COL}, %, raw std)"] = (
                round(sub.loc[mask, "BENCHMARK_RET"].std(), 3) if days else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows).set_index("Regime")


# ==========================================================================
# 4) دو موتور محاسبه — ROC (bps) و Z-Score (σ)، هرکدام مستقل
# ==========================================================================

def compute_roc_signal(df, credit_col, inflation_col, credit_lookback, inflation_lookback) -> pd.DataFrame:
    out = _load_levels(df, credit_col, inflation_col)
    out["CREDIT_SIGNAL"] = out["CREDIT_BPS"].diff(credit_lookback)
    out["INFLATION_SIGNAL"] = out["INFLATION_BPS"].diff(inflation_lookback)
    out["Regime"] = [classify(c, i) for c, i in zip(out["CREDIT_SIGNAL"], out["INFLATION_SIGNAL"])]
    out["Days_in_regime"] = _days_in_state(out["Regime"])
    return out


def compute_zscore_signal(df, credit_col, inflation_col, credit_lookback, inflation_lookback,
                           zscore_window: int = ZSCORE_WINDOW) -> pd.DataFrame:
    out = _load_levels(df, credit_col, inflation_col)
    credit_roc = out["CREDIT_BPS"].diff(credit_lookback)
    inflation_roc = out["INFLATION_BPS"].diff(inflation_lookback)
    out["CREDIT_SIGNAL"] = (
        (credit_roc - credit_roc.rolling(zscore_window, min_periods=30).mean())
        / credit_roc.rolling(zscore_window, min_periods=30).std()
    )
    out["INFLATION_SIGNAL"] = (
        (inflation_roc - inflation_roc.rolling(zscore_window, min_periods=30).mean())
        / inflation_roc.rolling(zscore_window, min_periods=30).std()
    )
    out["Regime"] = [classify(c, i) for c, i in zip(out["CREDIT_SIGNAL"], out["INFLATION_SIGNAL"])]
    out["Days_in_regime"] = _days_in_state(out["Regime"])
    return out


# ==========================================================================
# 5) رندر یک پنل کامل و مستقل (لوک‌بک خودش، کارت‌ها، نمودار، آمار)
# ==========================================================================

def render_panel(raw, credit_col, inflation_col, start_date, end_date,
                  method_label, compute_fn, signal_unit, key_prefix,
                  benchmark_ret: pd.Series | None = None,
                  benchmark_prices: pd.Series | None = None,
                  sector_df: pd.DataFrame | None = None):
    st.markdown(f"### {method_label}")

    def _compact_lookback(container, label, widget_key):
        """لیبل و کادر عدد در یک ردیف، به‌جای لیبل روی یک خط و کادر روی خط بعدی."""
        lbl_col, inp_col = container.columns([3, 1], vertical_alignment="center")
        lbl_col.markdown(f"<div style='font-size:0.95rem;'>{label}</div>", unsafe_allow_html=True)
        return inp_col.number_input(
            label,
            min_value=LOOKBACK_MIN, max_value=LOOKBACK_MAX, value=LOOKBACK_DEFAULT, step=LOOKBACK_STEP,
            key=widget_key, label_visibility="collapsed",
        )

    lc1, lc2 = st.columns(2)
    credit_lb = _compact_lookback(lc1, f"Credit {method_label} Lookback (days)", f"{key_prefix}_credit_lb")
    infl_lb = _compact_lookback(lc2, f"Inflation {method_label} Lookback (days)", f"{key_prefix}_infl_lb")

    df = compute_fn(raw, credit_col, inflation_col, int(credit_lb), int(infl_lb))
    df = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

    valid = df.dropna(subset=["Regime"])
    if valid.empty:
        st.warning("داده‌ای برای بازهٔ انتخاب‌شده با این لوک‌بک موجود نیست.")
        return

    cur = valid.iloc[-1]

    # ---- کارت‌های خلاصه (واحد درست: bps یا σ) ----
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Regime", cur["Regime"])
    m2.metric(f"Credit Signal ({signal_unit})", f"{cur['CREDIT_SIGNAL']:.2f}")
    m3.metric(f"Inflation Signal ({signal_unit})", f"{cur['INFLATION_SIGNAL']:.2f}")
    m4.metric("Days in Current Regime", int(cur["Days_in_regime"]))

    # ---- Regime Quadrant ----
    quad_order = ["Reflation", "Stagflation", "Goldilocks", "Recession"]
    qcols = st.columns(4)
    for col, name in zip(qcols, quad_order):
        info = REGIME_INFO[name]
        is_current = name == cur["Regime"]
        border = f"3px solid {info['color']}" if is_current else "1px solid #333"
        bg = f"{info['color']}22" if is_current else "transparent"
        col.markdown(
            f"""
            <div style="border:{border};background:{bg};border-radius:8px;padding:10px;height:110px;">
                <div style="color:{info['color']};font-weight:600;">{name}{' 🔵' if is_current else ''}</div>
                <div style="font-size:0.75em;margin-top:6px;">{info['desc']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---- نمودار سیگنال + رنگ‌آمیزی رژیم (خط و واحد متناسب با روش) ----
    fig = go.Figure()
    # این دو خط کمرنگ‌تر شدن (opacity) تا خط SP500 که اضافه شده برجسته‌تر دیده بشه.
    fig.add_trace(go.Scatter(x=valid.index, y=valid["CREDIT_SIGNAL"], name=f"Credit {method_label} ({signal_unit})",
                              line=dict(color="#2f9bd6", width=1), opacity=0.35))
    fig.add_trace(go.Scatter(x=valid.index, y=valid["INFLATION_SIGNAL"], name=f"Inflation {method_label} ({signal_unit})",
                              yaxis="y2", line=dict(color="#e8a33d", width=1), opacity=0.35))

    # ---- SP500 (فقط close) روی محور سوم مستقل — بی‌صدا حذف می‌شه اگه ستون نباشه ----
    has_sp500 = benchmark_prices is not None and not benchmark_prices.empty
    if has_sp500:
        sp_aligned = benchmark_prices.reindex(valid.index)
        fig.add_trace(go.Scatter(x=valid.index, y=sp_aligned, name=f"{BENCHMARK_COL} Close",
                                  yaxis="y3", line=dict(color="#f4f4f4", width=1.8)))

    prev, seg_start = None, valid.index[0]
    for date, regime in valid["Regime"].items():
        if regime != prev:
            if prev is not None:
                fig.add_vrect(x0=seg_start, x1=date, fillcolor=REGIME_INFO[prev]["color"], opacity=0.5, line_width=0)
            seg_start, prev = date, regime
    fig.add_vrect(x0=seg_start, x1=valid.index[-1], fillcolor=REGIME_INFO[prev]["color"], opacity=0.5, line_width=0)

    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.4)
    layout_kwargs = dict(
        yaxis=dict(title=f"Credit {method_label} ({signal_unit})"),
        yaxis2=dict(title=f"Inflation {method_label} ({signal_unit})", overlaying="y", side="right"),
        template="plotly_dark", height=380, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=1.1),
    )
    if has_sp500:
        # محور سوم مخفی (بدون تیک/گرید) — فقط برای اینکه شکل SP500 با مقیاس خودش
        # روی همون نمودار overlay بشه، بدون شلوغ کردن محورها.
        layout_kwargs["yaxis3"] = dict(overlaying="y", side="right", showticklabels=False, showgrid=False,
                                        zeroline=False, type="log")
    fig.update_layout(**layout_kwargs)
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_chart")

    # ---- آمار رژیم (جمع‌شونده) — شامل بازدهی/نوسان روزانه‌ی SP500 اگر موجود باشه ----
    with st.expander(f"📊 Regime Statistics — {method_label} (Selected Range)", expanded=False):
        if benchmark_ret is not None and not benchmark_ret.empty:
            bench_sub = benchmark_ret.reindex(valid.index)
            st.caption(
                f"مرجع مقایسه — میانگین بازدهی روزانه‌ی {BENCHMARK_COL} در کل بازه‌ی انتخابی "
                f"(بدون تفکیک رژیم): **{bench_sub.mean():.3f}٪** · نوسان روزانه: **{bench_sub.std():.3f}٪**. "
                "این عدد باید تقریباً میانگین وزنیِ ۴ سطر پایین باشه (چک سازگاری) — اگه خودش قویاً مثبته "
                "(روند صعودی غالب بازه)، طبیعیه هر ۴ رژیم هم به این عدد نزدیک و اغلب مثبت باشن، "
                "مخصوصاً چون این مدل بدون هیسترزیسه و برچسب‌ها زود عوض می‌شن (ستون Occurrences را ببینید)."
            )
        st.dataframe(regime_statistics(valid, benchmark_ret), use_container_width=True)

    # ---- میانگین بازدهی روزانه‌ی هر زیربخش در هر رژیم ----
    if sector_df is not None and not sector_df.empty:
        with st.expander(
            f"🏭 میانگین بازدهی روزانه‌ی هر زیربخش در هر رژیم — {method_label} (Selected Range)",
            expanded=False,
        ):
            sec_stats = sector_regime_returns(valid, sector_df)
            if sec_stats.empty:
                st.caption("داده‌ای برای محاسبه موجود نیست.")
            else:
                st.dataframe(sec_stats, use_container_width=True)

    return valid


# ==========================================================================
# 6) رابط کاربری اصلی
# ==========================================================================

def show() -> None:
    inject_global_style()
    st.markdown("# 📊 Credit & Inflation Regime Dashboard")
    st.caption("سیگنال سریع/تاکتیکی — الهام‌گرفته از داشبورد Credit & Inflation Regime (Capital Flows)")
    st.caption(
        "⚠️ محور «رشد» اینجا در واقع شرایط مالی/ریسک اعتباری (Credit Spread) را می‌سنجد، نه GDP واقعی. "
        "برای سیگنال کند/پایدار مبتنی بر رشد واقعی، تب Economic Regime (eco3min) را ببینید."
    )

    if not os.path.isfile(DB_PATH):
        st.error(
            f"دیتابیس پیدا نشد:\n`{DB_PATH}`\n\n"
            "مسیر DB_PATH را در بالای فایل regime_model1.py مطابق ساختار پروژه‌ خودتان اصلاح کنید."
        )
        return

    raw = load_database(str(DB_PATH), os.path.getmtime(DB_PATH))

    with st.expander("Advanced: انتخاب ستون‌های دیتابیس", expanded=False):
        col_a, col_b = st.columns(2)
        credit_options = _ordered_with_suggestions(raw.columns, SUGGESTED_CREDIT_COLS)
        inflation_options = _ordered_with_suggestions(raw.columns, SUGGESTED_INFLATION_COLS)
        credit_col = col_a.selectbox(
            "Credit Spread column",
            options=credit_options,
            index=credit_options.index(DEFAULT_CREDIT_COL) if DEFAULT_CREDIT_COL in credit_options else 0,
        )
        inflation_col = col_b.selectbox(
            "Inflation Proxy column",
            options=inflation_options,
            index=inflation_options.index(DEFAULT_INFLATION_COL) if DEFAULT_INFLATION_COL in inflation_options else 0,
        )
        st.caption(
            f"پیشنهادی برای Credit: {', '.join(SUGGESTED_CREDIT_COLS)} | "
            f"برای Inflation: {', '.join(SUGGESTED_INFLATION_COLS)} — بقیه‌ی ستون‌ها هم قابل انتخابند، "
            "فقط مطمئن شوید واحدشان با bps/درصد سازگار است."
        )

    # ---- بازه‌ی تاریخ مشترک بین هر دو پنل ----
    c1, c2, c3, c4, c5 = st.columns(5)
    min_date, max_date = raw.index.min().date(), raw.index.max().date()

    if "regime1_start" not in st.session_state:
        st.session_state.regime1_start = min_date
        st.session_state.regime1_end = max_date

    start_date = c1.date_input("Start Date", value=st.session_state.regime1_start, min_value=min_date, max_value=max_date)
    end_date = c2.date_input("End Date", value=st.session_state.regime1_end, min_value=min_date, max_value=max_date)

    quick_map = {"1Y": 365, "2Y": 365 * 2, "5Y": 365 * 5, "10Y": 365 * 10}
    for col, label in zip((c3, c4, c5), list(quick_map)[:3]):
        if col.button(label, use_container_width=True):
            st.session_state.regime1_start = max(min_date, (raw.index.max() - pd.Timedelta(days=quick_map[label])).date())
            st.session_state.regime1_end = max_date
            st.rerun()

    qb1, qb2, qb3 = st.columns(3)
    for col, label in zip((qb1, qb2), list(quick_map)[3:]):
        if col.button(label, use_container_width=True):
            st.session_state.regime1_start = max(min_date, (raw.index.max() - pd.Timedelta(days=quick_map[label])).date())
            st.session_state.regime1_end = max_date
            st.rerun()
    if qb3.button("ALL", use_container_width=True):
        st.session_state.regime1_start = min_date
        st.session_state.regime1_end = max_date
        st.rerun()

    if credit_col not in raw.columns or inflation_col not in raw.columns:
        st.error("ستون انتخاب‌شده در دیتابیس پیدا نشد.")
        return

    # ---- نمودار سطح (مستقل از لوک‌بک/روش) ----
    levels = _load_levels(raw, credit_col, inflation_col)
    levels = levels[(levels.index.date >= start_date) & (levels.index.date <= end_date)]
    st.markdown(f"#### {credit_col} & {inflation_col}")
    fig_levels = go.Figure()
    fig_levels.add_trace(go.Scatter(x=levels.index, y=levels["CREDIT_BPS"] / 100, name=f"{credit_col} (%)",
                                     yaxis="y1", line=dict(color="#2f9bd6")))
    fig_levels.add_trace(go.Scatter(x=levels.index, y=levels["INFLATION_BPS"], name=f"{inflation_col} (bps)",
                                     yaxis="y2", line=dict(color="#e8a33d")))
    fig_levels.update_layout(
        yaxis=dict(title=f"{credit_col} (%)"),
        yaxis2=dict(title=f"{inflation_col} (bps)", overlaying="y", side="right"),
        template="plotly_dark", height=340, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig_levels, use_container_width=True, key="levels_chart")

    # ---- ماتریس طبقه‌بندی (مشترک، مستقل از روش) ----
    st.markdown("#### Regime Classification Matrix")
    mc1, mc2 = st.columns(2)
    mc1.markdown("**SPREADS FALLING (GROWTH+)**")
    mc1.markdown("🟡 **Reflation** — Spreads tightening + inflation up")
    mc1.markdown("🟢 **Goldilocks** — Spreads tightening + inflation down")
    mc2.markdown("**SPREADS RISING (GROWTH-)**")
    mc2.markdown("🔴 **Stagflation** — Spreads widening + inflation up")
    mc2.markdown("🔵 **Recession** — Spreads widening + inflation down")

    # ---- داده‌ی مشترکِ بند ۱/۲/۳ (بازدهی/نوسان بازار + بازدهی زیربخش‌ها) ----
    # یک‌بار لود می‌شن (کش شده با mtime) و بین هر دو پنل به اشتراک گذاشته می‌شن،
    # همون‌طور که پایین‌تر برای جدول اعتبارسنجی بخشی هم استفاده می‌شن.
    benchmark_prices = load_benchmark(str(DB_PATH), os.path.getmtime(DB_PATH))
    benchmark_ret = benchmark_prices.pct_change().mul(100) if not benchmark_prices.empty else pd.Series(dtype=float)
    sector_df = load_sector_prices(str(DB_PATH), os.path.getmtime(DB_PATH))

    st.divider()
    roc_valid = render_panel(raw, credit_col, inflation_col, start_date, end_date,
                              method_label="Rate of Change", compute_fn=compute_roc_signal,
                              signal_unit="bps", key_prefix="roc",
                              benchmark_ret=benchmark_ret, benchmark_prices=benchmark_prices,
                              sector_df=sector_df)

    st.divider()
    zscore_valid = render_panel(raw, credit_col, inflation_col, start_date, end_date,
                                 method_label="Z-Score", compute_fn=compute_zscore_signal,
                                 signal_unit="σ", key_prefix="z",
                                 benchmark_ret=benchmark_ret, benchmark_prices=benchmark_prices,
                                 sector_df=sector_df)

    st.divider()
    panels = {}
    if roc_valid is not None:
        panels["RoC"] = roc_valid
    if zscore_valid is not None:
        panels["Z-Score"] = zscore_valid
    if panels:
        render_sector_validation_table(panels, sector_df)

    st.caption(
        f"Source: {DB_PATH} (read-only) | Generated {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"
    )