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

REGIME_COLORS = {
    "Advance": "#4caf50",
    "Accumulation": ACCENT,
    "Decline": "#d9534f",
    "Distribution": "#4a90d9",
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


def _regime_transition_lookup(res, low_var_state: int, high_var_state: int) -> dict:
    """
    p[i->j] در statsmodels یعنی احتمال گذار *از* رژیم i *به* رژیم j
    (تأییدشده از مستندات رسمی). این رو به یه دیکشنری با کلید
    ("low_var"/"high_var", "low_var"/"high_var") تبدیل می‌کنه تا
    مستقل از اینکه کدوم state داخلی (۰ یا ۱) کم‌نوسانه، قابل‌استفاده
    باشه.
    """
    p00 = res.params["p[0->0]"]  # P(بعدی=۰ | قبلی=۰)
    p10 = res.params["p[1->0]"]  # P(بعدی=۰ | قبلی=۱)
    raw = {
        (0, 0): p00,
        (0, 1): 1 - p00,
        (1, 0): p10,
        (1, 1): 1 - p10,
    }
    label = {low_var_state: "low_var", high_var_state: "high_var"}
    return {(label[frm], label[to]): prob for (frm, to), prob in raw.items()}


def _one_step_forecast(prob_high_today: float, transition: dict) -> float:
    """با احتمال فعلی + ماتریس انتقال، احتمال پرنوسان بودنِ روز بعد رو حساب می‌کنه."""
    prob_low_today = 1 - prob_high_today
    return (
        prob_low_today * transition[("low_var", "high_var")]
        + prob_high_today * transition[("high_var", "high_var")]
    )


@st.cache_data(show_spinner="در حال fit والک‌فوروارد...")
def fit_walkforward_point(db_path: str, mtime: float, return_kind: str, cutoff: int) -> dict:
    """
    یه fit کاملاً جدا و مستقل، فقط با داده‌ی تا (آخرین روز - cutoff).
    یعنی برای cutoff=1 (دیروز)، مدل اصلاً داده‌ی امروز رو نمی‌بینه؛
    برای cutoff=2 (دو روز پیش)، نه دیروز نه امروز رو نمی‌بینه.
    """
    ohlc = pd.read_csv(db_path, usecols=["Date", CLOSE_COL])
    ohlc["Date"] = pd.to_datetime(ohlc["Date"])
    ohlc = ohlc.set_index("Date").sort_index()

    log_ret_full = _to_returns(ohlc[CLOSE_COL], kind=return_kind)
    ret_slice = log_ret_full.iloc[: len(log_ret_full) - cutoff]

    model = MarkovRegression(
        ret_slice, k_regimes=2, trend="c", switching_trend=False, switching_variance=True
    )
    res = model.fit()

    sigma2 = [res.params[f"sigma2[{i}]"] for i in range(2)]
    low_var_state = int(np.argmin(sigma2))
    high_var_state = 1 - low_var_state

    smoothed = res.smoothed_marginal_probabilities
    prob_high = float(smoothed[high_var_state].iloc[-1])  # آخرین نقطه‌ی همین برش؛ smoothed=filtered اینجا
    label = "high_var" if prob_high > 0.5 else "low_var"

    transition = _regime_transition_lookup(res, low_var_state, high_var_state)
    prob_high_next = _one_step_forecast(prob_high, transition)

    return {
        "date": ret_slice.index[-1],
        "label": label,
        "prob_high": prob_high,
        "prob_low": 1 - prob_high,
        "transition": transition,
        "prob_high_next": prob_high_next,
        "prob_low_next": 1 - prob_high_next,
        "log_return": float(ret_slice.iloc[-1]),
    }


# ==========================================================================
# پایپ‌لاین کامل — کش‌شده با mtime (بدون آندرلاین، تا واقعاً در هش
# محاسبه بشه و با تغییر فایل invalidate بشه). همیشه روی کل تاریخچه.
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
    trend_regime = pd.Series(
        np.where(close_cont > tma, "bullish", "bearish"), index=close_cont.index
    )

    atr = _average_true_range(high_cont, low_cont, close_cont, ATR_WINDOW)
    trend_confirmed = _keltner_filter(close_cont, tma, trend_regime, atr, KELTNER_MULT)

    combined = variance_df.join(trend_confirmed.rename("trend_regime"), how="inner")
    combined["final_regime"] = combined.apply(
        lambda r: REGIME_MAP.get((r["trend_regime"], r["variance_regime"]), np.nan), axis=1
    )
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
    برای cutoff=1 (دیروز، بدون دیدن امروز) و cutoff=2 (دو روز پیش،
    بدون دیدن دیروز/امروز) استفاده می‌شه. cutoff=0 نیازی نداره چون
    دقیقاً همون run_pipeline اصلیه.
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
    prob_high = float(smoothed[high_var_state].iloc[-1])  # آخرین نقطه‌ی همین برش -> smoothed=filtered
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

        # امروز — از همون run_pipeline اصلی، بدون فیت مجدد
        today_date = combined.index[-1]
        today_var_label = combined["variance_regime"].iloc[-1]
        today_trend_label = combined["trend_regime"].iloc[-1]
        today_return = combined["log_return"].iloc[-1]
        _render_snapshot_block(
            st, "📍 امروز", today_date, today_var_label, today_trend_label,
            result["prob_high_today"], result["transition"], result["prob_high_tomorrow"],
            "فردا", today_return,
        )

        # دیروز و دو روز پیش — با فیت کاملاً جداگانه (walk-forward واقعی)
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
    counts = result["combined"]["final_regime"].value_counts()
    cols = st.columns(len(REGIME_MAP.values()))
    for col, name in zip(cols, ["Advance", "Accumulation", "Decline", "Distribution"]):
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

    # ---- جدول آماری (معادل Table 3 مقاله) ----
    st.markdown("### آمار بازدهی هر رژیم (معادل Table 3 مقاله)")
    st.dataframe(result["stats"], use_container_width=True)

    st.divider()

    # ---- نمودار قیمت + رنگ‌آمیزی رژیم ----
    st.markdown("### قیمت S&P500 با رنگ‌آمیزی رژیم")
    combined = result["combined"].dropna(subset=["final_regime"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=combined.index, y=combined["close"], name="SP500 Close", line=dict(color="#e8e8e8", width=1))
    )
    fig.add_trace(
        go.Scatter(x=combined.index, y=combined["tma"], name="TMA (250d)", line=dict(color="#888", width=1, dash="dot"))
    )

    prev, seg_start = None, combined.index[0]
    for date, regime in combined["final_regime"].items():
        if regime != prev:
            if prev is not None:
                fig.add_vrect(x0=seg_start, x1=date, fillcolor=REGIME_COLORS[prev], opacity=0.25, line_width=0)
            seg_start, prev = date, regime
    fig.add_vrect(x0=seg_start, x1=combined.index[-1], fillcolor=REGIME_COLORS[prev], opacity=0.25, line_width=0)

    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=1.08),
        yaxis_type="log",
    )
    st.plotly_chart(fig, use_container_width=True, key="model6_price_chart")

    st.caption("منبع: " + DB_PATH + " (read-only، هیچ‌چیز save نمی‌شه)")