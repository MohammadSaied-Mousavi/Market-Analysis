"""
==========================================================================
 Model 6 — replication روش‌شناسی مقاله‌ی SSRN 3144169 روی S&P500
==========================================================================

فقط نمایشیه — هیچ‌جا چیزی save/to_csv نمی‌کنه.

فرضیات صریحی که چون خودِ مقاله مبهم بود، انتخاب شدن (نه استخراج قطعی):
  ۱) لایه‌ی واریانس: MarkovRegression با trend='c', switching_trend=False,
     switching_variance=True, بدون جمله‌ی AR. (تأییدشده با سند: مثال
     رسمی خودِ statsmodels برای دقیقاً همین «two-variance, no mean
     effect» از trend='n' استفاده می‌کنه؛ trend='c' را هم آزمایش
     کردیم — تفاوت معناداری توی نسبت واریانس ایجاد نکرد.)
  ۲) TMA = SMA روی SMA (double smoothing ساده).
  ۳) ATR واقعیه (از SP500_H/SP500_L/SP500)، میانگین ساده‌ی True Range
     روی ۲۰ روز (نه smoothing وایلدر).
  ۴) بازدهی فقط بین دو observation معتبر و متوالی (نه پرکردن جای خالی).
  ۵) smoothed probability (نه filtered) — چون این صفحه مطالعه‌ی
     تاریخیه، نه فیچر زنده.

گزینه‌ی log/simple برای بازدهی نگه داشته شده تا مقایسه‌ی سریع ممکن
باشه؛ نتیجه‌ی آزمایش‌مون نشون داد این انتخاب هم تفاوت معناداری روی
نسبت واریانس ایجاد نمی‌کنه (هر دو تقریباً ۸.۰، در برابر ۴.۵ مقاله).
"""

import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

from constants import ROOT_DIR
from theme import inject_global_style, ACCENT

# ==========================================================================
# تنظیمات
# ==========================================================================

DB_PATH = os.path.join(ROOT_DIR, "database", "macro_database.csv")
CLOSE_COL = "SP500"
HIGH_COL = "SP500_H"
LOW_COL = "SP500_L"

TMA_WINDOW = 250
ATR_WINDOW = 20
KELTNER_MULT = 1.0

REGIME_MAP = {
    ("bullish", "low_var"): "Advance",
    ("bullish", "high_var"): "Accumulation",
    ("bearish", "high_var"): "Decline",
    ("bearish", "low_var"): "Distribution",
}
REGIME_ORDER = ["Advance", "Accumulation", "Decline", "Distribution"]

REGIME_COLORS = {
    "Advance": "#4caf50",
    "Accumulation": ACCENT,
    "Decline": "#d9534f",
    "Distribution": "#4a90d9",
}

# همون ۱۲ شاخص بخشی که برای model1 استفاده کردیم — universe یکسان،
# تا نتیجه‌ها بین صفحات قابل‌مقایسه بمونن.
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


# ==========================================================================
# توابع محاسباتی خام (بدون Streamlit، قابل تست جدا)
# ==========================================================================

def _to_returns(close: pd.Series, kind: str = "log") -> pd.Series:
    """
    بازدهی فقط بین دو observation معتبر و متوالی (نه پرکردن جای خالی).
    kind="log"    -> log(P_t / P_{t-1})
    kind="simple" -> (P_t - P_{t-1}) / P_{t-1}
    """
    valid = close.dropna()
    if kind == "simple":
        ret = valid.pct_change()
    else:
        ret = np.log(valid / valid.shift(1))
    return ret.dropna()


def _continuous(s: pd.Series) -> pd.Series:
    return s.asfreq("B").ffill()


def _triangular_ma(price: pd.Series, window: int) -> pd.Series:
    half = window // 2 + 1
    return price.rolling(half, min_periods=half).mean().rolling(half, min_periods=half).mean()


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    return pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)


def _average_true_range(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    return _true_range(high, low, close).rolling(window, min_periods=window).mean()


def _keltner_filter(price, tma, trend_regime, atr, mult) -> pd.Series:
    confirmed = trend_regime.copy()
    distance = (price - tma).abs()
    unconfirmed_mask = distance < (mult * atr)
    confirmed = confirmed.where(~unconfirmed_mask, other=np.nan)
    confirmed = confirmed.ffill()
    return confirmed


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


def _regime_transition_lookup(res, low_var_state: int, high_var_state: int) -> dict:
    """
    dict با کلید (from_label, to_label) -> احتمال گذار، بر چسب‌های
    low_var/high_var (نه اندیس خام ۰/۱ که بین دو fit مختلف ممکنه
    جابه‌جا باشه). طبق مستندات رسمی statsmodels: p[i->j] یعنی احتمال
    گذار از رژیم i به رژیم j.
    """
    p00 = res.params["p[0->0]"]  # P(فردا=۰ | امروز=۰)
    p10 = res.params["p[1->0]"]  # P(فردا=۰ | امروز=۱)
    raw = {
        (0, 0): p00,
        (0, 1): 1 - p00,
        (1, 0): p10,
        (1, 1): 1 - p10,
    }
    label = {low_var_state: "low_var", high_var_state: "high_var"}
    return {(label[frm], label[to]): prob for (frm, to), prob in raw.items()}


# ==========================================================================
# پایپ‌لاین کامل — کش‌شده با mtime. همیشه روی کل تاریخچه.
# ==========================================================================

@st.cache_data(show_spinner="در حال فیت مدل Markov-Switching...")
def run_pipeline(db_path: str, mtime: float, return_kind: str = "log"):
    ohlc = pd.read_csv(db_path, usecols=["Date", CLOSE_COL, HIGH_COL, LOW_COL])
    ohlc["Date"] = pd.to_datetime(ohlc["Date"])
    ohlc = ohlc.set_index("Date").sort_index()

    close_full = ohlc[CLOSE_COL]
    high_full = ohlc[HIGH_COL]
    low_full = ohlc[LOW_COL]

    log_ret = _to_returns(close_full, kind=return_kind)

    model = MarkovRegression(
        log_ret, k_regimes=2, trend="c", switching_trend=False, switching_variance=True
    )
    res = model.fit()
    summary_text = str(res.summary())
    llf = res.llf

    sigma2 = [res.params[f"sigma2[{i}]"] for i in range(2)]
    low_var_state = int(np.argmin(sigma2))
    high_var_state = 1 - low_var_state

    smoothed = res.smoothed_marginal_probabilities
    variance_regime = np.where(smoothed[high_var_state] > 0.5, "high_var", "low_var")
    variance_df = pd.DataFrame(
        {
            "variance_regime": variance_regime,
            "prob_high_var_smoothed": smoothed[high_var_state].values,
        },
        index=log_ret.index,
    )

    transition = _regime_transition_lookup(res, low_var_state, high_var_state)
    prob_high_today = float(smoothed[high_var_state].iloc[-1])
    prob_low_today = 1.0 - prob_high_today
    prob_high_tomorrow = (
        prob_low_today * transition[("low_var", "high_var")]
        + prob_high_today * transition[("high_var", "high_var")]
    )

    close_cont = _continuous(close_full)
    high_cont = _continuous(high_full)
    low_cont = _continuous(low_full)

    tma = _triangular_ma(close_cont, TMA_WINDOW)
    # هشدار: عدد > NaN همیشه False برمی‌گرده (نه NaN)، پس np.where بدون این
    # فیکس، کل دوره‌ی warm-up ی TMA (~۲۵۰ روز اول) رو بی‌صدا "bearish" می‌کرد،
    # حتی اگه قیمت واقعاً صعودی بود. اینجا صریحاً NaN نگه داشته می‌شه تا اون
    # دوره از تحلیل حذف بشه (نه اشتباه برچسب بخوره).
    trend_regime = pd.Series(
        np.where(close_cont > tma, "bullish", "bearish"), index=close_cont.index
    )
    trend_regime[tma.isna()] = np.nan

    atr = _average_true_range(high_cont, low_cont, close_cont, ATR_WINDOW)
    trend_confirmed = _keltner_filter(close_cont, tma, trend_regime, atr, KELTNER_MULT)

    combined = variance_df.join(trend_confirmed.rename("trend_regime"), how="inner")
    combined["final_regime"] = combined.apply(
        lambda r: REGIME_MAP.get((r["trend_regime"], r["variance_regime"]), np.nan), axis=1
    )
    combined["days_in_regime"] = _days_in_state(combined["final_regime"])
    combined = combined.join(log_ret.rename("log_return"), how="inner")
    combined = combined.join(close_cont.rename("close"), how="left")
    combined = combined.join(tma.rename("tma"), how="left")

    stats = combined.groupby("final_regime")["log_return"].agg(
        mean_daily_return="mean", std_daily_return="std", n_days="count"
    )
    stats["mean_daily_return_pct"] = (stats["mean_daily_return"] * 100).round(4)
    stats["std_daily_return_pct"] = (stats["std_daily_return"] * 100).round(4)
    stats = stats[["n_days", "mean_daily_return_pct", "std_daily_return_pct"]]

    return {
        "summary_text": summary_text,
        "llf": llf,
        "sigma2_low": sigma2[low_var_state],
        "sigma2_high": sigma2[high_var_state],
        "combined": combined,
        "stats": stats,
        "n_obs": len(log_ret),
        "date_start": log_ret.index.min(),
        "date_end": log_ret.index.max(),
        "transition": transition,
        "prob_high_today": prob_high_today,
        "prob_high_tomorrow": prob_high_tomorrow,
    }


@st.cache_data(show_spinner="در حال محاسبه‌ی walk-forward...")
def fit_walkforward_point(db_path: str, mtime: float, return_kind: str, cutoff: int) -> dict:
    """
    مدل رو *از نو*، فقط با داده‌ی تا (آخرین روز - cutoff) فیت می‌کنه —
    یعنی cutoff روز آخر کلاً از ورودی مدل حذف می‌شن، نه فقط از نمایش.
    """
    ohlc = pd.read_csv(db_path, usecols=["Date", CLOSE_COL, HIGH_COL, LOW_COL])
    ohlc["Date"] = pd.to_datetime(ohlc["Date"])
    ohlc = ohlc.set_index("Date").sort_index()

    log_ret_full = _to_returns(ohlc[CLOSE_COL], kind=return_kind)
    ret_slice = log_ret_full.iloc[: len(log_ret_full) - cutoff] if cutoff > 0 else log_ret_full

    model = MarkovRegression(
        ret_slice, k_regimes=2, trend="c", switching_trend=False, switching_variance=True
    )
    res = model.fit()

    sigma2 = [res.params[f"sigma2[{i}]"] for i in range(2)]
    low_var_state = int(np.argmin(sigma2))
    high_var_state = 1 - low_var_state

    smoothed = res.smoothed_marginal_probabilities
    prob_high = float(smoothed[high_var_state].iloc[-1])
    prob_low = 1.0 - prob_high
    label = "high_var" if prob_high > 0.5 else "low_var"

    transition = _regime_transition_lookup(res, low_var_state, high_var_state)
    prob_high_next = prob_low * transition[("low_var", "high_var")] + prob_high * transition[("high_var", "high_var")]

    return {
        "date": ret_slice.index[-1],
        "label": label,
        "prob_high": prob_high,
        "prob_low": prob_low,
        "transition": transition,
        "prob_high_next": prob_high_next,
        "log_return": float(ret_slice.iloc[-1]),
    }


@st.cache_data(show_spinner=False)
def load_sector_prices(path: str, mtime: float) -> pd.DataFrame:
    available = pd.read_csv(path, nrows=0).columns
    cols = [c for c in SECTOR_COLUMNS if c in available]
    if not cols:
        return pd.DataFrame()
    df = pd.read_csv(path, usecols=["Date"] + cols)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _render_snapshot_block(container, title: str, date, var_label: str, trend_label: str,
                            prob_high: float, transition: dict, prob_high_next: float,
                            next_title: str, log_return: float) -> None:
    prob_this = prob_high if var_label == "high_var" else (1 - prob_high)
    if prob_this > 0.8:
        confidence = "🟢 قوی"
    elif prob_this < 0.6:
        confidence = "🟡 نامطمئن"
    else:
        confidence = "🔵 متوسط"

    final_regime = REGIME_MAP.get((trend_label, var_label), "نامشخص")

    container.markdown(f"**{title} — {date.date()}**")
    container.markdown(f"رژیم واریانس: `{var_label}` — {prob_this:.0%} ({confidence})")
    container.markdown(f"رژیم نهایی (۴تایی): **{final_regime}**")
    container.markdown(f"بازدهی واقعی همون روز: {log_return * 100:+.3f}%")
    container.caption(
        f"ماتریس انتقال (fit همین برش) — "
        f"low→low: {transition[('low_var','low_var')]:.1%} | "
        f"low→high: {transition[('low_var','high_var')]:.1%} | "
        f"high→low: {transition[('high_var','low_var')]:.1%} | "
        f"high→high: {transition[('high_var','high_var')]:.1%}"
    )
    container.markdown(f"پیش‌بینی برای **{next_title}**: احتمال پرنوسان‌بودن = **{prob_high_next:.0%}**")
    container.divider()


def render_asset_class_behaviour(combined: pd.DataFrame, sector_df: pd.DataFrame, sp500_stats: pd.DataFrame) -> None:
    """
    معادل بخش «Asset Class Behaviour» (Table 4) مقاله‌ی SSRN 3144169 —
    میانگین بازدهی هر شاخص، روی *کل* روزهایی که در طول تاریخچه در هر
    رژیم بودیم (نه فقط یک اپیزود)، برای مقایسه‌ی مستقیم با جدول مقاله.
    """
    st.markdown("### 📚 Asset Class Behaviour (معادل Table 4 مقاله)")
    st.caption(
        "میانگین بازدهی روزانه‌ی هر دارایی، شرطی بر رژیمی که آن روز در آن بودیم — "
        "روی کل تاریخچه (نه فقط اپیزود اخیر)."
    )

    if sector_df.empty:
        st.warning("هیچ‌کدوم از ستون‌های شاخص بخشی توی دیتابیس نیستن.")
        return

    rows = []

    sp500_row = {"دارایی": "SP500 (خودِ مدل)"}
    for regime in REGIME_ORDER:
        sp500_row[regime] = sp500_stats["mean_daily_return_pct"].get(regime, np.nan)
    rows.append(sp500_row)

    sector_ret = sector_df.apply(lambda s: _to_returns(s, kind="log"))
    for ticker, name in SECTOR_COLUMNS.items():
        if ticker not in sector_ret.columns:
            continue
        merged = combined[["final_regime"]].join(sector_ret[ticker].rename("ret"), how="inner")
        by_regime = merged.groupby("final_regime")["ret"].mean() * 100
        row = {"دارایی": f"{ticker} ({name})"}
        for regime in REGIME_ORDER:
            row[regime] = by_regime.get(regime, np.nan)
        rows.append(row)

    table = pd.DataFrame(rows).set_index("دارایی")
    st.dataframe(
        table.style.format("{:+.3f}%", na_rep="—").background_gradient(
            cmap="RdYlGn", axis=None, vmin=-0.15, vmax=0.15
        ),
        use_container_width=True,
    )


def render_current_episode_sectors(combined: pd.DataFrame, sector_df: pd.DataFrame) -> None:
    """بازدهی هر شاخص بخشی، فقط از شروع اپیزودِ رژیم فعلی تا امروز."""
    n_current = int(combined["days_in_regime"].iloc[-1])
    current_regime_name = combined["final_regime"].iloc[-1]
    start_idx = max(len(combined) - n_current, 0)
    start_date = combined.index[start_idx]
    end_date = combined.index[-1]

    st.markdown(f"### 🔥 عملکرد بخشی در رژیم فعلی — {current_regime_name}")
    st.caption(f"{n_current} روزه توی این رژیم هستیم — از {start_date.date()} تا {end_date.date()}")

    if sector_df.empty:
        st.warning("ستون‌های شاخص بخشی توی دیتابیس نیستن.")
        return

    idx = sector_df.index
    pos_start = idx.searchsorted(start_date)
    pos_base = max(pos_start - 1, 0)
    base_prices = sector_df.iloc[pos_base]
    end_prices = sector_df.loc[:end_date].iloc[-1]
    ret = ((end_prices / base_prices - 1) * 100).dropna().sort_values(ascending=False)

    if ret.empty:
        st.warning("داده‌ی کافی برای این بازه نیست.")
        return

    labels = [f"{t} ({SECTOR_COLUMNS.get(t, t)})" for t in ret.index]
    colors = ["#4caf50" if v >= 0 else "#d9534f" for v in ret.values]
    fig = go.Figure(go.Bar(
        x=ret.values, y=labels, orientation="h", marker_color=colors,
        text=[f"{v:+.1f}%" for v in ret.values], textposition="outside",
    ))
    fig.update_layout(
        template="plotly_dark", height=420,
        margin=dict(l=10, r=60, t=10, b=10),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True, key="model6_current_episode_sectors")


def render_regime_correlation(combined: pd.DataFrame, sector_df: pd.DataFrame) -> None:
    """معادل Figure 8 مقاله — ماتریس همبستگیِ بازدهی روزانه، جدا برای هر رژیم.

    توجه: این بخش فقط روزهایی رو حساب می‌کنه که هم SP500 هم حداقل یکی از
    ETFهای بخشی داده داشته باشن. چون بیشتر ETFهای بخشی (مثلاً XLC از ۲۰۱۸،
    XLRE از ۲۰۱۵، حتی XLK/XLF/... از دسامبر ۱۹۹۸) خیلی دیرتر از SP500 راه
    افتادن، اگه SP500 توی دیتابیس شما تاریخچه‌ی قدیمی‌تر داشته باشه، تعداد
    کل روزهای این بخش کمتر از باکس‌های «توزیع رژیم نهایی» بالای صفحه
    می‌شه — این طبیعیه (محدودیت داده، نه باگ)، برای همین صریح نشونش می‌دیم.
    """
    st.markdown("### 🔗 ماتریس همبستگی به‌ازای هر رژیم (معادل Figure 8 مقاله)")
    st.caption("همبستگی بازدهی روزانه‌ی SP500 و شاخص‌های بخشی، فقط روی روزهایی که در همون رژیم بودیم.")

    if sector_df.empty:
        st.warning("ستون‌های شاخص بخشی توی دیتابیس نیستن.")
        return

    sector_ret = sector_df.apply(lambda s: _to_returns(s, kind="log"))
    all_ret = sector_ret.join(combined["log_return"].rename("SP500"), how="inner")
    all_ret = all_ret.join(combined["final_regime"], how="inner")
    all_ret = all_ret.dropna(subset=["final_regime"])

    if all_ret.empty:
        st.warning("داده‌ی مشترکی بین SP500 و شاخص‌های بخشی پیدا نشد.")
        return

    st.caption(
        f"⚠️ این بخش محدود به بازه‌ایه که داده‌ی بخشی هم موجوده: "
        f"{all_ret.index.min().date()} تا {all_ret.index.max().date()} "
        f"({len(all_ret):,} روز) — کمتر از تاریخچه‌ی کامل SP500 در باکس‌های بالا، "
        f"چون بیشتر ETFهای بخشی (XLK/XLF/... از ۱۹۹۸، RSP از ۲۰۰۳، GDX از ۲۰۰۶، "
        f"XLRE از ۲۰۱۵، XLC از ۲۰۱۸) دیرتر از SP500 راه افتادن."
    )

    cols_order = ["SP500"] + [t for t in SECTOR_COLUMNS if t in sector_ret.columns]

    grid = st.columns(2)
    for i, regime in enumerate(REGIME_ORDER):
        subset = all_ret[all_ret["final_regime"] == regime][cols_order].dropna(axis=1, how="all")
        n = len(subset)
        with grid[i % 2]:
            if n < 30 or subset.shape[1] < 2:
                st.warning(f"{regime}: داده‌ی کافی نیست ({n} روز)")
                continue
            corr = subset.corr()
            fig = go.Figure(data=go.Heatmap(
                z=corr.values, x=list(corr.columns), y=list(corr.columns),
                colorscale="RdBu", zmid=0, zmin=-1, zmax=1,
                text=corr.round(2).values, texttemplate="%{text}",
            ))
            fig.update_layout(
                title=f"{regime} ({n} روز)",
                template="plotly_dark", height=420,
                margin=dict(l=10, r=10, t=40, b=10),
            )
            st.plotly_chart(fig, use_container_width=True, key=f"model6_corr_{regime}")


# ==========================================================================
# رابط کاربری
# ==========================================================================

def show() -> None:

    inject_global_style()

    st.markdown("# 📐 Model 6 — Markov-Switching Regime (SSRN 3144169)")
    st.caption("replication روش‌شناسی مقاله روی S&P500 — فقط نمایشی، هنوز به دیتابیس ذخیره نمی‌شه")

    with st.expander("⚠️ فرضیات صریح این مدل (چون خودِ مقاله مبهم بود)", expanded=False):
        st.markdown(
            """
            - لایه‌ی واریانس: `MarkovRegression` با `trend='c', switching_trend=False, switching_variance=True`، بدون جمله‌ی AR
            - TMA = SMA روی SMA (double smoothing ساده)
            - ATR واقعیه (از SP500_H/SP500_L/SP500)، میانگین ساده روی ۲۰ روز (نه smoothing وایلدر)
            - بازدهی فقط بین دو observation معتبر و متوالی (نه پرکردن جای خالی)
            - از **smoothed probability** استفاده شده (مناسب مطالعه‌ی تاریخی، نه فیچر زنده)
            """
        )

    if not os.path.isfile(DB_PATH):
        st.error(f"دیتابیس پیدا نشد:\n`{DB_PATH}`")
        return

    missing = [c for c in (CLOSE_COL, HIGH_COL, LOW_COL) if c not in pd.read_csv(DB_PATH, nrows=0).columns]
    if missing:
        st.error(f"این ستون‌ها توی دیتابیس نیستن: {missing}")
        return

    return_kind = st.radio(
        "نوع بازدهی",
        options=["log", "simple"],
        horizontal=True,
    )

    result = run_pipeline(DB_PATH, os.path.getmtime(DB_PATH), return_kind)

    # ---- خلاصه‌ی بازه ----
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("بازه‌ی داده", f"{result['date_start'].date()} → {result['date_end'].date()}")
    c2.metric("تعداد observation", f"{result['n_obs']:,}")
    c3.metric("sigma² (کم‌نوسان / پرنوسان)", f"{result['sigma2_low']:.5f} / {result['sigma2_high']:.5f}")
    c4.metric("نسبت واریانس", f"{result['sigma2_high'] / result['sigma2_low']:.2f}", help="مقاله: 4.50")
    st.caption(f"Log-Likelihood: {result['llf']:.3f}")

    st.divider()

    # ---- خروجی خام statsmodels + پنل walk-forward (کنار هم) ----
    st.markdown("### خروجی مدل Markov-Switching Variance + وضعیت معاملاتی")

    col_summary, col_panel = st.columns([1.3, 1])

    with col_summary:
        with st.expander("📄 res.summary() کامل", expanded=False):
            st.code(result["summary_text"], language=None)

    with col_panel:
        combined = result["combined"]

        today_date = combined.index[-1]
        today_var_label = combined["variance_regime"].iloc[-1]
        today_trend_label = combined["trend_regime"].iloc[-1]
        today_return = combined["log_return"].iloc[-1]
        _render_snapshot_block(
            st, "📍 امروز", today_date, today_var_label, today_trend_label,
            result["prob_high_today"], result["transition"], result["prob_high_tomorrow"],
            "فردا", today_return,
        )

        yesterday = fit_walkforward_point(DB_PATH, os.path.getmtime(DB_PATH), return_kind, 1)
        yesterday_trend_label = combined["trend_regime"].loc[yesterday["date"]]
        _render_snapshot_block(
            st, "📍 دیروز (بدون دیدن امروز)", yesterday["date"], yesterday["label"], yesterday_trend_label,
            yesterday["prob_high"], yesterday["transition"], yesterday["prob_high_next"],
            "امروز", yesterday["log_return"],
        )

        two_days_ago = fit_walkforward_point(DB_PATH, os.path.getmtime(DB_PATH), return_kind, 2)
        two_days_ago_trend_label = combined["trend_regime"].loc[two_days_ago["date"]]
        _render_snapshot_block(
            st, "📍 دو روز پیش (بدون دیدن دیروز/امروز)", two_days_ago["date"], two_days_ago["label"], two_days_ago_trend_label,
            two_days_ago["prob_high"], two_days_ago["transition"], two_days_ago["prob_high_next"],
            "دیروز", two_days_ago["log_return"],
        )

    st.divider()

    # ---- توزیع ۴ رژیم نهایی ----
    st.markdown("### توزیع رژیم نهایی")
    st.caption(
        f"روی کل تاریخچه‌ی SP500 توی دیتابیس ({result['date_start'].date()} تا {result['date_end'].date()}) — "
        "شاخص‌های بخشی معمولاً دیرتر شروع شدن، پس جدول‌های همبستگیِ پایین‌تر صفحه بازه‌ی کوتاه‌تری رو پوشش می‌دن."
    )
    counts = result["combined"]["final_regime"].value_counts()
    cols = st.columns(len(REGIME_MAP.values()))
    for col, name in zip(cols, REGIME_ORDER):
        n = int(counts.get(name, 0))
        col.markdown(
            f"""
            <div style="border:1px solid rgba(255,255,255,0.09);background:rgba(255,255,255,0.025);
                        border-radius:14px;padding:14px;text-align:center;">
                <div style="color:{REGIME_COLORS[name]};font-weight:700;">{name}</div>
                <div style="font-size:24px;font-weight:800;margin-top:4px;">{n:,}</div>
                <div style="font-size:12px;color:#8a8f98;">روز</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    sector_df = load_sector_prices(DB_PATH, os.path.getmtime(DB_PATH))

    # ---- عملکرد بخشی در رژیم فعلی ----
    render_current_episode_sectors(result["combined"], sector_df)

    st.divider()

    # ---- جدول آماری SP500 (معادل Table 3 مقاله) ----
    st.markdown("### آمار بازدهی هر رژیم — SP500 (معادل Table 3 مقاله)")
    st.dataframe(result["stats"], use_container_width=True)

    st.divider()

    # ---- Asset Class Behaviour (معادل Table 4 مقاله) ----
    render_asset_class_behaviour(result["combined"], sector_df, result["stats"])

    st.divider()

    # ---- ماتریس همبستگی به‌ازای هر رژیم (معادل Figure 8 مقاله) ----
    render_regime_correlation(result["combined"], sector_df)

    st.divider()

    # ---- نمودار قیمت + رنگ‌آمیزی رژیم ----
    st.markdown("### قیمت S&P500 با رنگ‌آمیزی رژیم")
    combined_plot = result["combined"].dropna(subset=["final_regime"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=combined_plot.index, y=combined_plot["close"], name="SP500 Close", line=dict(color="#e8e8e8", width=1))
    )
    fig.add_trace(
        go.Scatter(x=combined_plot.index, y=combined_plot["tma"], name="TMA (250d)", line=dict(color="#888", width=1, dash="dot"))
    )

    prev, seg_start = None, combined_plot.index[0]
    for date, regime in combined_plot["final_regime"].items():
        if regime != prev:
            if prev is not None:
                fig.add_vrect(x0=seg_start, x1=date, fillcolor=REGIME_COLORS[prev], opacity=0.25, line_width=0)
            seg_start, prev = date, regime
    fig.add_vrect(x0=seg_start, x1=combined_plot.index[-1], fillcolor=REGIME_COLORS[prev], opacity=0.25, line_width=0)

    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=1.08),
        yaxis_type="log",
    )
    st.plotly_chart(fig, use_container_width=True, key="model6_price_chart")

    st.caption("منبع: " + DB_PATH + " (read-only، هیچ‌چیز save نمی‌شه)")