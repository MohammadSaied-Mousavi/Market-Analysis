"""
regime_model1.py — مدل خالص Eco3min + نوکست Trimmed Mean PCE از CPI/PPI
==========================================================================
جایگزین مستقیم world_market/macroF/regime_model1.py

منابع روش‌شناسی رژیم:
    https://eco3min.fr/en/macro-financial-regimes/
    https://eco3min.fr/en/current-regime/
    https://eco3min.fr/en/macro-regime-classification-methodology/

==========================================================================
تغییرات نسبت به نسخهٔ قبلی
==========================================================================

۱) دیتابیس شما دیگر forward-filled نیست (خودتان گفتید «هر چی هست دادهٔ
   اصلیه»). برای همین خواندن داده اصلاح شد: برای هر ستون، ابتدا مقادیر
   NaN حذف می‌شوند (dropna) و بعد بر اساس ماه گروه‌بندی می‌شوند — این روش
   چه دیتابیستان ffill باشد چه raw/sparse، درست کار می‌کند.

۲) چون ستون‌های PCETRIM12M159SFRBDAL، SAHMREALTIME، و UNRATE را اضافه
   کردید، دیگر نیازی به جایگزین‌سازی نیست: این‌ها مستقیماً و عیناً همان
   سنجه‌های رسمی eco3min هستند. Sahm Rule هم دیگر دستی محاسبه نمی‌شود —
   مستقیم از SAHMREALTIME خوانده می‌شود.

۳) *** جدید *** نوکست Trimmed Mean PCE از CPI/PPI:
   چون PCETRIM حدود ۳ هفته دیرتر از CPI/PPI منتشر می‌شود، برای ماه(های)
   بسیار اخیر که هنوز Dallas Fed منتشر نکرده، یک رگرسیون OLS با پنجرهٔ
   غلتان زیر تخمین می‌زند:

       Trimmed_PCE_YoY(t) = β0 + β1·CoreCPI_YoY(t) + β2·CorePPI_YoY(t) + ε

   - برای هر ماهی که عدد رسمی PCETRIM از قبل موجود است (یعنی تقریباً کل
     تاریخچه)، از همان عدد واقعی استفاده می‌شود — صد‌درصد وفادار به
     eco3min، هیچ تخمینی درکار نیست.
   - فقط برای ۱ الی ۲ ماه انتهایی که هنوز منتشر نشده، رگرسیون بالا
     (فیت‌شده روی آخرین NOWCAST_TRAIN_WINDOW_MONTHS ماه دادهٔ رسمی)
     یک تخمین (نوکست) تولید می‌کند.
   - یک بک‌تست walk-forward (کاملاً out-of-sample، بدون نگاه به آینده)
     هم جداگانه اجرا می‌شود تا خطای واقعی تاریخی این نوکست را نشان دهد
     (نه صرفاً برازش خوش‌بینانهٔ درون‌نمونه‌ای).

نیازمندی‌های دیتابیس برای فعال‌شدن نوکست:
    ستون ضروری:    PPIFES        (PPI Final Demand Less Foods and Energy)
    ستون اختیاری:  WPSFD49116    (PPI Final Demand Less Foods, Energy,
                                   and Trade Services — دقت را کمی بهتر
                                   می‌کند، الزامی نیست)
    اگر PPIFES در دیتابیس نباشد، نوکست به‌طور خودکار غیرفعال می‌ماند و
    فقط عدد رسمی (هرجا موجود بود) نمایش داده می‌شود — بدون خطا.

نیازمندی‌ها: streamlit, pandas, numpy, plotly
==========================================================================
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from theme import inject_global_style

# ==========================================================================
# 0) تنظیمات
# ==========================================================================

_CANDIDATE_DB_PATHS = [
    Path(__file__).resolve().parents[2] / "database" / "macro_database.csv",
    Path(__file__).resolve().parents[1] / "database" / "macro_database.csv",
    Path("database/macro_database.csv"),
]

THRESH = {
    "G_PLUS": 0.10,
    "G_MINUS": -0.50,
    "I_PLUS": 2.75,
    "I_MINUS": 1.50,
    "SAHM_TRIGGER": 0.50,
    "HYSTERESIS_MONTHS": 2,
}

# پنجرهٔ آموزش رگرسیون نوکست (ماه) — چرا ۹۶: به‌اندازهٔ کافی بزرگ برای
# پایداری آماری، ولی به‌اندازهٔ کافی کوچک که رابطهٔ CPI/PPI/PCE با گذر
# زمان (تجدید وزن‌های BEA/BLS) بیش‌ازحد کهنه نشود.
NOWCAST_TRAIN_WINDOW_MONTHS = 96
NOWCAST_MIN_TRAIN_MONTHS = 24

REGIME_GRID_NAMES = {
    ("G+", "I-"): "Disinflationary Expansion",
    ("G+", "I="): "Balanced Expansion",
    ("G+", "I+"): "Overheating",
    ("G=", "I-"): "Transition",
    ("G=", "I="): "Transition",
    ("G=", "I+"): "Inflationary Pressure",
    ("G-", "I-"): "Disinflationary Contraction",
    ("G-", "I="): "Slowdown",
    ("G-", "I+"): "Stagflation",
}

REGIME_COLORS = {
    "Disinflationary Expansion": "#2e7d32",
    "Balanced Expansion": "#66bb6a",
    "Overheating": "#f9a825",
    "Inflationary Pressure": "#ef6c00",
    "Stagflation": "#c62828",
    "Slowdown": "#8d6e63",
    "Disinflationary Contraction": "#1565c0",
    "Transition": "#9e9e9e",
}


# ==========================================================================
# 1) خواندن داده — فقط خواندنی؛ سازگار با دیتابیس raw (بدون forward-fill)
# ==========================================================================

def _find_db_path() -> Path:
    for p in _CANDIDATE_DB_PATHS:
        if p.exists():
            return p
    raise FileNotFoundError(
        "macro_database.csv پیدا نشد. مسیرهای بررسی‌شده:\n" +
        "\n".join(str(p) for p in _CANDIDATE_DB_PATHS) +
        "\nاگر ساختار پوشه‌بندی شما فرق دارد، مقدار _CANDIDATE_DB_PATHS را در "
        "ابتدای این فایل ویرایش کنید."
    )


# @st.cache_data(ttl=3600, show_spinner="در حال خواندن دیتابیس ماکرو (فقط‌خواندنی)...")
def load_monthly_data() -> pd.DataFrame:
    """
    فقط با pandas.read_csv می‌خواند. چون دیتابیس شما raw است (نه ffilled)،
    برای هر ستون جداگانه ابتدا NaNها حذف می‌شوند و بعد بر اساس ماه گروه‌بندی
    می‌شوند (آخرین مقدار موجود در آن ماه). این روش هم برای دادهٔ raw/sparse
    درست کار می‌کند هم اگر فردا ستونی را ffilled ذخیره کردید.
    """
    path = _find_db_path()
    df = pd.read_csv(path, parse_dates=["Date"])
    df = df.sort_values("Date").set_index("Date")

    required = ["CFNAI", "PCETRIM12M159SFRBDAL", "CPILFESL", "NFCI", "SAHMREALTIME"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"ستون(های) ضروری در دیتابیس یافت نشد: {missing}")

    optional = [c for c in ["PPIFES", "WPSFD49116", "UNRATE"] if c in df.columns]

    monthly_cols = {}
    for col in required + optional:
        monthly_cols[col] = df[col].dropna().resample("MS").last()

    monthly = pd.concat(monthly_cols, axis=1)
    return monthly


# ==========================================================================
# 2) نوکست Trimmed Mean PCE از Core CPI/PPI (بریج رگرسیون OLS)
# ==========================================================================

def _fit_ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """OLS ساده: کمترین مربعات با numpy.linalg.lstsq. ستون اول X باید ۱ (عرض از مبدأ) باشد."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def _build_predictor_frame(monthly: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Core CPI/PPI YoY را از سطح شاخص‌ها می‌سازد و لیست ستون‌های پیش‌بین موجود را برمی‌گرداند."""
    df = monthly.copy()
    predictor_cols = []

    df["CORE_CPI_YOY"] = df["CPILFESL"].pct_change(12) * 100
    predictor_cols.append("CORE_CPI_YOY")

    if "PPIFES" in df.columns:
        df["CORE_PPI_YOY"] = df["PPIFES"].pct_change(12) * 100
        predictor_cols.append("CORE_PPI_YOY")

    if "WPSFD49116" in df.columns:
        df["CORE_PPI_EXTRADE_YOY"] = df["WPSFD49116"].pct_change(12) * 100
        predictor_cols.append("CORE_PPI_EXTRADE_YOY")

    return df, predictor_cols


def nowcast_latest_gap(monthly: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    برای ماه(های) انتهایی که PCETRIM12M159SFRBDAL هنوز NaN است (چون منتشر
    نشده)، با رگرسیون OLS روی آخرین NOWCAST_TRAIN_WINDOW_MONTHS ماه دادهٔ
    رسمی، یک تخمین می‌سازد. برای همهٔ ماه‌های دیگر عدد رسمی دست‌نخورده
    باقی می‌ماند.
    خروجی: (دیتافریم به‌روزشده با ستون INFLATION_MEASURE و Inflation_Is_Nowcast،
             دیکشنری تشخیصی شامل وضعیت فعال/غیرفعال بودن نوکست و R2/MAE فیت اخیر)
    """
    y_col = "PCETRIM12M159SFRBDAL"
    df, predictor_cols = _build_predictor_frame(monthly)

    df["INFLATION_MEASURE"] = df[y_col]
    df["Inflation_Is_Nowcast"] = False

    diagnostics = {"nowcast_enabled": "PPIFES" in monthly.columns, "fit_r2": np.nan, "fit_mae": np.nan,
                    "predictors_used": predictor_cols, "n_train": 0}

    if not diagnostics["nowcast_enabled"]:
        return df, diagnostics

    for i in range(len(df)):
        if pd.notna(df[y_col].iloc[i]):
            continue
        x_row = df[predictor_cols].iloc[i]
        if x_row.isna().any():
            continue

        train = df.iloc[max(0, i - NOWCAST_TRAIN_WINDOW_MONTHS):i].dropna(subset=[y_col] + predictor_cols)
        if len(train) < NOWCAST_MIN_TRAIN_MONTHS:
            continue

        X_train = np.column_stack([np.ones(len(train))] + [train[c].values for c in predictor_cols])
        y_train = train[y_col].values
        beta = _fit_ols(X_train, y_train)

        y_fit = X_train @ beta
        ss_res = np.sum((y_train - y_fit) ** 2)
        ss_tot = np.sum((y_train - y_train.mean()) ** 2)
        diagnostics["fit_r2"] = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        diagnostics["fit_mae"] = float(np.mean(np.abs(y_train - y_fit)))
        diagnostics["n_train"] = len(train)

        x_pred = np.array([1.0] + list(x_row.values))
        pred = float(x_pred @ beta)

        df.iloc[i, df.columns.get_loc("INFLATION_MEASURE")] = pred
        df.iloc[i, df.columns.get_loc("Inflation_Is_Nowcast")] = True

    return df, diagnostics


# @st.cache_data(ttl=3600, show_spinner="در حال اجرای بک‌تست نوکست تورم...")
def walkforward_backtest(monthly: pd.DataFrame) -> pd.DataFrame:
    """
    بک‌تست کاملاً out-of-sample (walk-forward): برای هر ماهی که عدد رسمی
    را از قبل داریم، وانمود می‌کنیم آن را نمی‌دانیم و فقط با دادهٔ *قبل*
    از آن ماه، یک نوکست می‌سازیم؛ سپس با عدد واقعی مقایسه می‌کنیم. این
    صادقانه‌ترین سنجهٔ دقت نوکست است، نه صرفاً برازش درون‌نمونه‌ای خوش‌بینانه.
    """
    y_col = "PCETRIM12M159SFRBDAL"
    if "PPIFES" not in monthly.columns:
        return pd.DataFrame(columns=["Actual", "Nowcast", "Error"])

    df, predictor_cols = _build_predictor_frame(monthly)
    rows = []
    for i in range(len(df)):
        if pd.isna(df[y_col].iloc[i]):
            continue
        x_row = df[predictor_cols].iloc[i]
        if x_row.isna().any():
            continue
        train = df.iloc[max(0, i - NOWCAST_TRAIN_WINDOW_MONTHS):i].dropna(subset=[y_col] + predictor_cols)
        if len(train) < NOWCAST_MIN_TRAIN_MONTHS:
            continue
        X_train = np.column_stack([np.ones(len(train))] + [train[c].values for c in predictor_cols])
        y_train = train[y_col].values
        beta = _fit_ols(X_train, y_train)
        x_pred = np.array([1.0] + list(x_row.values))
        pred = float(x_pred @ beta)
        rows.append({"date": df.index[i], "Actual": df[y_col].iloc[i], "Nowcast": pred})

    if not rows:
        return pd.DataFrame(columns=["Actual", "Nowcast", "Error"])

    bt = pd.DataFrame(rows).set_index("date")
    bt["Error"] = bt["Nowcast"] - bt["Actual"]
    return bt


# ==========================================================================
# 3) محاسبهٔ محورها و طبقه‌بندی رژیم
# ==========================================================================

def compute_regime(monthly: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    with_inflation, nowcast_diag = nowcast_latest_gap(monthly)
    out = with_inflation.copy()

    out["CFNAI_MA3"] = out["CFNAI"].rolling(3, min_periods=1).mean()

    def g_level(v):
        if pd.isna(v):
            return np.nan
        if v > THRESH["G_PLUS"]:
            return "G+"
        if v < THRESH["G_MINUS"]:
            return "G-"
        return "G="

    def i_level(v):
        if pd.isna(v):
            return np.nan
        if v > THRESH["I_PLUS"]:
            return "I+"
        if v < THRESH["I_MINUS"]:
            return "I-"
        return "I="

    out["G_level_raw"] = out["CFNAI_MA3"].apply(g_level)
    out["I_level_raw"] = out["INFLATION_MEASURE"].apply(i_level)

    # ماشهٔ فوری Sahm Rule — مستقیم از ستون واقعی SAHMREALTIME، بدون محاسبهٔ دستی
    sahm_trigger = out["SAHMREALTIME"] >= THRESH["SAHM_TRIGGER"]

    out["G_level"] = _apply_hysteresis(out["G_level_raw"], sahm_trigger, THRESH["HYSTERESIS_MONTHS"])
    out["I_level"] = _apply_hysteresis(out["I_level_raw"], pd.Series(False, index=out.index), THRESH["HYSTERESIS_MONTHS"])

    out["Regime"] = [REGIME_GRID_NAMES.get((g, i), np.nan) for g, i in zip(out["G_level"], out["I_level"])]

    def financial_state(v):
        if pd.isna(v):
            return np.nan
        if v <= -0.5:
            return "accommodating"
        if v < 0:
            return "mildly_accommodating"
        if v < 0.5:
            return "neutral"
        return "tight"

    out["Financial_state"] = out["NFCI"].apply(financial_state)
    out["Days_in_regime"] = _days_in_state(out["Regime"])
    out["Days_in_financial_state"] = _days_in_state(out["Financial_state"])

    return out, nowcast_diag


def _apply_hysteresis(raw_series: pd.Series, hard_gate: pd.Series, n_months: int) -> pd.Series:
    current, pending, pending_count = None, None, 0
    values, hard = raw_series.tolist(), hard_gate.tolist()
    result = []
    for i, v in enumerate(values):
        if hard[i]:
            current = "G-"
            pending, pending_count = None, 0
            result.append(current)
            continue
        if current is None:
            current = v
            result.append(current)
            continue
        if pd.isna(v):
            result.append(current)
            continue
        if v == current:
            pending, pending_count = None, 0
            result.append(current)
        else:
            if v == pending:
                pending_count += 1
            else:
                pending, pending_count = v, 1
            if pending_count >= n_months:
                current = pending
                pending, pending_count = None, 0
            result.append(current)
    return pd.Series(result, index=raw_series.index)


def _days_in_state(s: pd.Series) -> pd.Series:
    counts, run, prev = [], 0, None
    for v in s.tolist():
        if pd.isna(v):
            run = 0
        elif v == prev:
            run += 1
        else:
            run = 1
        counts.append(run)
        prev = v if pd.notna(v) else prev
    return pd.Series(counts, index=s.index)


def get_reference_row(df: pd.DataFrame) -> pd.Series:
    valid = df.dropna(subset=["CFNAI_MA3", "INFLATION_MEASURE"])
    return valid.iloc[-1] if not valid.empty else df.iloc[-1]


# ==========================================================================
# 4) رابط کاربری Streamlit
# ==========================================================================

def show():
    inject_global_style()
    st.markdown("# 📊 US Macro Regime — Eco3min Methodology")
    st.caption("Growth (CFNAI) × Inflation (Trimmed Mean PCE) — دقیقاً طبق چارچوب eco3min.fr")

    try:
        monthly_raw = load_monthly_data()
    except (FileNotFoundError, KeyError) as e:
        st.error(str(e))
        return

    df, nowcast_diag = compute_regime(monthly_raw)
    ref = get_reference_row(df)
    is_lagged = ref.name != df.index[-1]

    if is_lagged:
        months_behind = (df.index[-1].to_period("M") - ref.name.to_period("M")).n
        st.warning(
            f"⚠️ داده‌های ماه(های) اخیر هنوز کامل نیستند. این گزارش مربوط به "
            f"آخرین ماه دارای دادهٔ کامل (رسمی یا نوکست) است: **{ref.name.strftime('%B %Y')}** "
            f"({months_behind} ماه عقب‌تر از آخرین ردیف دیتابیس)."
        )

    # --- وضعیت منبع تورم ماه مرجع (رسمی یا نوکست) ---
    if bool(ref.get("Inflation_Is_Nowcast", False)):
        st.info(
            f"🔮 **نوکست فعال برای {ref.name.strftime('%B %Y')}**: عدد رسمی "
            f"Trimmed Mean PCE هنوز از Dallas Fed منتشر نشده؛ مقدار نمایش‌داده‌شده "
            f"({ref['INFLATION_MEASURE']:.2f}%) تخمینی از رگرسیون Core CPI/PPI است "
            f"(R² درون‌نمونه‌ای فیت اخیر: {nowcast_diag['fit_r2']:.2f}، با "
            f"{nowcast_diag['n_train']} ماه دادهٔ آموزشی)."
        )
    else:
        st.success(f"✅ برای {ref.name.strftime('%B %Y')} عدد رسمی Trimmed Mean PCE موجود است (بدون نوکست).")

    with st.expander("ℹ️ جزئیات فنی نوکست تورم و محدودیت‌ها"):
        if nowcast_diag["nowcast_enabled"]:
            st.markdown(
                f"- **پیش‌بینی‌کننده‌های فعال:** {', '.join(nowcast_diag['predictors_used'])}\n"
                f"- **پنجرهٔ آموزش:** آخرین {NOWCAST_TRAIN_WINDOW_MONTHS} ماه دادهٔ رسمی (رگرسیون هر بار دوباره فیت می‌شود)\n"
                "- این نوکست فقط برای ماه(های) انتهایی که Dallas Fed هنوز منتشر نکرده استفاده می‌شود؛ "
                "برای تمام تاریخچهٔ قبلی، عدد رسمی و دقیق eco3min بدون تغییر باقی می‌ماند.\n"
                "- این یک **تخمین آماری خوب** است، نه معادل صددرصدی عدد رسمی — به بخش بک‌تست پایین صفحه نگاه کنید."
            )
        else:
            st.markdown(
                "- نوکست غیرفعال است چون ستون **PPIFES** در دیتابیس شما پیدا نشد.\n"
                "- برای فعال‌سازی، ستون `PPIFES` (PPI Final Demand Less Foods and Energy) "
                "را به دیتابیس اضافه کنید؛ اختیاری: `WPSFD49116` هم دقت را کمی بهتر می‌کند."
            )

    # --- کارت‌های رژیم فعلی ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CURRENT REGIME", ref["Regime"])
    c2.metric("CFNAI-MA3 (Growth)", f"{ref['CFNAI_MA3']:+.3f}", help="G+ اگر بیش از +0.10 ، G- اگر کمتر از -0.50")
    c3.metric("Trimmed Mean PCE", f"{ref['INFLATION_MEASURE']:.2f}%", help="I+ اگر بیش از 2.75% ، I- اگر کمتر از 1.50%")
    c4.metric("Days in Regime", int(ref["Days_in_regime"]))

    st.markdown(
        f"**Financial Conditions (NFCI, context — طبق eco3min جزو نام‌گذاری رژیم نیست):** "
        f"`{ref['Financial_state']}` — {int(ref['Days_in_financial_state'])} ماه در همین وضعیت"
    )

    # --- گرید نام‌گذاری رژیم ۳×۳ ---
    st.markdown("### Regime Classification Grid")
    grid_layout = [
        ("G+", "I-", "Disinflationary Expansion"), ("G+", "I=", "Balanced Expansion"), ("G+", "I+", "Overheating"),
        ("G=", "I-", "Transition"), ("G=", "I=", "Transition"), ("G=", "I+", "Inflationary Pressure"),
        ("G-", "I-", "Disinflationary Contraction"), ("G-", "I=", "Slowdown"), ("G-", "I+", "Stagflation"),
    ]
    grid_cols = st.columns(3)
    for idx, (g, i, name) in enumerate(grid_layout):
        col = grid_cols[idx % 3]
        is_current = (g == ref["G_level"] and i == ref["I_level"])
        color = REGIME_COLORS.get(name, "#888")
        border = f"2px solid {color}" if is_current else "1px solid #333"
        bg = color + "22" if is_current else "#111"
        badge = '<span style="float:right;font-size:10px;background:#ffffff22;padding:1px 6px;border-radius:5px;">CURRENT</span>' if is_current else ""
        col.markdown(f"""
        <div style="border:{border};background:{bg};border-radius:8px;padding:10px;margin-bottom:8px;text-align:center;">
            <div style="color:{color};font-weight:700;">{name}{badge}</div>
            <div style="color:#888;font-size:11px;">[{g} , {i}]</div>
        </div>
        """, unsafe_allow_html=True)

    # --- نمودار خط‌زمانی رژیم + CFNAI/Inflation ---
    st.markdown("### Regime Timeline")
    plotdf = df.dropna(subset=["Regime"])

    # چقدر پررنگ باشند نوارهای پس‌زمینه — این عدد را برای کم/زیاد کردن شدت رنگ عوض کنید
    REGIME_BAND_OPACITY = 0.7

    if not plotdf.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=plotdf.index, y=plotdf["CFNAI_MA3"], name="CFNAI-MA3 (Growth)",
                                  line=dict(color="#2f9bd6", width=2)))
        fig.add_trace(go.Scatter(x=plotdf.index, y=plotdf["INFLATION_MEASURE"], name="Trimmed Mean PCE (%)",
                                  line=dict(color="#e8a33d", width=2), yaxis="y2"))

        nowcast_pts = plotdf[plotdf["Inflation_Is_Nowcast"]]
        if not nowcast_pts.empty:
            fig.add_trace(go.Scatter(x=nowcast_pts.index, y=nowcast_pts["INFLATION_MEASURE"],
                                      name="Nowcast point", mode="markers",
                                      marker=dict(color="#ff5252", size=9, symbol="diamond"), yaxis="y2"))

        shapes = []
        prev, seg_start = None, plotdf.index[0]
        for date, regime in plotdf["Regime"].items():
            if regime != prev:
                if prev is not None:
                    shapes.append(dict(type="rect", xref="x", yref="paper", x0=seg_start, x1=date,
                                        y0=0, y1=1, fillcolor=REGIME_COLORS.get(prev, "#888"),
                                        opacity=REGIME_BAND_OPACITY, line_width=0))
                seg_start, prev = date, regime
        if prev is not None:
            shapes.append(dict(type="rect", xref="x", yref="paper", x0=seg_start, x1=plotdf.index[-1],
                                y0=0, y1=1, fillcolor=REGIME_COLORS.get(prev, "#888"),
                                opacity=REGIME_BAND_OPACITY, line_width=0))

        # --- ترفند: shape های plotly خودشان در legend نمی‌آیند؛ برای همین یک
        # trace نامرئی (بدون هیچ نقطهٔ واقعی) برای هر رژیمی که در این بازه
        # واقعاً دیده می‌شود اضافه می‌کنیم، فقط تا در legend نمایش داده شود.
        regimes_present = plotdf["Regime"].unique().tolist()
        for regime in regimes_present:
            color = REGIME_COLORS.get(regime, "#888")
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="markers",
                marker=dict(size=14, color=color, symbol="square", opacity=REGIME_BAND_OPACITY + 0.3),
                name=regime, showlegend=True,
            ))

        fig.update_layout(
            template="plotly_dark", height=460, shapes=shapes,
            yaxis=dict(title="CFNAI-MA3"),
            yaxis2=dict(title="Trimmed Mean PCE (%)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.18, font=dict(size=11)),
            margin=dict(t=60, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- راهنمای رنگی اضافه زیر نمودار (خیلی واضح‌تر، همیشه قابل‌خواندن) ---
        legend_html = "<div style='display:flex;flex-wrap:wrap;gap:14px;margin-top:-10px;margin-bottom:10px;'>"
        for regime in regimes_present:
            color = REGIME_COLORS.get(regime, "#888")
            legend_html += (
                f"<div style='display:flex;align-items:center;gap:6px;'>"
                f"<span style='width:14px;height:14px;background:{color};border-radius:3px;display:inline-block;'></span>"
                f"<span style='font-size:13px;color:#ddd;'>{regime}</span></div>"
            )
        legend_html += "</div>"
        st.markdown(legend_html, unsafe_allow_html=True)
        st.caption(f"شدت رنگ نوارهای پس‌زمینه (opacity) الان {REGIME_BAND_OPACITY} است — برای پررنگ‌تر/کم‌رنگ‌تر کردن، مقدار REGIME_BAND_OPACITY را در کد بالای همین بخش تغییر دهید (بین 0 تا 1).")

    # --- تاریخچهٔ ۱۲ ماه اخیر ---
    st.markdown("### Last 12 Months")
    hist = plotdf[["G_level", "I_level", "Regime", "Financial_state", "Inflation_Is_Nowcast"]].tail(12).copy()
    hist.index = hist.index.strftime("%Y-%m")
    st.dataframe(hist, use_container_width=True)

    # --- درصد زمان در هر رژیم ---
    st.markdown("### Time Spent in Each Regime (Full History)")
    if not plotdf.empty:
        dist = (plotdf["Regime"].value_counts(normalize=True) * 100).round(1)
        st.bar_chart(dist)

    # --- بک‌تست صادقانهٔ نوکست (walk-forward, out-of-sample) ---
    st.markdown("### 🔬 Nowcast Backtest (Walk-Forward, Out-of-Sample)")
    bt = walkforward_backtest(monthly_raw)
    if bt.empty:
        st.caption("بک‌تست غیرفعال (ستون PPIFES در دیتابیس نیست).")
    else:
        mae = bt["Error"].abs().mean()
        ss_res = (bt["Error"] ** 2).sum()
        ss_tot = ((bt["Actual"] - bt["Actual"].mean()) ** 2).sum()
        r2_oos = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

        bcol1, bcol2 = st.columns(2)
        bcol1.metric("MAE (خطای مطلق میانگین، واحد درصد)", f"{mae:.2f}")
        bcol2.metric("R² خارج از نمونه (Out-of-Sample)", f"{r2_oos:.2f}")

        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=bt.index, y=bt["Actual"], name="Actual (رسمی)", line=dict(color="#66bb6a")))
        fig_bt.add_trace(go.Scatter(x=bt.index, y=bt["Nowcast"], name="Nowcast (walk-forward)",
                                     line=dict(color="#ff5252", dash="dot")))
        fig_bt.update_layout(template="plotly_dark", height=350, margin=dict(t=20, b=20),
                              legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig_bt, use_container_width=True)
        st.caption(
            "این بک‌تست کاملاً out-of-sample است: برای هر ماه، فقط از داده‌های *قبل* از آن ماه "
            "برای فیت رگرسیون استفاده شده — دقیقاً همان چیزی که در لحظهٔ واقعی نوکست در اختیار داشتید."
        )

    st.caption(
        "منبع داده: macro_database.csv (فقط‌خواندنی) | روش‌شناسی رژیم: eco3min.fr | "
        f"آخرین ردیف دیتابیس: {df.index[-1].strftime('%Y-%m-%d')}"
    )