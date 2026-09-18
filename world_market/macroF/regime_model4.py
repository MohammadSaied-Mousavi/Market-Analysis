"""
regime_model2.py — بازطراحی بر مبنای اصول مقالات Prometheus Research
==========================================================================
تغییرات نسبت به نسخه‌ی قبلی (و چرا):

۱) گرید سطحِ آستانه‌ثابت (Regime_level, G_level/I_level با هیسترزیس)
   حذف شد. طبق «Why Does GDP Growth Matter» و «Understanding Inflation»،
   رژیم Prometheus بر مبنای *جهتِ تغییر* رشد/تورمه، نه سطح مطلق نسبت به
   یه آستانه‌ی دلخواه.

۲) نقدینگی دیگه یه محور سومِ هم‌وزن با G/I نیست (نه در برچسب رژیم اصلی،
   نه در جدول دارایی). طبق «What Is Liquidity»: نقدینگی جهتِ برنده‌شدنِ
   یه دارایی خاص رو تعیین نمی‌کنه، فقط ظرفیت ریسک‌پذیری رو فعال می‌کنه.
   برای همین این‌جا به‌عنوان یه *عامل جداگانه‌ی گزارش‌شده* کنار G×I میاد
   (دقیقاً مثل ستون «(-) L» جدای عکسی که فرستادید)، نه ترکیب‌شده در یه
   برچسب واحد.

۳) دیکشنری کیفیِ DIRECTION_ASSET_HINTS_8 (حدس دستیِ متنی) کاملاً حذف شد.
   به‌جاش دو جدول *تجربی* از خودِ macro_database.csv ساخته می‌شه:
   - جدول ۴رژیمی + عامل نقدینگی (معادل ساختاریِ عکس «Regime-Expected
     Returns»)
   - جدول ۸طرفه‌ی متقاطع G×I×L، با دو معیار: میانگین بازدهی سه‌ماهه و
     درصد فصل‌های مثبت (معادل ساختاریِ عکس «Asset Class Regime»)

۴) لایه‌ی احتمال (Probability Layer) دست‌نخورده موند — چون مفهوماً
   درسته (تخمین احتمالِ هر ۴ رژیم از z-score جهتِ تغییر)، فقط منبعش
   داده‌ی کلانه نه قیمت دارایی؛ این محدودیت صریحاً توی expander پایین
   صفحه اعلام می‌شه.

۵) بخش‌های داده‌خوانی و ساخت سنجه‌ی دوجزئیِ تورم (Component A/B با
   fallback) عیناً از نسخه‌ی قبلی حفظ شدن — این‌ها منبع مغایرت با
   مقالات نبودن.
"""

from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import requests
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

CLEVELAND_FED_NOWCAST_URL = "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting"

THRESH = {
    "SAHM_TRIGGER": 0.50,
    "ZSCORE_WINDOW_MONTHS": 60,
    "SIGMOID_SCALE": 1.0,
    "BRENT_SHOCK_YOY": 20.0,
    "DIVERGENCE_GAP_PP": 1.0,
    "DXY_SHOCK_3M": 5.0,
    "CREDIT_SPREAD_Z_SHOCK": 2.0,
}

NOWCAST_TRAIN_WINDOW_MONTHS = 96
NOWCAST_MIN_TRAIN_MONTHS = 24
MIN_EPISODES_PER_CELL = 3   # کمتر از این تعداد اپیزود، سلول خالی گذاشته می‌شه

REGIME_4_CODES = ["(+)G(-)I", "(+)G(+)I", "(-)G(-)I", "(-)G(+)I"]
REGIME_4_NAMES = {
    "(+)G(-)I": "Rising Growth / Falling Inflation",
    "(+)G(+)I": "Rising Growth / Rising Inflation",
    "(-)G(-)I": "Falling Growth / Falling Inflation",
    "(-)G(+)I": "Falling Growth / Rising Inflation",
}
REGIME_4_COLORS = {
    "(+)G(-)I": "#2e7d32",
    "(+)G(+)I": "#f9a825",
    "(-)G(-)I": "#1565c0",
    "(-)G(+)I": "#c62828",
}

QUADRANT_LABELS = {
    "p_gup_idown": "(+)G(-)I — Rising Growth / Falling Inflation",
    "p_gup_iup": "(+)G(+)I — Rising Growth / Rising Inflation",
    "p_gdown_idown": "(-)G(-)I — Falling Growth / Falling Inflation",
    "p_gdown_iup": "(-)G(+)I — Falling Growth / Rising Inflation",
}
QUADRANT_COLORS = {
    "p_gup_idown": "#2e7d32",
    "p_gup_iup": "#f9a825",
    "p_gdown_idown": "#1565c0",
    "p_gdown_iup": "#c62828",
}

# دارایی‌هایی که اگه توی دیتابیس باشن، توی جدول‌های تجربی نشون داده می‌شن —
# فقط ستون‌هایی که واقعاً موجودن استفاده می‌شن، بقیه بی‌صدا رد می‌شن.
ASSET_UNIVERSE = {
    "SP500": "S&P 500",
    "RSP": "Equal-Weight (RSP)",
    "XLK": "Technology", "XLF": "Financials", "XLV": "Health Care",
    "XLE": "Energy", "XLY": "Cons. Discretionary", "XLP": "Cons. Staples",
    "XLB": "Materials", "XLU": "Utilities", "XLRE": "Real Estate",
    "XLC": "Communications",
    "GOLD": "Gold", "SILVER": "Silver", "WTI": "WTI Crude", "XCUUSD": "Copper",
    "DXY": "Dollar Index", "EURUSD": "EUR/USD",
    "TLT": "20+Y Treasury (TLT)", "IEF": "7-10Y Treasury (IEF)",
}


# ==========================================================================
# 1) خواندن داده — بدون تغییر نسبت به نسخه‌ی قبلی
# ==========================================================================

def _find_db_path() -> Path:
    for p in _CANDIDATE_DB_PATHS:
        if p.exists():
            return p
    raise FileNotFoundError(
        "macro_database.csv پیدا نشد. مسیرهای بررسی‌شده:\n" +
        "\n".join(str(p) for p in _CANDIDATE_DB_PATHS)
    )


@st.cache_data(ttl=3600, show_spinner="در حال خواندن دیتابیس ماکرو (فقط‌خواندنی)...")
def load_monthly_data() -> pd.DataFrame:
    path = _find_db_path()
    df = pd.read_csv(path, parse_dates=["Date"])
    df = df.sort_values("Date").set_index("Date")

    required = [
        "CFNAI", "SAHMREALTIME", "PCETRIM12M159SFRBDAL", "CPILFESL", "PCEPILFE",
        "CPIAUCSL", "NFCI", "WALCL", "WTREGEN", "RRPONTSYD",
        "DCOILBRENTEU", "DTWEXBGS", "BAA10Y",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"ستون(های) ضروری در دیتابیس یافت نشد: {missing}")

    optional = [c for c in ["PPIFES", "WPSFD49116"] if c in df.columns]

    monthly_cols = {}
    for col in required + optional:
        monthly_cols[col] = df[col].dropna().resample("MS").last()

    monthly = pd.concat(monthly_cols, axis=1)
    return monthly


@st.cache_data(ttl=3600, show_spinner="در حال اسکرپ نوکست کلیولند...")
def fetch_cleveland_fed_nowcast() -> pd.DataFrame | None:
    try:
        resp = requests.get(
            CLEVELAND_FED_NOWCAST_URL,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RegimeClassifier/1.0)"},
            timeout=20,
        )
        resp.raise_for_status()
        tables = pd.read_html(resp.text)
    except Exception:
        return None

    candidates = []
    for t in tables:
        cols = [str(c).strip() for c in t.columns]
        needed = {"Month", "CPI", "Core CPI", "PCE", "Core PCE"}
        if needed.issubset(set(cols)):
            candidates.append(t)
    if not candidates:
        return None

    def avg_abs(t):
        vals = pd.concat([pd.to_numeric(t[c], errors="coerce") for c in ["CPI", "Core CPI", "PCE", "Core PCE"]])
        return vals.abs().mean()

    yoy_table = max(candidates, key=avg_abs)
    rows = []
    for _, row in yoy_table.iterrows():
        month_str = str(row["Month"]).strip()
        try:
            parsed = pd.to_datetime(month_str, format="%B %Y")
            date = pd.Timestamp(parsed.year, parsed.month, 1)
        except Exception:
            continue
        core_cpi = pd.to_numeric(row["Core CPI"], errors="coerce")
        core_pce = pd.to_numeric(row["Core PCE"], errors="coerce")
        if pd.notna(core_cpi) or pd.notna(core_pce):
            rows.append({"date": date, "CORE_CPI_YOY_NOWCAST": core_cpi, "CORE_PCE_YOY_NOWCAST": core_pce})
    if not rows:
        return None
    return pd.DataFrame(rows).set_index("date").sort_index()


def _fit_ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def _add_yoy_predictors(monthly: pd.DataFrame) -> pd.DataFrame:
    df = monthly.copy()
    df["CORE_CPI_YOY"] = df["CPILFESL"].pct_change(12) * 100
    df["CORE_PCE_YOY"] = df["PCEPILFE"].pct_change(12) * 100
    df["HEADLINE_CPI_YOY"] = df["CPIAUCSL"].pct_change(12) * 100
    if "PPIFES" in df.columns:
        df["CORE_PPI_YOY"] = df["PPIFES"].pct_change(12) * 100
    if "WPSFD49116" in df.columns:
        df["CORE_PPI_EXTRADE_YOY"] = df["WPSFD49116"].pct_change(12) * 100
    return df


def _fill_gap_with_bridge(df: pd.DataFrame, target_col: str, predictor_cols: list[str],
                           window: int = NOWCAST_TRAIN_WINDOW_MONTHS,
                           min_train: int = NOWCAST_MIN_TRAIN_MONTHS) -> tuple[pd.Series, pd.Series, dict]:
    filled = df[target_col].copy()
    is_nowcast = pd.Series(False, index=df.index)
    diag = {"fit_r2": np.nan, "fit_mae": np.nan, "n_train": 0}

    for i in range(len(df)):
        if pd.notna(filled.iloc[i]):
            continue
        x_row = df[predictor_cols].iloc[i]
        if x_row.isna().any():
            continue
        train = df.iloc[max(0, i - window):i].dropna(subset=[target_col] + predictor_cols)
        if len(train) < min_train:
            continue

        X_train = np.column_stack([np.ones(len(train))] + [train[c].values for c in predictor_cols])
        y_train = train[target_col].values
        beta = _fit_ols(X_train, y_train)

        y_fit = X_train @ beta
        ss_res = np.sum((y_train - y_fit) ** 2)
        ss_tot = np.sum((y_train - y_train.mean()) ** 2)
        diag["fit_r2"] = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        diag["fit_mae"] = float(np.mean(np.abs(y_train - y_fit)))
        diag["n_train"] = len(train)

        x_pred = np.array([1.0] + list(x_row.values))
        filled.iloc[i] = float(x_pred @ beta)
        is_nowcast.iloc[i] = True

    return filled, is_nowcast, diag


@st.cache_data(ttl=3600, show_spinner=False)
def walkforward_backtest(monthly: pd.DataFrame, target_col: str, predictor_cols: tuple[str, ...],
                          window: int = NOWCAST_TRAIN_WINDOW_MONTHS,
                          min_train: int = NOWCAST_MIN_TRAIN_MONTHS) -> pd.DataFrame:
    df = _add_yoy_predictors(monthly)
    predictor_cols = list(predictor_cols)
    if any(c not in df.columns for c in predictor_cols):
        return pd.DataFrame(columns=["Actual", "Nowcast", "Error"])

    rows = []
    for i in range(len(df)):
        if pd.isna(df[target_col].iloc[i]):
            continue
        x_row = df[predictor_cols].iloc[i]
        if x_row.isna().any():
            continue
        train = df.iloc[max(0, i - window):i].dropna(subset=[target_col] + predictor_cols)
        if len(train) < min_train:
            continue
        X_train = np.column_stack([np.ones(len(train))] + [train[c].values for c in predictor_cols])
        y_train = train[target_col].values
        beta = _fit_ols(X_train, y_train)
        x_pred = np.array([1.0] + list(x_row.values))
        pred = float(x_pred @ beta)
        rows.append({"date": df.index[i], "Actual": df[target_col].iloc[i], "Nowcast": pred})

    if not rows:
        return pd.DataFrame(columns=["Actual", "Nowcast", "Error"])
    bt = pd.DataFrame(rows).set_index("date")
    bt["Error"] = bt["Nowcast"] - bt["Actual"]
    return bt


def build_inflation_measure(monthly: pd.DataFrame, cleveland: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]:
    df = _add_yoy_predictors(monthly)
    diagnostics = {}

    a_predictors = ["CORE_CPI_YOY"] + (["CORE_PPI_YOY"] if "CORE_PPI_YOY" in df.columns else [])
    if "CORE_PPI_EXTRADE_YOY" in df.columns:
        a_predictors.append("CORE_PPI_EXTRADE_YOY")

    if len(a_predictors) >= 2:
        comp_a, comp_a_is_now, diag_a = _fill_gap_with_bridge(df, "PCETRIM12M159SFRBDAL", a_predictors)
        diagnostics["component_a_enabled"] = True
    else:
        comp_a, comp_a_is_now = df["PCETRIM12M159SFRBDAL"].copy(), pd.Series(False, index=df.index)
        diag_a = {"fit_r2": np.nan, "fit_mae": np.nan, "n_train": 0}
        diagnostics["component_a_enabled"] = False
    diagnostics["component_a_diag"] = diag_a
    diagnostics["component_a_predictors"] = a_predictors

    df["Component_A"] = comp_a
    df["Component_A_Is_Nowcast"] = comp_a_is_now

    df["Component_B"] = df["PCETRIM12M159SFRBDAL"].shift(-1)
    df["Component_B_Is_Nowcast"] = False
    diagnostics["component_b_cleveland_available"] = cleveland is not None
    diagnostics["component_b_target_month"] = None
    diagnostics["component_b_diag"] = {"fit_r2": np.nan, "fit_mae": np.nan, "n_train": 0}

    if cleveland is not None:
        b_predictors = ["CORE_CPI_YOY", "CORE_PCE_YOY"]
        for i in range(len(df)):
            if pd.notna(df["Component_B"].iloc[i]):
                continue
            target_month = df.index[i] + pd.DateOffset(months=1)
            if target_month not in cleveland.index:
                continue

            cpi_now = cleveland.loc[target_month, "CORE_CPI_YOY_NOWCAST"]
            pce_now = cleveland.loc[target_month, "CORE_PCE_YOY_NOWCAST"]
            if pd.isna(cpi_now) or pd.isna(pce_now):
                continue

            train = df.iloc[max(0, i - NOWCAST_TRAIN_WINDOW_MONTHS):i + 1].dropna(
                subset=["PCETRIM12M159SFRBDAL"] + b_predictors
            )
            if len(train) < NOWCAST_MIN_TRAIN_MONTHS:
                continue

            X_train = np.column_stack([np.ones(len(train))] + [train[c].values for c in b_predictors])
            y_train = train["PCETRIM12M159SFRBDAL"].values
            beta = _fit_ols(X_train, y_train)

            y_fit = X_train @ beta
            ss_res = np.sum((y_train - y_fit) ** 2)
            ss_tot = np.sum((y_train - y_train.mean()) ** 2)
            diagnostics["component_b_diag"] = {
                "fit_r2": 1 - ss_res / ss_tot if ss_tot > 0 else np.nan,
                "fit_mae": float(np.mean(np.abs(y_train - y_fit))),
                "n_train": len(train),
            }

            x_pred = np.array([1.0, cpi_now, pce_now])
            df.iloc[i, df.columns.get_loc("Component_B")] = float(x_pred @ beta)
            df.iloc[i, df.columns.get_loc("Component_B_Is_Nowcast")] = True
            diagnostics["component_b_target_month"] = target_month

    df["Component_B_Is_Fallback"] = False
    still_missing = df["Component_B"].isna() & df["Component_A"].notna()
    df.loc[still_missing, "Component_B"] = df.loc[still_missing, "Component_A"]
    df.loc[still_missing, "Component_B_Is_Fallback"] = True

    df["INFLATION_MEASURE"] = 0.5 * df["Component_A"] + 0.5 * df["Component_B"]
    df["Inflation_Is_Nowcast"] = (
        df["Component_A_Is_Nowcast"] | df["Component_B_Is_Nowcast"] | df["Component_B_Is_Fallback"]
    )

    return df, diagnostics


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

def _fit_table_height(n_rows: int, row_px: int = 35, header_px: int = 38, pad_px: int = 3) -> int:
    return header_px + row_px * n_rows + pad_px

# ==========================================================================
# 2) محورهای رشد/تورم/نقدینگی — بازطراحی‌شده (بدون گرید سطح، بدون
#    نقدینگی به‌عنوان محور سوم)
# ==========================================================================

def compute_regime_signals(monthly: pd.DataFrame, cleveland: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]:
    out, inflation_diag = build_inflation_measure(monthly, cleveland)

    out["CFNAI_MA3"] = out["CFNAI"].rolling(3, min_periods=1).mean()
    out["NET_LIQUIDITY"] = (out["WALCL"] - out["WTREGEN"] - out["RRPONTSYD"]) / 1000.0

    out["G_chg3m"] = out["CFNAI_MA3"].diff(3)
    out["I_chg3m"] = out["INFLATION_MEASURE"].diff(3)
    out["L_chg3m"] = out["NET_LIQUIDITY"].pct_change(3) * 100

    sahm_trigger = out["SAHMREALTIME"] >= THRESH["SAHM_TRIGGER"]

    out["G_dir"] = np.where(out["G_chg3m"] >= 0, "+", "-")
    out.loc[out["G_chg3m"].isna(), "G_dir"] = np.nan
    out.loc[sahm_trigger, "G_dir"] = "-"  # قانون سام: override صریح، مستقل از علامت تغییر

    out["I_dir"] = np.where(out["I_chg3m"] >= 0, "+", "-")
    out.loc[out["I_chg3m"].isna(), "I_dir"] = np.nan

    out["L_dir"] = np.where(out["L_chg3m"] >= 0, "+", "-")
    out.loc[out["L_chg3m"].isna(), "L_dir"] = np.nan

    out["regime_4"] = [
        f"({g})G({i})I" if pd.notna(g) and pd.notna(i) else np.nan
        for g, i in zip(out["G_dir"], out["I_dir"])
    ]
    out["regime_8"] = [
        f"({g})G({i})I({l})L" if pd.notna(g) and pd.notna(i) and pd.notna(l) else np.nan
        for g, i, l in zip(out["G_dir"], out["I_dir"], out["L_dir"])
    ]
    out["Days_in_regime_4"] = _days_in_state(out["regime_4"])

    # --- لایه‌ی احتمال (از داده‌ی کلان، نه قیمت دارایی — محدودیت صریح) ---
    win, scale = THRESH["ZSCORE_WINDOW_MONTHS"], THRESH["SIGMOID_SCALE"]

    def rolling_z(series):
        mu = series.rolling(win, min_periods=24).mean()
        sd = series.rolling(win, min_periods=24).std()
        return (series - mu) / sd.replace(0, np.nan)

    def sigmoid(z):
        return 1.0 / (1.0 + np.exp(-scale * z))

    out["p_growth_up"] = sigmoid(rolling_z(out["G_chg3m"]))
    out["p_inflation_up"] = sigmoid(rolling_z(out["I_chg3m"]))
    out["p_gup_idown"] = out["p_growth_up"] * (1 - out["p_inflation_up"])
    out["p_gup_iup"] = out["p_growth_up"] * out["p_inflation_up"]
    out["p_gdown_idown"] = (1 - out["p_growth_up"]) * (1 - out["p_inflation_up"])
    out["p_gdown_iup"] = (1 - out["p_growth_up"]) * out["p_inflation_up"]

    quad_cols = ["p_gup_idown", "p_gup_iup", "p_gdown_idown", "p_gdown_iup"]
    quad_df = out[quad_cols]

    def safe_idxmax(row):
        return np.nan if row.notna().sum() == 0 else row.idxmax()

    out["top_regime_key"] = quad_df.apply(safe_idxmax, axis=1)
    out["top_regime"] = out["top_regime_key"].map(QUADRANT_LABELS)
    out["top_regime_prob"] = quad_df.max(axis=1, skipna=True)

    def entropy_row(row):
        vals = row[quad_cols].values.astype(float)
        if np.any(np.isnan(vals)):
            return np.nan
        vals = np.clip(vals, 1e-12, 1.0)
        return float(-np.sum(vals * np.log2(vals)))

    out["probability_entropy"] = out.apply(entropy_row, axis=1)

    # --- Overlay شوک بیرونی (بدون تغییر نسبت به نسخه‌ی قبلی) ---
    out["BRENT_YOY"] = out["DCOILBRENTEU"].pct_change(12) * 100
    out["Headline_Underlying_Gap_pp"] = out["HEADLINE_CPI_YOY"] - out["INFLATION_MEASURE"]
    out["Headline_Underlying_Divergence_Flag"] = (
        (out["BRENT_YOY"].abs() > THRESH["BRENT_SHOCK_YOY"]) &
        (out["Headline_Underlying_Gap_pp"].abs() > THRESH["DIVERGENCE_GAP_PP"])
    )
    out["DXY_PROXY_3M_CHG"] = out["DTWEXBGS"].pct_change(3) * 100
    out["CREDIT_SPREAD_BAA10Y"] = out["BAA10Y"]
    out["credit_spread_z"] = rolling_z(out["CREDIT_SPREAD_BAA10Y"])
    out["Shock_Alert"] = (
        (out["BRENT_YOY"].abs() > 30) |
        (out["DXY_PROXY_3M_CHG"].abs() > THRESH["DXY_SHOCK_3M"]) |
        (out["credit_spread_z"].abs() > THRESH["CREDIT_SPREAD_Z_SHOCK"])
    )

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

    return out, inflation_diag


def get_reference_row(df: pd.DataFrame) -> pd.Series:
    """آخرین ماهی که هم رشد/تورم هم رژیمِ ۴تایی/لایه‌ی احتمال کامل دارن."""
    full_anchor = ["CFNAI_MA3", "INFLATION_MEASURE", "regime_4", "top_regime"]
    valid_full = df.dropna(subset=full_anchor)
    if not valid_full.empty:
        return valid_full.iloc[-1]

    partial_anchor = ["CFNAI_MA3", "INFLATION_MEASURE"]
    valid_partial = df.dropna(subset=partial_anchor)
    if not valid_partial.empty:
        return valid_partial.iloc[-1]

    return df.iloc[-1]


def get_latest_overlay_row(df: pd.DataFrame) -> pd.Series:
    cols = ["BRENT_YOY", "DXY_PROXY_3M_CHG", "CREDIT_SPREAD_BAA10Y", "Financial_state"]
    valid = df.dropna(subset=cols)
    return valid.iloc[-1] if not valid.empty else df.iloc[-1]


# ==========================================================================
# 3) جدول‌های تجربیِ دارایی — این بخش کاملاً جدیده
# ==========================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_asset_prices(path: str, mtime: float) -> pd.DataFrame:
    available = pd.read_csv(path, nrows=0).columns
    cols = [c for c in ASSET_UNIVERSE if c in available]
    if not cols:
        return pd.DataFrame()
    df = pd.read_csv(path, usecols=["Date"] + cols)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _build_regime_episodes(regime_df: pd.DataFrame, regime_col: str) -> list[dict]:
    """هر اپیزودِ پیوسته‌ی یه مقدار رژیم رو به‌صورت (start, end, label) برمی‌گردونه —
    start/end تاریخِ ماهِ اول/آخرِ همون اپیزودن (چون خودِ regime_df ماهانه‌ست)."""
    series = regime_df[regime_col].dropna()
    if series.empty:
        return []

    idx, vals = series.index, series.values
    episodes, start_i = [], 0
    for i in range(1, len(vals)):
        if vals[i] != vals[start_i]:
            episodes.append({"start": idx[start_i], "end": idx[i - 1], "label": vals[start_i]})
            start_i = i
    episodes.append({"start": idx[start_i], "end": idx[-1], "label": vals[start_i]})
    return episodes


def _episode_asset_return(asset_df: pd.DataFrame, asset: str, ep: dict) -> float:
    """بازدهیِ کلِ یه اپیزود برای یه دارایی: از آخرین قیمتِ *درست‌قبل* از شروع
    اپیزود، تا آخرین قیمتِ موجود تا پایانِ ماهِ آخرِ اپیزود."""
    if asset not in asset_df.columns:
        return np.nan

    idx = asset_df.index
    pos_start = idx.searchsorted(ep["start"])
    pos_base = max(pos_start - 1, 0)
    base_price = asset_df[asset].iloc[pos_base]

    episode_end_calendar = ep["end"] + pd.offsets.MonthEnd(0)
    end_slice = asset_df.loc[:episode_end_calendar, asset].dropna()
    if end_slice.empty or pd.isna(base_price) or base_price == 0:
        return np.nan

    end_price = end_slice.iloc[-1]
    return (end_price / base_price - 1) * 100


def _episode_length_days(ep: dict) -> int:
    return (ep["end"] + pd.offsets.MonthEnd(0) - ep["start"]).days


def build_regime_return_table_4(asset_df: pd.DataFrame, regime_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """معادل ساختاریِ عکس «Regime-Expected Returns»، این‌بار per-episode
    (نه پنجره‌ی ثابت سه‌ماهه). نقدینگی جدا از G×I محاسبه می‌شه — طبق اصل
    مقاله‌ی Liquidity."""
    episodes_4 = _build_regime_episodes(regime_df, "regime_4")
    episodes_L = _build_regime_episodes(regime_df, "L_dir")

    rows, meta = [], {}
    for asset, label in ASSET_UNIVERSE.items():
        if asset not in asset_df.columns:
            continue
        row = {"دارایی": label}

        for code in REGIME_4_CODES:
            eps = [e for e in episodes_4 if e["label"] == code]
            rets = [_episode_asset_return(asset_df, asset, e) for e in eps]
            rets = [r for r in rets if pd.notna(r)]
            row[code] = np.mean(rets) if len(rets) >= MIN_EPISODES_PER_CELL else np.nan
            meta[code] = {
                "n_episodes": len(eps),
                "avg_len_days": np.mean([_episode_length_days(e) for e in eps]) if eps else np.nan,
            }

        for l_sym, l_label in [("+", "(+) L — نقدینگی رو به گشایش"), ("-", "(-) L — نقدینگی رو به انقباض")]:
            eps = [e for e in episodes_L if e["label"] == l_sym]
            rets = [_episode_asset_return(asset_df, asset, e) for e in eps]
            rets = [r for r in rets if pd.notna(r)]
            row[l_label] = np.mean(rets) if len(rets) >= MIN_EPISODES_PER_CELL else np.nan
            meta[l_label] = {
                "n_episodes": len(eps),
                "avg_len_days": np.mean([_episode_length_days(e) for e in eps]) if eps else np.nan,
            }

        rows.append(row)

    return pd.DataFrame(rows).set_index("دارایی"), meta


def build_regime_return_table_8(asset_df: pd.DataFrame, regime_df: pd.DataFrame, metric: str = "mean") -> tuple[pd.DataFrame, dict]:
    """معادل ساختاریِ عکس «Asset Class Regime»، per-episode روی هر ۸ ترکیب G×I×L."""
    episodes_8 = _build_regime_episodes(regime_df, "regime_8")
    codes_8 = [f"({g})G({i})I({l})L" for g in ["+", "-"] for i in ["+", "-"] for l in ["+", "-"]]

    rows, meta = [], {}
    for code in codes_8:
        eps = [e for e in episodes_8 if e["label"] == code]
        meta[code] = {
            "n_episodes": len(eps),
            "avg_len_days": np.mean([_episode_length_days(e) for e in eps]) if eps else np.nan,
        }

    for asset, label in ASSET_UNIVERSE.items():
        if asset not in asset_df.columns:
            continue
        row = {"دارایی": label}
        for code in codes_8:
            eps = [e for e in episodes_8 if e["label"] == code]
            rets = [_episode_asset_return(asset_df, asset, e) for e in eps]
            rets = [r for r in rets if pd.notna(r)]
            if len(rets) < MIN_EPISODES_PER_CELL:
                row[code] = np.nan
            elif metric == "mean":
                row[code] = np.mean(rets)
            else:
                row[code] = (np.array(rets) > 0).mean() * 100
        rows.append(row)

    return pd.DataFrame(rows).set_index("دارایی"), meta

# ==========================================================================
# 4) رابط کاربری
# ==========================================================================

def show():
    inject_global_style()
    st.markdown("## 📊 US Macro Regime — Growth × Inflation × Liquidity")
    st.caption(
        "بازطراحی‌شده بر مبنای اصول مقالات Prometheus Research — رژیم بر مبنای جهتِ تغییر "
        "(نه سطح مطلق)؛ نقدینگی عاملی جداست، نه محور سومِ هم‌وزن؛ جدول‌های دارایی، تجربی و "
        "محاسبه‌شده از دیتابیس شمان."
    )
    st.info(
        "**این صفحه چی می‌گه؟** اقتصاد آمریکا رو روی دو محور می‌سنجه: آیا **رشد** داره شتاب "
        "می‌گیره یا کند می‌شه، و آیا **تورم** داره بالا می‌ره یا پایین میاد. از ترکیب این دو، "
        "۴ تا حالت ممکنه (مثلاً «رشد بالا + تورم پایین»). برای هر حالت، از تاریخچه‌ی واقعیِ "
        "خودتون می‌بینید هر دارایی (سهام، طلا، نفت، ...) به‌طور میانگین چطور بازده داده. "
        "**نقدینگی** (میزان پول در گردشِ سیستم بانکی) یه عامل جداست — جهتِ برنده‌شدنِ یه دارایی "
        "رو تعیین نمی‌کنه، فقط شدتِ واکنش بازار رو تشدید یا تضعیف می‌کنه."
    )

    with st.expander("📚 این صفحه دقیقاً از کدام اصول مقالات پیروی می‌کند و چه محدودیتی دارد؟"):
        st.markdown(
            "- **رشد و تورم**: محور اصلی، بر مبنای جهتِ تغییرِ ۳ماهه — طبق «Why Does GDP Growth "
            "Matter» و «Understanding Inflation».\n"
            "- **نقدینگی**: عاملی مستقل و جدا، نه محور سومِ هم‌وزن — طبق «What Is Liquidity»، که "
            "صریحاً می‌گوید نقدینگی جهتِ برنده‌شدنِ یک دارایی خاص را تعیین نمی‌کند، فقط ظرفیت "
            "ریسک‌پذیری را فعال می‌کند.\n"
            "- **جدول‌های دارایی**: تجربی‌اند — میانگین بازدهی واقعیِ سه‌ماهه، شرطی بر رژیم، از "
            "خودِ دیتابیس شما؛ نه یک توصیف کیفیِ دستی.\n\n"
            "⚠️ **آنچه این‌جا نیست و نمی‌توانست باشد**: بخش «bottom-up قیمت‌محور» که طبق یادداشت "
            "«Macro Regime Probabilities» برای تخمین احتمال ۱روزه‌ی forward استفاده می‌شود — فرمول "
            "و سیگنال‌های دقیقش منتشر نشده. لایه‌ی احتمال زیر، صرفاً از داده‌ی کلان (نه قیمت "
            "دارایی‌ها) ساخته شده، پس افق و ماهیتش با نسخه‌ی واقعیِ Prometheus فرق دارد."
        )

    try:
        monthly_raw = load_monthly_data()
    except (FileNotFoundError, KeyError) as e:
        st.error(str(e))
        return

    cleveland = fetch_cleveland_fed_nowcast()
    df, inflation_diag = compute_regime_signals(monthly_raw, cleveland)
    ref = get_reference_row(df)
    is_lagged = ref.name != df.index[-1]

    st.caption(f"📅 ماهِ مرجعِ این گزارش: **{ref.name.strftime('%B %Y')}**  |  "
               f"آخرین ردیف دیتابیس: {df.index[-1].strftime('%B %Y')}")

    if pd.isna(ref.get("top_regime")):
        st.error(
            "⚠️ حتی بعد از رفتن به آخرین ماهِ کامل، لایهٔ احتمال/رژیم هنوز NaN است — معمولاً یعنی "
            "پنجرهٔ ۶۰ماههٔ z-score هنوز به‌اندازهٔ کافی دادهٔ پیوسته ندارد."
        )

    if is_lagged:
        months_behind = (df.index[-1].to_period("M") - ref.name.to_period("M")).n
        st.warning(
            f"⚠️ این گزارش مربوط به آخرین ماهی است که رشد/تورم/رژیم برایش کامل بودند: "
            f"**{ref.name.strftime('%B %Y')}** ({months_behind} ماه عقب‌تر از آخرین ردیف دیتابیس)."
        )

    with st.expander("ℹ️ جزئیات فنی سنجه‌ی دوجزئیِ تورم"):
        a_status = "🔮 نوکست (بریج CPI/PPI)" if bool(ref.get("Component_A_Is_Nowcast", False)) else "✅ عدد رسمی"
        if bool(ref.get("Component_B_Is_Nowcast", False)):
            b_status = "🔮 نوکست (کلیولند)"
        elif bool(ref.get("Component_B_Is_Fallback", False)):
            b_status = "↩️ Fallback (از Component A)"
        else:
            b_status = "✅ عدد رسمی (گذشته‌نگر)"
        st.markdown(
            f"- **Component A** ({ref.name.strftime('%B %Y')}): `{ref['Component_A']:.2f}%` — {a_status}\n"
            f"- **Component B** ({(ref.name + pd.DateOffset(months=1)).strftime('%B %Y')}): "
            f"`{ref['Component_B']:.2f}%` — {b_status}\n"
            f"- **سنجه‌ی نهایی** = 0.5×A + 0.5×B = `{ref['INFLATION_MEASURE']:.2f}%`"
        )

    # --- کارت‌های خلاصه ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Regime (4-way)", ref["regime_4"])
    c2.metric("Liquidity Direction", f"({ref['L_dir']}) L")
    c3.metric("CFNAI-MA3", f"{ref['CFNAI_MA3']:+.3f}")
    c4.metric("Days in Regime", int(ref["Days_in_regime_4"]))

    st.markdown("### 🎲 Probability Layer")
    p1, p2 = st.columns(2)
    p1.metric("رژیم غالب", ref.get("top_regime", "—"))
    ent = ref.get("probability_entropy", np.nan)
    p2.metric("آنتروپی (0-2)", f"{ent:.2f}" if pd.notna(ent) else "—")
    st.caption(
        "نزدیک به ۰ یعنی یه رژیم به‌وضوح غالبه؛ نزدیک به ۲ یعنی هر ۴ رژیم تقریباً هم‌احتمالن "
        "(رژیم مختلط/نامشخص). این احتمال از داده‌ی کلانه، نه قیمت دارایی."
    )

    # --- شرایط مالی + شوک ---
    overlay_ref = get_latest_overlay_row(df)
    st.markdown("### 🏦 Financial Conditions & Shock Overlay")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("NFCI State", overlay_ref.get("Financial_state", "—"))
    f2.metric("Brent YoY", f"{overlay_ref['BRENT_YOY']:+.1f}%" if pd.notna(overlay_ref.get("BRENT_YOY")) else "—")
    f3.metric("DXY 3M Δ", f"{overlay_ref['DXY_PROXY_3M_CHG']:+.1f}%" if pd.notna(overlay_ref.get("DXY_PROXY_3M_CHG")) else "—")
    f4.metric("Baa-10Y Spread", f"{overlay_ref['CREDIT_SPREAD_BAA10Y']:.2f}" if pd.notna(overlay_ref.get("CREDIT_SPREAD_BAA10Y")) else "—")
    if bool(ref.get("Headline_Underlying_Divergence_Flag", False)):
        st.warning("⚠️ پرچم واگرایی تورمی فعال — شوک نفتی/کالایی از تورم ساختاری جداست.")
    if bool(overlay_ref.get("Shock_Alert", False)):
        st.error("⚠️ هشدار شوک بیرونی فعال (نفت/دلار/اسپرد اعتباری).")

    st.divider()

    # --- جدول‌های تجربی دارایی ---
    db_path = _find_db_path()
    asset_df = load_asset_prices(str(db_path), db_path.stat().st_mtime)

    if asset_df.empty:
        st.warning("هیچ‌کدوم از دارایی‌های ASSET_UNIVERSE توی دیتابیس نیستن — جدول‌های تجربی نمایش داده نمی‌شن.")
    else:
        st.markdown("### 📈 Regime-Expected Returns (۴ رژیم + عامل نقدینگی)")
        st.caption(
            "میانگین بازدهیِ *کل طول هر اپیزودِ واقعیِ رژیم* (نه یه پنجره‌ی ثابت سه‌ماهه) — "
            "اگه یه رژیم فقط ۴۰ روز طول کشیده، بازدهیِ همون ۴۰ روز حساب می‌شه؛ اگه ۳۰۰ روز طول "
            "کشیده، بازدهیِ همون ۳۰۰ روز."
        )
        table4, meta4 = build_regime_return_table_4(asset_df, df)
        meta_line = " | ".join(
            f"{c}: {m['n_episodes']} اپیزود (میانگین طول {m['avg_len_days']:.0f} روز)"
            if pd.notna(m["avg_len_days"]) else f"{c}: 0 اپیزود"
            for c, m in meta4.items()
        )
        st.caption(meta_line)
        st.dataframe(
            table4.style.format("{:+.1f}%", na_rep="—").background_gradient(cmap="RdYlGn", axis=None),
            use_container_width=True,
            height=_fit_table_height(len(table4)),
        )

        st.divider()
        st.markdown("### 🧮 Asset Class Regime — ۸ ترکیبِ متقاطع G×I×L")
        tab_mean, tab_pos = st.tabs(["میانگین بازدهی هر اپیزود", "٪ اپیزودهای مثبت"])
        with tab_mean:
            table8_mean, meta8 = build_regime_return_table_8(asset_df, df, metric="mean")
            st.dataframe(
                table8_mean.style.format("{:+.1f}%", na_rep="—").background_gradient(cmap="RdYlGn", axis=None),
                use_container_width=True,
                height=_fit_table_height(len(table8_mean)),
            )
        with tab_pos:
            table8_pos, _ = build_regime_return_table_8(asset_df, df, metric="pct_positive")
            st.dataframe(
                table8_pos.style.format("{:.0f}%", na_rep="—").background_gradient(cmap="RdYlGn", axis=None, vmin=0, vmax=100),
                use_container_width=True,
                height=_fit_table_height(len(table8_pos)),
            )

        with st.expander("📏 تعداد اپیزود و میانگین طول، برای هر یک از ۸ حالت"):
            meta8_df = pd.DataFrame(meta8).T
            meta8_df.columns = ["تعداد اپیزود", "میانگین طول (روز)"]
            st.dataframe(meta8_df.style.format({"میانگین طول (روز)": "{:.0f}"}), use_container_width=True)

        st.caption(
            "⚠️ محدودیت آماری: سلول‌های با کمتر از "
            f"{MIN_EPISODES_PER_CELL} اپیزود نمونه، خالی (—) گذاشته شدن. چون رژیمِ ۸طرفه (G×I×L) "
            "با تغییرِ هرکدوم از سه محور عوض می‌شه، اپیزودهاش طبیعتاً کوتاه‌تر و پرتعدادتر از "
            "رژیمِ ۴طرفه‌ان — این آمار توصیفیِ تاریخیه، نه پیش‌بینی."
        )

    st.divider()

    # --- نمودار خط‌زمانی رژیم ۴تایی ---
    st.markdown("### Regime Timeline")
    plotdf = df.dropna(subset=["regime_4"])
    if not plotdf.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=plotdf.index, y=plotdf["CFNAI_MA3"], name="CFNAI-MA3 (Growth)",
                                  line=dict(color="#2f9bd6", width=2)))
        has_sp500 = not asset_df.empty and "SP500" in asset_df.columns
        if has_sp500:
            sp_monthly = asset_df["SP500"].resample("MS").last()
            sp_aligned = sp_monthly.reindex(plotdf.index).ffill()
            fig.add_trace(go.Scatter(x=plotdf.index, y=sp_aligned, name="SP500 Close",
                                      yaxis="y3", line=dict(color="#f4f4f4", width=1.6)))

        fig.add_trace(go.Scatter(x=plotdf.index, y=plotdf["INFLATION_MEASURE"], name="Inflation Measure (%)",
                                  line=dict(color="#e8a33d", width=2), yaxis="y2"))

        shapes = []
        prev, seg_start = None, plotdf.index[0]
        for date, regime in plotdf["regime_4"].items():
            if regime != prev:
                if prev is not None:
                    shapes.append(dict(type="rect", xref="x", yref="paper", x0=seg_start, x1=date,
                                        y0=0, y1=1, fillcolor=REGIME_4_COLORS.get(prev, "#888"),
                                        opacity=0.6, line_width=0))
                seg_start, prev = date, regime
        if prev is not None:
            shapes.append(dict(type="rect", xref="x", yref="paper", x0=seg_start, x1=plotdf.index[-1],
                                y0=0, y1=1, fillcolor=REGIME_4_COLORS.get(prev, "#888"),
                                opacity=0.6, line_width=0))

        for code in REGIME_4_CODES:
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                                      marker=dict(size=14, color=REGIME_4_COLORS[code], symbol="square"),
                                      name=code, showlegend=True))

        fig.update_layout(
            template="plotly_dark", height=440, shapes=shapes,
            yaxis=dict(title="CFNAI-MA3"),
            yaxis2=dict(title="Inflation (%)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.15, font=dict(size=11)),
            margin=dict(t=50, b=30),
            **({"yaxis3": dict(overlaying="y", side="right", showticklabels=False,
                               showgrid=False, zeroline=False, type="log")} if has_sp500 else {}),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("### 🎲 Entropy Timeline — اطمینان مدل در طول زمان")

        prob_plotdf = df.dropna(subset=["probability_entropy", "top_regime_key"])
        if not prob_plotdf.empty:
            fig_ent = go.Figure()
            fig_ent.add_trace(go.Scatter(
                x=prob_plotdf.index, y=prob_plotdf["probability_entropy"],
                name="Entropy", line=dict(color="#bbbbbb", width=1.6),
            ))

            shapes_ent = []
            prev_key, seg_start = None, prob_plotdf.index[0]
            for date, key in prob_plotdf["top_regime_key"].items():
                if key != prev_key:
                    if prev_key is not None:
                        shapes_ent.append(dict(
                            type="rect", xref="x", yref="paper", x0=seg_start, x1=date,
                            y0=0, y1=1, fillcolor=QUADRANT_COLORS.get(prev_key, "#888"),
                            opacity=0.15, line_width=0,
                        ))
                    seg_start, prev_key = date, key
            if prev_key is not None:
                shapes_ent.append(dict(
                    type="rect", xref="x", yref="paper", x0=seg_start, x1=prob_plotdf.index[-1],
                    y0=0, y1=1, fillcolor=QUADRANT_COLORS.get(prev_key, "#888"),
                    opacity=0.15, line_width=0,
                ))

            fig_ent.add_hline(y=0, line_dash="dot", line_color="#4caf50", opacity=0.6)
            fig_ent.add_hline(y=2, line_dash="dot", line_color="#d9534f", opacity=0.6)
            fig_ent.update_layout(
                template="plotly_dark", height=300, shapes=shapes_ent,
                yaxis=dict(title="Entropy", range=[0, 2]),
                margin=dict(t=20, b=20),
            )
            st.plotly_chart(fig_ent, use_container_width=True)
            st.caption(
                "هرچی خط به **۰** نزدیک‌تر باشه، مدل مطمئن‌تره کدوم رژیم برقراره؛ نزدیک **۲** یعنی "
                "هر ۴ رژیم تقریباً هم‌احتمال شدن (وضعیت انتقالی/مبهم). رنگِ کم‌رنگِ پس‌زمینه، رژیمِ "
                "غالبِ همون لحظه رو نشون می‌ده، فقط برای راهنمایی چشم."
            )

    st.caption(
        "منبع داده: macro_database.csv (فقط‌خواندنی) | چارچوب: G×I جهت‌محور + نقدینگی به‌عنوان "
        f"عامل جدا (بر مبنای مقالات Prometheus Research) | آخرین ردیف دیتابیس: "
        f"{df.index[-1].strftime('%Y-%m-%d')}"
    )