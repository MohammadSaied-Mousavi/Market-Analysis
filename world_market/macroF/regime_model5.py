#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regime_model5.py
=================
پورت محلی (local-CSV) و وفادار به منطق اصلی نویسنده:

    Eco3min Macro Regime Classifier — v1.1.0
    https://github.com/eco3min/macro-regime-classifier
    Threshold table: config/thresholds.json v1.1.0 (calibrated & frozen 2026-07-11)
    Licence: MIT (کد) · CC-BY 4.0 (جدول آستانه‌ها و خروجی‌های مشتق‌شده)

این فایل، تمام قوانین طبقه‌بندی رژیم کلان اقتصاد آمریکا رو عیناً از اسکریپت اصلی نویسنده
(scripts/regime_classifier.py) پیاده‌سازی می‌کنه:

    - محور رشد (Growth):     CFNAI-MA3  + گیت Sahm (edge-trigger)  + هیسترزیس ۲ ماهه
    - محور تورم (Inflation):  Dallas Fed Trimmed-Mean PCE 12m      + هیسترزیس ۲ ماهه
    - لایه‌ی استرس مالی:      Chicago Fed NFCI (بدون هیسترزیس)
    - لایه‌ی زمینه‌ی جهانی:   US/G7 CLI sync + دلار + برنت + VIX + CISS
    - Grid نهایی ۳×۳ رشد×تورم  →  ۸ کد رژیم (regime_code 1..8)

تنها تفاوت ساختاری با کد اصلی، لایه‌ی ورودی داده‌ست: به‌جای fetch زنده‌ی هر سری از
FRED / ECB / Richmond Fed در زمان اجرا، همه‌چیز از یک CSV محلی (macro_database.csv)
بازسازی می‌شه — با همون فرکانس نمونه‌برداری و همون فرمول‌هایی که نویسنده به‌کار برده
(نگاه کن به `LocalDataBundle` پایین‌تر). ثابت‌ها، grid رژیم‌ها، ماشین‌حالت هیسترزیس،
گیت Sahm و resolve_regime همگی کپیِ عینی هستن — چیزی در تئوریِ کد تغییر نکرده.

────────────────────────────────────────────────────────────────────────────
تفاوت‌های مستندشده‌ی این پورت با اجرای زنده‌ی اصلی
────────────────────────────────────────────────────────────────────────────
هیچ‌کدوم از موارد زیر لیبل رژیم (regime_code / growth_state / inflation_state) رو
تغییر نمی‌دن مگر صراحتاً خلافش گفته بشه — این‌ها همه در سطح «ورودی»، نه «تئوری»اند:

  1. SOS (Richmond Fed recession indicator) — در macro_database.csv شما وجود نداره.
     این تنها سری‌ای بود که در بین همه‌ی سری‌های استفاده‌شده توسط نویسنده، شما ندارید.
     در کد اصلی هم SOS یک ورودی «best-effort» با graceful degradation طراحی‌شده:
     fetch_richmond_sos() اگر نتونه داده بگیره Series خالی برمی‌گردونه و کد با
     `SOS unavailable — proceeding without SOS signal` ادامه می‌ده. این پورت هم دقیقاً
     همون مسیر رو می‌ره (sos همیشه NaN). تنها اثر SOS در کل کد این‌جاست:
     `raw_classify_growth`، وقتی CFNAI-MA3 داخل باند خنثی (-0.50 تا 0.10) باشه و
     SOS >= 0.20 بشه، به‌عنوان هشدار زودهنگام G_minus رو زودتر فعال می‌کنه. نبود این
     سیگنال دقیقاً همون چیزیه که شما گفتید «تا الان تغییری در نتایج ایجاد نکرده» —
     چون این شرط فقط در یک باند باریک و برای دوره‌های نسبتاً کم‌تلاطم فعال می‌شه.
  2. VIX ⇢ ستون شما «VIX» است، در کد اصلی «VIXCLS» (هر دو یعنی همون شاخص بسته‌ی
     CBOE VIX). این فقط اسم ستونه، نه سری متفاوت.
  3. Brent ⇢ کد اصلی برنت ماهانه‌ی World Bank CMO یا در نبودش FRED `MCOILBRENTEU`
     (میانگین ماهانه) می‌خونه. شما ستون `DCOILBRENTEU` (اسپات روزانه‌ی برنت اروپا)
     را دارید که این‌جا با «آخرین مقدار هر ماه» ماهانه می‌شه. طبق README خودِ پروژه،
     برنت هرگز محور رشد/تورم رو تغییر نمی‌ده؛ فقط `commodity_channel` qualifier و
     پرچم `headline_underlying_divergence` رو تغذیه می‌کنه — پس این تفاوت در دیتاسورس
     می‌تونه گاهی همون پرچم/qualifier رو در نزدیکیِ آستانه (±20% یا +40%) جابه‌جا کنه،
     ولی هیچ‌وقت regime_code رو عوض نمی‌کنه.
  4. NFCI/ICSA ⇢ این‌ها در منبع اصلی «هفتگی» منتشر می‌شن. اگر ستون‌های شما از قبل
     forward-fill روزانه هستن (رایج در دیتاست‌های TradingView/Bloomberg-style)، این
     پورت با resample به W-FRI (آخرین مقدار هفته) دقیقاً همون سری هفتگی اصلی رو
     بازسازی می‌کنه و بعد میانگین ماهانه‌ی NFCI رو عیناً طبق فرمول نویسنده
     (`compute_nfci_monthly`) حساب می‌کنه. اگر پایه‌ی forward-fill شما هم‌راستا با
     روزهای انتشار واقعی (جمعه برای NFCI) نباشه، ممکنه چند صدم واحد اختلاف ایجاد بشه.
  5. HY OAS (BAMLH0A0HYM2) ⇢ در v1.1.0 **ورودیِ طبقه‌بندی نیست** (فقط corroboration
     نمایشی)؛ این پورت هم مثل اصلی از اون در تصمیم رژیم استفاده نمی‌کنه.

برای اعتبارسنجی: مخزن اصلی یک اسنپ‌شات منجمد از تاریخچه‌ی ماهانه (2003-01 → 2026-07)
با تمام مقادیر ورودی منتشر کرده: `docs/regime_history_v1.1.0.csv`. کافیه خروجی این پورت
رو برای چند ماه مشترک (مثلاً 2024-01 تا 2026-07) با اون فایل مقایسه کنید — اگر
cfnai_ma3 / nfci / pce_trimmed_12m / t10y2y / fedfunds مو‌به‌مو یکی بود، لایه‌ی ورودی
هم به‌درستی بازسازی شده.
"""

from __future__ import annotations

import json
import math
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
log = logging.getLogger("macroF.regime_model5")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# مسیرهای پیش‌فرض پروژه‌ی شما — در صورت نیاز override کنید
# ---------------------------------------------------------------------------
DEFAULT_CSV_PATH = Path(r"D:\project\database\macro_database.csv")
HISTORY_START    = "2003-01-01"          # همان نقطه‌ی شروع کد اصلی
THRESHOLDS_VERSION = "1.1.0"

# ===========================================================================
# ثابت‌ها — کپی عینی از config/thresholds.json v1.1.0
# (رجوع کنید به _meta.changelog در همان فایل برای دلیل هر عدد — چیزی این‌جا
#  تغییر داده نشده)
# ===========================================================================
G_PLUS_THRESHOLD   =  0.10
G_MINUS_THRESHOLD  = -0.50
I_PLUS_THRESHOLD   =  2.75   # درصد
I_MINUS_THRESHOLD  =  1.50   # درصد
NFCI_ACCOMMODATING = -0.50
NFCI_RESTRICTIVE   =  0.50
NFCI_ACUTE         =  1.50
SAHM_THRESHOLD     =  0.50
SOS_THRESHOLD       =  0.20
ICSA_CORR_THRESH   = 15.0    # درصد YoY
CISS_STRESS        =  0.30
VIX_ELEVATED       = 20.0
VIX_ACUTE          = 30.0
DOLLAR_STRONG      =  3.0    # درصد ۳ماهه
DOLLAR_WEAK        = -3.0
BRENT_SHOCK        = 20.0    # درصد YoY — قابل‌فهم برای commodity_channel qualifier
BRENT_DEMAND_DESTR = -20.0
HUD_BRENT_SHOCK    = 40.0    # درصد YoY — آستانه‌ی اختصاصیِ پرچم headline_underlying_divergence

# ---------------------------------------------------------------------------
# GRID رژیم‌ها و رنگ‌ها — کپی عینی
# ---------------------------------------------------------------------------
REGIME_GRID = {
    ("G_plus",    "I_minus"):   (1, "Disinflationary Expansion",   "Désinflation expansive"),
    ("G_plus",    "I_neutral"): (2, "Balanced Expansion",          "Expansion équilibrée"),
    ("G_plus",    "I_plus"):    (3, "Overheating",                 "Surchauffe"),
    ("G_neutral", "I_plus"):    (4, "Inflationary Pressure",       "Pression inflationniste"),
    ("G_minus",   "I_plus"):    (5, "Stagflation",                 "Stagflation"),
    ("G_minus",   "I_neutral"): (6, "Slowdown",                    "Ralentissement"),
    ("G_minus",   "I_minus"):   (7, "Disinflationary Contraction", "Contraction désinflationniste"),
    ("G_neutral", "I_neutral"): (8, "Transition / Mixed signals",  "Transition / Signaux mixtes"),
    ("G_neutral", "I_minus"):   (8, "Transition / Mixed signals",  "Transition / Signaux mixtes"),
}

COLOR_MAP = {
    1: {"zone": "#D8E2EC", "line": "#4A6B8A", "label": "#2D4256"},
    2: {"zone": "#DCE9DC", "line": "#5A8C5A", "label": "#2E542E"},
    3: {"zone": "#F4DDD8", "line": "#C73E2E", "label": "#8B2A1F"},
    4: {"zone": "#F4DDD8", "line": "#C73E2E", "label": "#8B2A1F"},
    5: {"zone": "#ECE2D2", "line": "#B8854A", "label": "#6E4E2B"},
    6: {"zone": "#E2E2DA", "line": "#7A7A6A", "label": "#3E3E32"},
    7: {"zone": "#C8D6E4", "line": "#2D4A6A", "label": "#1A2E42"},
    8: {"zone": "#E8E8E8", "line": "#9A9A9A", "label": "#4A4A4A"},
}

_OVERLAY_PREFIX_EN = {
    "accommodating": "under accommodating financial conditions — ",
    "neutral":       "",
    "restrictive":   "under restrictive financial conditions — ",
    "acute_stress":  "under acute financial stress — ",
}
_OVERLAY_PREFIX_FR = {
    "accommodating": "dans un contexte financier accommodant — ",
    "neutral":       "",
    "restrictive":   "dans un contexte de conditions financières restrictives — ",
    "acute_stress":  "sous stress financier aigu — ",
}

# ===========================================================================
# نگاشت ستون‌های macro_database.csv شما → سری‌های موردنیاز کد اصلی
# اگر اسم ستونی در دیتابیس شما فرق داشت، فقط همین دیکشنری رو ویرایش کنید —
# بقیه‌ی فایل نباید تغییر کنه.
# ===========================================================================
COLUMN_MAP = {
    "cfnai":       "CFNAI",
    "sahm":        "SAHMREALTIME",
    "icsa":        "ICSA",
    "pce_trimmed": "PCETRIM12M159SFRBDAL",
    "t5yifr":      "T5YIFR",
    "nfci":        "NFCI",
    "t10y2y":      "T10Y2Y",
    "fedfunds":    "FEDFUNDS",
    "us_cli":      "USALOLITOAASTSAM",
    "g7_cli":      "G7LOLITOAASTSAM",
    "dtwexbgs":    "DTWEXBGS",
    "vix":         "VIX",             # جایگزین محلیِ FRED VIXCLS
    "brent":       "DCOILBRENTEU",    # جایگزین محلیِ World Bank Brent / FRED MCOILBRENTEU
    "ciss":        "CISS_Eurozone",
    "hy_oas":      "BAMLH0A0HYM2",    # فقط corroboration — در تصمیم رژیم استفاده نمی‌شه
}

# ستون قیمتِ SP500 برای چارت پس‌زمینه‌ی رژیم‌ها (خودش ورودیِ طبقه‌بندی نیست)
SP500_COLUMN = "SP500"

# ===========================================================================
# بارگذاری CSV
# ===========================================================================

def load_raw_csv(csv_path: Path | str = DEFAULT_CSV_PATH) -> pd.DataFrame:
    """macro_database.csv را می‌خواند، بر اساس ستون Date ایندکس و مرتب می‌کند."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"macro_database.csv پیدا نشد: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    if "Date" not in df.columns:
        raise ValueError("ستون 'Date' در macro_database.csv پیدا نشد.")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").set_index("Date")
    df = df[~df.index.duplicated(keep="last")]
    return df


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """یک ستون را به‌صورت Series عددی و بدون NaN برمی‌گرداند؛ اگر نبود، Series خالی."""
    if name not in df.columns:
        log.warning(f"  ستون «{name}» در CSV پیدا نشد — این سری NaN در نظر گرفته می‌شود.")
        return pd.Series(dtype=float)
    s = pd.to_numeric(df[name], errors="coerce").dropna()
    return s


def resample_monthly_last(s: pd.Series) -> pd.Series:
    """معادل FredFetcher.get_resampled(freq='monthly') روی سری اصلی."""
    if s.empty:
        return s
    return s.resample("MS").last().dropna()


def resample_weekly_last(s: pd.Series) -> pd.Series:
    """معادل FredFetcher.get_resampled(freq='weekly') — آخرین مقدار هر هفته‌ی جمعه‌محور."""
    if s.empty:
        return s
    return s.resample("W-FRI").last().dropna()


def resample_monthly_mean(s: pd.Series) -> pd.Series:
    """میانگین تمام روزهای هر ماه تقویمی — برای بازسازیِ سری‌هایی که در منبع اصلی
    از قبل «میانگین ماهانه» هستن (مثل FRED MCOILBRENTEU) از یک سری اسپاتِ روزانه."""
    if s.empty:
        return s
    return s.resample("MS").mean().dropna()

# ===========================================================================
# PREPROCESSORها — کپی عینی فرمول‌های نویسنده
# ===========================================================================

def compute_cfnai_ma3(cfnai: pd.Series) -> pd.Series:
    return cfnai.rolling(window=3, min_periods=3).mean().rename("CFNAI_MA3")


def compute_nfci_monthly(nfci_weekly: pd.Series) -> pd.Series:
    """میانگین ماهانه‌ی مقادیر هفتگی NFCI (W-FRI → MS)."""
    if nfci_weekly.empty:
        return nfci_weekly
    return nfci_weekly.resample("MS").mean().rename("NFCI_monthly")


def compute_cli_delta_3m(cli: pd.Series) -> pd.Series:
    if cli.empty:
        return cli
    return (cli - cli.shift(3)).rename(str(cli.name) + "_3m_delta")


def compute_brent_yoy(brent: pd.Series) -> pd.Series:
    if brent.empty:
        return brent
    return brent.pct_change(periods=12).mul(100).rename("brent_yoy_pct")


def compute_dtwexbgs_3m_pct(s: pd.Series) -> pd.Series:
    if s.empty:
        return s
    return s.pct_change(periods=3).mul(100).rename("dtwexbgs_3m_pct")


def compute_icsa_4w_ma_yoy(icsa_weekly: pd.Series) -> pd.Series:
    """میانگین متحرک ۴هفته‌ای مطالبات بیکاری، سپس تغییر سالانه‌ی ۵۲هفته‌ای، ماهانه‌شده."""
    if icsa_weekly.empty:
        return icsa_weekly
    ma4 = icsa_weekly.rolling(4).mean()
    yoy = ma4.pct_change(periods=52).mul(100)
    return yoy.resample("MS").last().rename("icsa_4w_ma_yoy_pct")

# ===========================================================================
# دسترسی به آخرین مقدار موجود (پوشش تأخیر انتشار) — کپی عینی
# ===========================================================================

def get_latest_available(series: pd.Series, as_of: pd.Timestamp, max_lag: int = 3):
    """(value, is_lagged) را برمی‌گرداند؛ تا max_lag ماه به عقب جست‌وجو می‌کند."""
    if series is None or series.empty:
        return float("nan"), True
    for lag in range(max_lag + 1):
        target = (as_of - pd.DateOffset(months=lag)).replace(day=1)
        if target in series.index and not pd.isna(series[target]):
            return float(series[target]), lag > 0
    return float("nan"), True

# ===========================================================================
# طبقه‌بندی‌کننده‌ها (بدون حالت — هیسترزیس در RegimeStateMachine) — کپی عینی
# ===========================================================================

def classify_stress(nfci: float) -> str:
    """لایه‌ی استرس مالی — بدون هیسترزیس، به‌روزرسانی فوری."""
    if math.isnan(nfci):
        return "neutral"
    if nfci < NFCI_ACCOMMODATING:
        return "accommodating"
    if nfci < NFCI_RESTRICTIVE:
        return "neutral"
    if nfci < NFCI_ACUTE:
        return "restrictive"
    return "acute_stress"


def raw_classify_growth(cfnai_ma3: float, sahm: float, sos: float) -> str:
    """حالت رشد کاندید (پیش از هیسترزیس). گیت Sahm در RegimeStateMachine مدیریت می‌شود."""
    if math.isnan(cfnai_ma3):
        return "G_neutral"
    if cfnai_ma3 > G_PLUS_THRESHOLD:
        return "G_plus"
    if cfnai_ma3 < G_MINUS_THRESHOLD:
        return "G_minus"
    # باند G_neutral: ارتقای هشدار زودهنگام SOS
    if not math.isnan(sos) and sos >= SOS_THRESHOLD:
        return "G_minus"
    return "G_neutral"


def raw_classify_inflation(pce_12m: float) -> str:
    """حالت تورم کاندید (پیش از هیسترزیس)."""
    if math.isnan(pce_12m):
        return "I_neutral"
    if pce_12m > I_PLUS_THRESHOLD:
        return "I_plus"
    if pce_12m < I_MINUS_THRESHOLD:
        return "I_minus"
    return "I_neutral"


def classify_global_context(
    us_cli_delta: float,
    g7_cli_delta: float,
    dtwexbgs_3m: float,
    brent_yoy: float,
    vix: float,
    ciss: float,
) -> dict:
    def sign(x):
        return 1 if x > 0 else (-1 if x < 0 else 0)

    if (
        not math.isnan(us_cli_delta) and not math.isnan(g7_cli_delta)
        and sign(us_cli_delta) == sign(g7_cli_delta)
        and sign(us_cli_delta) != 0
    ):
        global_sync = "synchronized"
    else:
        global_sync = "divergent"

    qualifiers = []
    commodity_channel = "neutral"

    if not math.isnan(dtwexbgs_3m):
        if dtwexbgs_3m > DOLLAR_STRONG:
            qualifiers.append("dollar strengthening (tighter global financial conditions)")
        elif dtwexbgs_3m < DOLLAR_WEAK:
            qualifiers.append("dollar weakening (easing global financial conditions)")

    if not math.isnan(brent_yoy):
        if brent_yoy > BRENT_SHOCK:
            commodity_channel = "shock"
            qualifiers.append("commodity supply/demand shock")
        elif brent_yoy < BRENT_DEMAND_DESTR:
            commodity_channel = "demand_destruction"
            qualifiers.append("commodity demand destruction")

    if not math.isnan(vix):
        if vix > VIX_ACUTE:
            qualifiers.append("acute global market stress")
        elif vix > VIX_ELEVATED:
            qualifiers.append("elevated market volatility")

    if not math.isnan(ciss) and ciss > CISS_STRESS:
        qualifiers.append("European systemic stress elevated")

    return {
        "global_sync": global_sync,
        "global_qualifiers": qualifiers,
        "commodity_channel": commodity_channel,
    }

# ===========================================================================
# ماشین‌حالت — هیسترزیس ۲ماهه روی محورهای G و I + گیت Sahm — کپی عینی
# ===========================================================================

class RegimeStateMachine:
    """
    هیسترزیس تأیید ۲ماهه برای محور رشد و تورم. لایه‌ی استرس هیسترزیس ندارد.
    گیت Sahm — v1.1.0، EDGE-TRIGGERED: عبور روبه‌بالا از SAHM_THRESHOLD بلافاصله
    G_minus را فعال می‌کند (ورود بدون تأخیر)؛ ماندگاریِ آن سپس توسط ماشین‌حالت
    معمولی (کاندید CFNAI-MA3 + تأیید ۲ماهه) اداره می‌شود. برگشت Sahm زیر آستانه،
    گیت را برای عبور بعدی مجدداً مسلح می‌کند.
    """
    CONFIRMATION_MONTHS = 2

    def __init__(self, initial_g: str = "G_neutral", initial_i: str = "I_neutral"):
        self.current_growth = initial_g
        self.current_inflation = initial_i
        self._pending_g: Optional[str] = None
        self._pending_g_count: int = 0
        self._pending_i: Optional[str] = None
        self._pending_i_count: int = 0
        self._gate_level_prev: bool = False

    def update(self, candidate_g: str, candidate_i: str, sahm: float):
        gate_level = not math.isnan(sahm) and sahm >= SAHM_THRESHOLD
        gate_edge = gate_level and not self._gate_level_prev
        self._gate_level_prev = gate_level
        if gate_edge:
            self.current_growth = "G_minus"
            self._pending_g = None
            self._pending_g_count = 0
        else:
            self._update_axis_g(candidate_g)
        self._update_axis_i(candidate_i)
        return self.current_growth, self.current_inflation

    def _update_axis_g(self, candidate: str) -> None:
        if candidate == self.current_growth:
            self._pending_g = None
            self._pending_g_count = 0
        elif candidate == self._pending_g:
            self._pending_g_count += 1
            if self._pending_g_count >= self.CONFIRMATION_MONTHS:
                self.current_growth = candidate
                self._pending_g = None
                self._pending_g_count = 0
        else:
            self._pending_g = candidate
            self._pending_g_count = 1

    def _update_axis_i(self, candidate: str) -> None:
        if candidate == self.current_inflation:
            self._pending_i = None
            self._pending_i_count = 0
        elif candidate == self._pending_i:
            self._pending_i_count += 1
            if self._pending_i_count >= self.CONFIRMATION_MONTHS:
                self.current_inflation = candidate
                self._pending_i = None
                self._pending_i_count = 0
        else:
            self._pending_i = candidate
            self._pending_i_count = 1

# ===========================================================================
# RESOLVER — کپی عینی
# ===========================================================================

def resolve_regime(
    confirmed_g: str,
    confirmed_i: str,
    stress: str,
    global_ctx: dict,
    brent_yoy: float,
) -> dict:
    code, name_en, name_fr = REGIME_GRID.get(
        (confirmed_g, confirmed_i), (8, "Transition / Mixed signals", "Transition / Signaux mixtes")
    )
    full_en = _OVERLAY_PREFIX_EN.get(stress, "") + name_en
    full_fr = _OVERLAY_PREFIX_FR.get(stress, "") + name_fr

    hud = (
        confirmed_i in ("I_neutral", "I_minus")
        and not math.isnan(brent_yoy)
        and brent_yoy > HUD_BRENT_SHOCK
    )

    colors = COLOR_MAP.get(code, COLOR_MAP[8])
    return {
        "regime_code":                    code,
        "regime_name_EN":                 name_en,
        "regime_name_FR":                 name_fr,
        "full_label_EN":                  full_en,
        "full_label_FR":                  full_fr,
        "headline_underlying_divergence": hud,
        "color_zone_hex":                 colors["zone"],
        "color_line_hex":                 colors["line"],
        "color_label_hex":                colors["label"],
    }

# ===========================================================================
# LocalDataBundle — معادلِ محلیِ DataBundle اصلی (به‌جای fetch از FRED/ECB/Richmond
# Fed، همه‌چیز از دیتافریمِ CSV شما بازسازی می‌شود؛ فرمول‌ها و فرکانس‌ها عیناً حفظ شده)
# ===========================================================================

class LocalDataBundle:
    def __init__(self, df: pd.DataFrame, column_map: dict = COLUMN_MAP):
        cm = column_map
        log.info("در حال ساخت سری‌ها از macro_database.csv ...")

        self.cfnai        = resample_monthly_last(_col(df, cm["cfnai"]))
        self.cfnai_ma3     = compute_cfnai_ma3(self.cfnai)

        self.sahmrealtime  = resample_monthly_last(_col(df, cm["sahm"]))

        icsa_daily          = _col(df, cm["icsa"])
        self.icsa_weekly    = resample_weekly_last(icsa_daily)
        self.icsa_yoy        = compute_icsa_4w_ma_yoy(self.icsa_weekly)

        self.pce_trimmed   = resample_monthly_last(_col(df, cm["pce_trimmed"]))
        self.t5yifr        = resample_monthly_last(_col(df, cm["t5yifr"]))

        nfci_daily          = _col(df, cm["nfci"])
        self.nfci_weekly    = resample_weekly_last(nfci_daily)
        self.nfci_monthly  = compute_nfci_monthly(self.nfci_weekly)

        self.t10y2y        = resample_monthly_last(_col(df, cm["t10y2y"]))
        self.fedfunds      = resample_monthly_last(_col(df, cm["fedfunds"]))

        self.us_cli        = resample_monthly_last(_col(df, cm["us_cli"]))
        self.g7_cli        = resample_monthly_last(_col(df, cm["g7_cli"]))
        self.us_cli_delta  = compute_cli_delta_3m(self.us_cli)
        self.g7_cli_delta  = compute_cli_delta_3m(self.g7_cli)

        self.dtwexbgs      = resample_monthly_last(_col(df, cm["dtwexbgs"]))
        self.dtwexbgs_3m   = compute_dtwexbgs_3m_pct(self.dtwexbgs)

        self.vix           = resample_monthly_last(_col(df, cm["vix"]))

        # SOS (Richmond Fed) — در دیتاست شما موجود نیست. کد اصلی هم برای این حالت
        # مسیر graceful-degradation دارد (Series خالی → sos همیشه NaN).
        self.sos_weekly    = pd.Series(dtype=float)

        ciss_daily          = _col(df, cm["ciss"])
        self.ciss_monthly  = (
            ciss_daily.resample("MS").mean() if not ciss_daily.empty else pd.Series(dtype=float)
        )

        # نکته‌ی مهم: منبع اصلی نویسنده برای برنت یک سریِ ماهانه‌ست (World Bank CMO یا
        # fallback به FRED MCOILBRENTEU که خودش میانگینِ ماهانه‌ی از‌پیش‌محاسبه‌شده‌ست).
        # چون شما فقط اسپاتِ روزانه (DCOILBRENTEU) دارید، «آخرین روز ماه» یک نقطه‌ی
        # پرنوسانه و می‌تونه به‌شدت از میانگین ماهانه فاصله بگیره (در مقایسه با فایل
        # مرجع نویسنده تا ۲۰۰+ واحد اختلاف در brent_yoy_pct دیده شد). میانگینِ تمام
        # روزهای هر ماه، تقریبِ بسیار نزدیک‌تری به MCOILBRENTEU‌ه.
        brent_daily          = _col(df, cm["brent"])
        self.brent_monthly  = resample_monthly_mean(brent_daily)
        self.brent_yoy      = compute_brent_yoy(self.brent_monthly)

        self.hy_oas         = resample_monthly_last(_col(df, cm["hy_oas"]))

        log.info("سری‌ها آماده شدند.")

    def get_month_inputs(self, month: pd.Timestamp) -> dict:
        def g(series, lag=3):
            val, _ = get_latest_available(series, month, lag)
            return val

        sos_val = float("nan")
        if not self.sos_weekly.empty:
            mask = (self.sos_weekly.index >= month) & (
                self.sos_weekly.index <= month + pd.offsets.MonthEnd(0)
            )
            subset = self.sos_weekly[mask]
            if not subset.empty:
                sos_val = float(subset.iloc[-1])

        return {
            "cfnai_ma3":          g(self.cfnai_ma3),
            "sahmrealtime":       g(self.sahmrealtime),
            "sos":                sos_val,
            "pce_trimmed_12m":    g(self.pce_trimmed),
            "t5yifr":             g(self.t5yifr),
            "nfci":               g(self.nfci_monthly),
            "hy_oas_bps":         g(self.hy_oas) if not self.hy_oas.empty else float("nan"),
            "t10y2y":             g(self.t10y2y),
            "fedfunds":           g(self.fedfunds),
            "usaloli_3m_delta":   g(self.us_cli_delta),
            "g7loli_3m_delta":    g(self.g7_cli_delta),
            "dtwexbgs_3m_pct":    g(self.dtwexbgs_3m),
            "brent_yoy_pct":      g(self.brent_yoy),
            "vixcls":             g(self.vix),
            "icsa_4w_ma_yoy_pct": g(self.icsa_yoy),
            "ciss":               g(self.ciss_monthly),
        }

# ===========================================================================
# HISTORY RUNNER — کپی عینی منطق حلقه‌ی اصلی
# ===========================================================================

def run_history(bundle: LocalDataBundle, start_date: str = HISTORY_START,
                 end_date: Optional[str] = None) -> pd.DataFrame:
    start_ts = pd.Timestamp(start_date)
    if end_date is not None:
        end_ts = pd.Timestamp(end_date).replace(day=1)
    else:
        end_ts = pd.Timestamp.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    months = pd.date_range(start=start_ts, end=end_ts, freq="MS")

    sm = RegimeStateMachine()
    rows = []

    for month in months:
        inputs = bundle.get_month_inputs(month)
        candidate_g = raw_classify_growth(
            inputs["cfnai_ma3"], inputs["sahmrealtime"], inputs["sos"]
        )
        candidate_i = raw_classify_inflation(inputs["pce_trimmed_12m"])
        sahm = inputs["sahmrealtime"]
        if math.isnan(sahm):
            sahm = 0.0

        confirmed_g, confirmed_i = sm.update(candidate_g, candidate_i, sahm)
        stress = classify_stress(inputs["nfci"])
        global_ctx = classify_global_context(
            inputs["usaloli_3m_delta"], inputs["g7loli_3m_delta"],
            inputs["dtwexbgs_3m_pct"], inputs["brent_yoy_pct"],
            inputs["vixcls"], inputs.get("ciss", float("nan")),
        )
        resolved = resolve_regime(
            confirmed_g, confirmed_i, stress, global_ctx, inputs["brent_yoy_pct"]
        )
        icsa_ok = (
            not math.isnan(inputs.get("icsa_4w_ma_yoy_pct", float("nan")))
            and inputs["icsa_4w_ma_yoy_pct"] > ICSA_CORR_THRESH
        )

        data_quality = "full" if month >= pd.Timestamp("2003-01-01") else "degraded"

        rows.append({
            "date":                            month.strftime("%Y-%m-%d"),
            "regime_code":                     resolved["regime_code"],
            "regime_name_EN":                  resolved["regime_name_EN"],
            "regime_name_FR":                  resolved["regime_name_FR"],
            "full_label_EN":                   resolved["full_label_EN"],
            "full_label_FR":                   resolved["full_label_FR"],
            "growth_state":                    confirmed_g,
            "inflation_state":                 confirmed_i,
            "stress_overlay":                  stress,
            "global_sync":                     global_ctx["global_sync"],
            "cfnai_ma3":                       _f(inputs.get("cfnai_ma3")),
            "sahmrealtime":                    _f(inputs.get("sahmrealtime")),
            "sos":                             _f(inputs.get("sos")),
            "pce_trimmed_12m":                 _f(inputs.get("pce_trimmed_12m")),
            "t5yifr":                          _f(inputs.get("t5yifr")),
            "nfci":                            _f(inputs.get("nfci")),
            "t10y2y":                          _f(inputs.get("t10y2y")),
            "fedfunds":                        _f(inputs.get("fedfunds")),
            "dtwexbgs_3m_pct":                 _f(inputs.get("dtwexbgs_3m_pct")),
            "brent_yoy_pct":                   _f(inputs.get("brent_yoy_pct")),
            "headline_underlying_divergence":  resolved["headline_underlying_divergence"],
            "thresholds_version":              THRESHOLDS_VERSION,
            "data_quality":                    data_quality,
            "color_zone_hex":                  resolved["color_zone_hex"],
            "color_line_hex":                  resolved["color_line_hex"],
            "color_label_hex":                 resolved["color_label_hex"],
            # ستون‌های اضافه (خارج از schema اصلی، برای شفافیت نگه‌داشته شده)
            "global_qualifiers":               json.dumps(global_ctx["global_qualifiers"]),
            "hy_oas_bps":                      _f(inputs.get("hy_oas_bps")),
            "icsa_4w_ma_yoy_pct":              _f(inputs.get("icsa_4w_ma_yoy_pct")),
            "icsa_corroboration_triggered":    icsa_ok,
        })

    core_cols = [
        "date", "regime_code", "regime_name_EN", "regime_name_FR",
        "full_label_EN", "full_label_FR",
        "growth_state", "inflation_state", "stress_overlay", "global_sync",
        "cfnai_ma3", "sahmrealtime", "sos", "pce_trimmed_12m", "t5yifr",
        "nfci", "t10y2y", "fedfunds",
        "dtwexbgs_3m_pct", "brent_yoy_pct",
        "headline_underlying_divergence", "thresholds_version", "data_quality",
        "color_zone_hex", "color_line_hex", "color_label_hex",
        "global_qualifiers", "icsa_4w_ma_yoy_pct", "icsa_corroboration_triggered",
        "hy_oas_bps",
    ]
    out = pd.DataFrame(rows)
    return out[[c for c in core_cols if c in out.columns]]

# ===========================================================================
# HELPERS
# ===========================================================================

def _f(val) -> Optional[float]:
    """float → round(4) یا None برای NaN."""
    if val is None:
        return None
    try:
        v = float(val)
        return None if math.isnan(v) else round(v, 4)
    except (TypeError, ValueError):
        return None

# ===========================================================================
# API سطح‌بالا — این‌ها را از بقیه‌ی صفحات Streamlit پروژه import کنید
# ===========================================================================

def compute_regime_history(
    csv_path: Path | str = DEFAULT_CSV_PATH,
    start_date: str = HISTORY_START,
    end_date: Optional[str] = None,
    column_map: dict = COLUMN_MAP,
) -> pd.DataFrame:
    """کل تاریخچه‌ی ماهانه‌ی رژیم را از macro_database.csv می‌سازد و DataFrame برمی‌گرداند."""
    df = load_raw_csv(csv_path)
    bundle = LocalDataBundle(df, column_map=column_map)
    return run_history(bundle, start_date=start_date, end_date=end_date)


def get_current_regime(history_df: pd.DataFrame) -> dict:
    """آخرین ردیف تاریخچه را به قالب regime_current.json (خروجی اصلی نویسنده) تبدیل می‌کند."""
    if history_df.empty:
        raise ValueError("history_df خالی است — ابتدا compute_regime_history را اجرا کنید.")
    latest = history_df.iloc[-1]

    lagged_candidates = [
        "cfnai_ma3", "sahmrealtime", "pce_trimmed_12m", "t5yifr", "nfci",
        "t10y2y", "fedfunds", "dtwexbgs_3m_pct", "brent_yoy_pct", "icsa_4w_ma_yoy_pct",
    ]
    lagged = [c for c in lagged_candidates if pd.isna(latest.get(c))]
    freshness = "lagged" if lagged else "current"

    return {
        "regime_name_EN":                  latest["regime_name_EN"],
        "regime_name_FR":                  latest["regime_name_FR"],
        "regime_code":                     int(latest["regime_code"]),
        "growth_state":                    latest["growth_state"],
        "inflation_state":                 latest["inflation_state"],
        "stress_overlay":                  latest["stress_overlay"],
        "full_label_EN":                   latest["full_label_EN"],
        "full_label_FR":                   latest["full_label_FR"],
        "global_sync":                     latest["global_sync"],
        "global_qualifiers":               json.loads(latest["global_qualifiers"])
                                            if isinstance(latest.get("global_qualifiers"), str) else [],
        "headline_underlying_divergence":  bool(latest["headline_underlying_divergence"]),
        "color_zone_hex":                  latest["color_zone_hex"],
        "color_line_hex":                  latest["color_line_hex"],
        "color_label_hex":                 latest["color_label_hex"],
        "data_as_of":                      latest["date"],
        "computed_at":                     datetime.now(timezone.utc).isoformat(),
        "thresholds_version":              THRESHOLDS_VERSION,
        "data_freshness":                  freshness,
        "lagged_inputs":                   lagged,
        "icsa_corroboration_triggered":    bool(latest.get("icsa_corroboration_triggered", False)),
    }


def save_outputs(history_df: pd.DataFrame, current: dict, output_dir: Path | str) -> None:
    """اختیاری: خروجی را دقیقاً مثل ریپوی اصلی (regime_history.csv / regime_current.json) ذخیره می‌کند."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    history_df.to_csv(output_dir / "regime_history.csv", index=False)
    with open(output_dir / "regime_current.json", "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False, default=str)
    log.info(f"ذخیره شد → {output_dir}")

# ===========================================================================
# لایه‌ی Streamlit — show() نقطه‌ی ورودیِ استانداردِ پروژه‌ی شماست
# (همون الگویی که سایر فایل‌های macroF هم استفاده می‌کنن: ماژول.show())
# هیچ‌چیز روی دیسک ذخیره نمی‌شه؛ st.cache_data فقط در حافظه‌ی سشن Streamlit
# نگه می‌داره تا با هر rerun صفحه، کل CSV دوباره پردازش نشه.
# ===========================================================================

try:
    import streamlit as st
    _HAS_ST = True
except ImportError:
    st = None
    _HAS_ST = False


def _cache_data(func):
    """اگر streamlit در دسترس بود cache می‌کند، وگرنه بدون تغییر برمی‌گرداند."""
    if _HAS_ST:
        return st.cache_data(show_spinner="در حال محاسبه‌ی رژیم کلان...")(func)
    return func


@_cache_data
def _cached_compute_history(csv_path: str, start_date: str, end_date: Optional[str],
                             _csv_mtime: float) -> pd.DataFrame:
    """پوشش cache-friendly برای compute_regime_history. _csv_mtime فقط برای این‌جاست
    که وقتی macro_database.csv عوض شد، cache خودکار باطل بشه — چیزی ذخیره نمی‌کند."""
    return compute_regime_history(csv_path=csv_path, start_date=start_date, end_date=end_date)


@_cache_data
def _cached_load_sp500(csv_path: str, column: str, _csv_mtime: float) -> pd.Series:
    """قیمت روزانه‌ی خامِ SP500 را برای چارت پس‌زمینه‌ی رژیم‌ها می‌خواند (فقط نمایش،
    در تصمیم رژیم استفاده نمی‌شود). چیزی روی دیسک نمی‌نویسد."""
    df = load_raw_csv(csv_path)
    return _col(df, column)


def show(
    csv_path: Path | str = DEFAULT_CSV_PATH,
    start_date: str = HISTORY_START,
    end_date: Optional[str] = None,
    sp500_column: str = SP500_COLUMN,
) -> None:
    """نقطه‌ی ورودی که بقیه‌ی پروژه صدا می‌زند: regime_model5.show().
    فقط در صفحه نمایش می‌دهد — هیچ فایلی نمی‌نویسد."""
    if not _HAS_ST:
        raise RuntimeError("streamlit نصب نیست؛ show() فقط داخل یک اپ Streamlit معنا دارد.")

    csv_path = Path(csv_path)
    if not csv_path.exists():
        st.error(f"فایل macro_database.csv پیدا نشد:\n`{csv_path}`")
        return

    try:
        mtime = csv_path.stat().st_mtime
        history = _cached_compute_history(str(csv_path), start_date, end_date, mtime)
        current = get_current_regime(history)
        sp500 = _cached_load_sp500(str(csv_path), sp500_column, mtime)
    except Exception as e:
        log.exception("regime_model5.show() failed")
        st.error(f"خطا در محاسبه‌ی رژیم کلان: {e}")
        return

    render_streamlit(history, current)
    render_regime_grid(current)
    render_sp500_regime_chart(history, sp500)


def render_streamlit(history_df: pd.DataFrame, current: Optional[dict] = None) -> None:
    """یک نمای ساده از رژیم فعلی + تاریخچه در Streamlit رسم می‌کند. از هر صفحه‌ی
    دیگری از پروژه می‌توانید صدا بزنید: render_streamlit(history_df)."""
    try:
        import streamlit as st
    except ImportError:
        log.warning("streamlit نصب نیست — render_streamlit صرف‌نظر شد.")
        return

    if current is None:
        current = get_current_regime(history_df)

    st.markdown(
        f"""
        <div style="padding:14px 18px;border-radius:10px;
                    background:{current['color_zone_hex']};
                    border:1px solid {current['color_line_hex']};">
          <div style="font-size:0.8rem;color:{current['color_label_hex']};opacity:.8;">
            US Macro Regime — as of {current['data_as_of']}
          </div>
          <div style="font-size:1.3rem;font-weight:700;color:{current['color_label_hex']};">
            {current['full_label_EN']}
          </div>
          <div style="font-size:0.85rem;color:{current['color_label_hex']};opacity:.85;">
            Growth: {current['growth_state']} · Inflation: {current['inflation_state']} ·
            Stress: {current['stress_overlay']} · Global: {current['global_sync']}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if current["global_qualifiers"]:
        st.caption(" · ".join(current["global_qualifiers"]))
    if current["headline_underlying_divergence"]:
        st.warning("headline_underlying_divergence فعال است — واگرایی برنت YoY از تورم پایه.")
    if current["data_freshness"] == "lagged":
        st.caption(f"ورودی‌های تأخیردار: {', '.join(current['lagged_inputs'])}")

    # همون ستون‌ها و همون ترتیبِ ستون‌های docs/regime_history_v1.1.0.csv نویسنده —
    # برای مقایسه‌ی سطر‌به‌سطر راحت‌تر. کل بازه نمایش داده می‌شه، نه فقط چند ماه آخر.
    _compare_cols = [
        "date", "regime_code", "regime_name_EN", "regime_name_FR",
        "growth_state", "inflation_state", "stress_overlay", "global_sync",
        "cfnai_ma3", "sahmrealtime", "sos", "pce_trimmed_12m", "t5yifr",
        "nfci", "t10y2y", "fedfunds", "dtwexbgs_3m_pct", "brent_yoy_pct",
        "headline_underlying_divergence", "thresholds_version", "data_quality",
        "global_qualifiers", "icsa_4w_ma_yoy_pct", "icsa_corroboration_triggered",
    ]
    _compare_cols = [c for c in _compare_cols if c in history_df.columns]
    st.caption(f"کل بازه‌ی محاسبه‌شده: {len(history_df)} ماه "
               f"({history_df['date'].iloc[0]} تا {history_df['date'].iloc[-1]})")
    st.dataframe(
        history_df[_compare_cols],
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------------------------
# Growth × Inflation Grid — همون جدول ۳×۳ که در docs/methodology.md هست، با
# رنگِ هر خانه دقیقاً از همون COLOR_MAP که در بج رژیم فعلی و در چارت SP500 هم
# استفاده می‌شه (تا رنگ‌ها در کل صفحه یکدست بمونن)
# ---------------------------------------------------------------------------

_GRID_ROWS = [("G_plus", "G+ (above trend)"), ("G_neutral", "G= (on trend)"), ("G_minus", "G- (contracting)")]
_GRID_COLS = [("I_minus", "I− (Disinflation)"), ("I_neutral", "I= (Stable)"), ("I_plus", "I+ (Acceleration)")]
_GRID_HEAD_STYLE = (
    "background:#EDE6D6;color:#4A4A3A;font-family:'Courier New',monospace;"
    "font-size:0.72rem;letter-spacing:.03em;padding:10px 8px;text-align:left;border-radius:4px;"
)


def _regime_grid_html(current_growth: str, current_inflation: str) -> str:
    head = "".join(f'<th style="{_GRID_HEAD_STYLE}">{label}</th>' for _, label in _GRID_COLS)
    body = ""
    for g_key, g_label in _GRID_ROWS:
        row = f'<th style="{_GRID_HEAD_STYLE}">{g_label}</th>'
        for i_key, _ in _GRID_COLS:
            code, name_en, _ = REGIME_GRID.get((g_key, i_key), (8, "Transition / Mixed signals", ""))
            c = COLOR_MAP.get(code, COLOR_MAP[8])
            is_current = (g_key == current_growth and i_key == current_inflation)
            weight = "font-style:italic;font-weight:400;" if code == 8 else "font-weight:700;"
            border = f"3px solid {c['line']}" if is_current else f"1px solid {c['line']}66"
            glow = f"box-shadow:0 0 0 2px {c['line']}44;" if is_current else ""
            marker = (
                f'<div style="font-size:0.65rem;margin-top:5px;opacity:.85;">● موقعیت فعلی</div>'
                if is_current else ""
            )
            row += (
                f'<td style="background:{c["zone"]};border:{border};color:{c["label"]};'
                f'padding:16px 10px;text-align:center;border-radius:5px;{weight}{glow}">'
                f'{name_en}{marker}</td>'
            )
        body += f"<tr>{row}</tr>"
    return (
        '<table style="width:100%;border-collapse:separate;border-spacing:6px;margin-top:6px;">'
        f'<tr><th style="{_GRID_HEAD_STYLE}">Growth ⁄ Inflation</th>{head}</tr>{body}</table>'
    )


def render_regime_grid(current: dict) -> None:
    """جدول ۳×۳ Growth×Inflation را رسم می‌کند و خانه‌ی رژیمِ فعلی را مشخص می‌کند.
    رنگ هر خانه از همون COLOR_MAP خانواده‌ی بج/چارته — چیزی جدا تعریف نشده."""
    if not _HAS_ST:
        log.warning("streamlit نصب نیست — render_regime_grid صرف‌نظر شد.")
        return
    st.markdown("##### Growth × Inflation Regime Grid")
    st.markdown(_regime_grid_html(current["growth_state"], current["inflation_state"]),
                unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# چارت SP500 با پس‌زمینه‌ی رنگیِ رژیم — رنگ هر باند دقیقاً همون color_zone_hex
# از COLOR_MAP هست، همون که در بج بالا و در جدول Growth×Inflation استفاده شد.
# ---------------------------------------------------------------------------

def render_sp500_regime_chart(history_df: pd.DataFrame, sp500: pd.Series,
                               log_scale: bool = True, band_opacity: float = 0.85) -> None:
    """قیمت SP500 را با نوارهای پس‌زمینه‌ی رنگیِ رژیم رسم می‌کند — تعاملی با Plotly
    (زوم/پن). چیزی ذخیره نمی‌کند. رنگ نوارها همون color_zone_hex از COLOR_MAP هست
    (همون‌که در بج و جدول بالا استفاده شد)."""
    if not _HAS_ST:
        log.warning("streamlit نصب نیست — render_sp500_regime_chart صرف‌نظر شد.")
        return
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("برای این چارت به plotly نیاز است: `pip install plotly`")
        return

    if sp500 is None or sp500.empty:
        st.warning(f"ستون «{SP500_COLUMN}» در macro_database.csv پیدا نشد یا خالی است.")
        return
    if history_df.empty:
        return

    hist = history_df.copy()
    hist["date"] = pd.to_datetime(hist["date"])
    start_bound = hist["date"].min()
    end_bound = hist["date"].max() + pd.offsets.MonthEnd(1)

    sp = sp500.sort_index()
    sp = sp[(sp.index >= start_bound) & (sp.index <= end_bound)]
    if sp.empty:
        st.warning("در بازه‌ی محاسبه‌شده هیچ داده‌ی SP500‌ای پیدا نشد.")
        return

    st.markdown("##### S&P 500 — با پس‌زمینه‌ی رژیم کلان")

    fig = go.Figure()

    # خط قیمت SP500 — با تاریخ به‌صورت رشته‌ی ISO (نه Timestamp خام) تا محور x
    # همیشه به‌عنوان «تاریخ» تشخیص داده بشه، نه عددی (باگ اسکرین‌شاتِ قبلی همین بود)
    fig.add_trace(go.Scatter(
        x=sp.index.strftime("%Y-%m-%d").tolist(), y=sp.values.tolist(), mode="lines",
        line=dict(color="#1a1a1a", width=1.3),
        name="S&P 500",
        hovertemplate="%{x}<br>S&P 500: %{y:,.0f}<extra></extra>",
    ))

    # نوارهای پس‌زمینه‌ی رژیم — با fig.add_vrect (به‌جای ساختن دستیِ shapes) چون این
    # تابع خودش نوع محور x رو درست تشخیص می‌ده و با x0/x1 رشته‌ای هم درست کار می‌کنه
    for _, row in hist.iterrows():
        seg_start = row["date"].strftime("%Y-%m-%d")
        seg_end = (row["date"] + pd.offsets.MonthEnd(1)).strftime("%Y-%m-%d")
        fig.add_vrect(
            x0=seg_start, x1=seg_end,
            fillcolor=row["color_zone_hex"], opacity=band_opacity,
            line_width=0.4, line_color=row["color_line_hex"],
            layer="below",
        )

    # لجندِ سفارشی برای نوارها — چون vrectها خودشون در legend پلاتلی ظاهر نمی‌شن،
    # برای هر رژیمی که واقعاً در بازه دیده شده یک trace نامرئی با همون رنگ (+ حاشیه‌ی
    # پررنگ‌تر برای خوانایی بهتر) اضافه می‌کنیم تا در legend بیاد
    seen = {}
    for _, row in hist.iterrows():
        seen.setdefault(row["regime_code"],
                         (row["regime_name_EN"], row["color_zone_hex"], row["color_line_hex"]))
    for code, (name, zone_hex, line_hex) in sorted(seen.items()):
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(size=13, symbol="square", color=zone_hex,
                        line=dict(width=1.5, color=line_hex)),
            name=name, hoverinfo="skip", showlegend=True,
        ))

    fig.update_layout(
        xaxis=dict(
            type="date",  # صراحتاً date — دیگه به auto-detect وابسته نیست
            range=[start_bound.strftime("%Y-%m-%d"), end_bound.strftime("%Y-%m-%d")],
            title=None,
            gridcolor="rgba(0,0,0,0.08)",
            rangeslider=dict(visible=False),
        ),
        yaxis=dict(
            type="log" if log_scale else "linear",
            title="S&P 500 (log scale)" if log_scale else "S&P 500",
            gridcolor="rgba(0,0,0,0.10)",
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        height=560,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=12, color="#1a1a1a"), bgcolor="rgba(255,255,255,0.9)",
                    bordercolor="rgba(0,0,0,0.15)", borderwidth=1),
        dragmode="zoom",
    )

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})


# ===========================================================================
# اجرای مستقیم (تست/دیباگ خارج از Streamlit)
# ===========================================================================

if __name__ == "__main__":
    history = compute_regime_history()
    current = get_current_regime(history)
    print(f"رژیم فعلی: {current['full_label_EN']}  (as of {current['data_as_of']})")
    print(f"تعداد ماه‌های محاسبه‌شده: {len(history)}")
