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
سنجه‌ی تورم (TDTF_IEI) به‌جای EXPINF2YR انتخاب شده چون فرکانس بالاتری دارد
و به یک سری تورم انتظاری ۲ساله در بلومبرگ (که دسترسی مستقیم نداریم) نزدیک‌تر
است.

*** تغییر بزرگ نسخه‌ی فعلی: از کوادرانت آستانه‌ی‌ثابت به HMM ***
--------------------------------------------------------------
نسخه‌ی قبلی این فایل، رژیم را با یک آستانه‌ی ثابت (علامت سیگنال: مثبت/منفی)
تشخیص می‌داد. این نسخه به‌جایش از یک Hidden Markov Model دوحالته (Gaussian)
روی هر محور (credit، inflation) به‌طور مستقل استفاده می‌کند:

  - چرا ۲ حالت نه بیشتر: تعداد رژیم‌های ترکیبی (Reflation/Stagflation/
    Goldilocks/Recession) دقیقاً ۴ باقی می‌ماند (۲×۲)، پس کل UI/کارت‌های
    کوادرانت/جدول آماری دست‌نخورده می‌ماند — فقط منطق classify() عوض شده.
  - لوک‌بک: طبق تصمیم مشترک، یک عدد واحد برای هر دو محور (credit و
    inflation) به‌کار می‌رود؛ دیگر دو ورودی جدا در UI نیست.
  - train/test 80/20: HMM هر محور روی ۸۰٪ اولِ کل تاریخچه‌ی موجود (نه بازه‌ی
    فیلترشده‌ی UI) فیت می‌شود؛ خط عمودی نقطه‌کن روی چارت این مرز را نشان
    می‌دهد. این تقسیم فقط برای *نمایش روی چارت* معنا دارد — جدول آماری
    (regime_statistics) و هر نمایش غیرپیش‌بینی دیگر از کل داده استفاده
    می‌کند.
  - دیکد: در همه‌جا (چه بخش train چه test) از احتمال فیلترشده‌ی رو-به-جلو
    (forward filtering، پیاده‌سازی دستی با الگوریتم forward استاندارد در
    فضای لگاریتمی) استفاده می‌شود، نه Viterbi/smoothing — چون این یک سیگنال
    زنده‌ی روز-به-روز است و نباید از اطلاعات آینده (حتی در بخش train) نشت
    کند. توابع داخلی/خصوصی hmmlearn استفاده نشده تا در برابر تغییر نسخه
    (تست‌شده روی hmmlearn==0.3.3) شکننده نباشد — فقط از پارامترهای عمومی
    مدل (means_, covars_, transmat_, startprob_) استفاده شده.
  - label switching: بعد از هر fit، حالت‌ها بر اساس میانگین (صعودی) مرتب
    می‌شوند تا «حالت ۰» همیشه معادل «سیگنال پایین‌تر» (آنالوگ c<0 در منطق
    قدیمی) باشد و نگاشت به ۴ اسم رژیم (classify_hmm) پایدار بماند.

نکات فنی دیگر (از نسخه‌ی قبلی، هنوز صادق)
--------------------------------------------
- هیچ‌جای این کد دیتابیس نوشته/تغییر داده نمی‌شود؛ فقط pd.read_csv
  (read-only). کش (load_database) با mtime فایل invalidate می‌شود.
- کلید session_state این صفحه namespace دار شده (regime1_start/end) تا
  با صفحات دیگر تداخل نکند.
- نکته‌ی قدیمی «classify() روی مقدار دقیقاً صفر به Recession می‌افتد» دیگر
  صادق نیست چون classify() حذف شده؛ معادلش الان این است: اگر احتمال دو
  حالت دقیقاً ۵۰/۵۰ باشد (خیلی نادر)، argmax اولین اندیس (حالت ۰) را
  برمی‌گرداند — تصمیم گرفته نشده این را عوض کنیم چون عملاً رخ نمی‌دهد.
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from hmmlearn.hmm import GaussianHMM
from scipy.stats import norm
from scipy.special import logsumexp

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
DEFAULT_INFLATION_COL = "TDTF_IEI"

LOOKBACK_MIN = 5
LOOKBACK_MAX = 60
LOOKBACK_STEP = 5
LOOKBACK_DEFAULT = 60

ZSCORE_WINDOW = 252  # ثابت، طبق تصمیم مشترک از UI قابل‌تنظیم نیست

# ستون بازار برای بند «بازدهی/نوسان روزانه‌ی هر رژیم» — طبق تصمیم مشترک: SP500.
# اگر دیتابیس این ستون را نداشته باشد، load_benchmark یک Series خالی
# برمی‌گرداند و بخش‌های مربوطه بی‌صدا از خروجی حذف می‌شوند (نه خطا).
BENCHMARK_COL = "SP500"

# --- تنظیمات HMM (طبق تصمیم مشترک) ---
N_HMM_STATES = 2
TRAIN_FRAC = 0.8            # ۸۰٪ اول تاریخچه = train، بقیه = test
N_HMM_RESTARTS = 10         # چند بار fit با seed متفاوت، بهترین log-likelihood نگه داشته می‌شود
HMM_RANDOM_STATE = 42
MIN_OBS_FOR_HMM = 50        # کمتر از این، فیت را بی‌معنی و ناپایدار می‌دانیم

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
# پورت‌شده عیناً از regime_model1.py — برای «بازدهی/نوسان روزانه‌ی هر رژیم»
# و «بازدهی هر زیربخش در هر رژیم». منطق HMM/محاسباتی این فایل دست‌نخورده.
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


def sector_regime_returns(valid: pd.DataFrame, sector_df: pd.DataFrame) -> pd.DataFrame:
    """میانگین بازدهی روزانه‌ی هر زیربخش (٪)، به تفکیک رژیم، محدود به
    بازه‌ی valid.index. یک سطر برای هر ۴ رژیم برمی‌گرداند، حتی اگه رژیمی
    توی این بازه رخ نداده باشه (NaN)."""
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
# 3) هسته‌ی HMM — فیت، دیکد رو-به-جلو، و نگاشت به ۴ رژیم
# ==========================================================================

@st.cache_data(show_spinner=False)
def fit_regime_hmm(
    train_signal: pd.Series,
    n_states: int = N_HMM_STATES,
    n_restarts: int = N_HMM_RESTARTS,
    random_state: int = HMM_RANDOM_STATE,
) -> GaussianHMM:
    """
    یک HMM با n_states حالت (Gaussian emission) را روی train_signal فیت
    می‌کند و مدل را برمی‌گرداند.

    - این تابع فقط روی داده‌ای که به آن پاس داده می‌شود fit می‌کند — تصمیم
      اینکه کدام بخش از تاریخچه «train» است، بیرون از این تابع (در
      _attach_hmm_regime) گرفته می‌شود.
    - چون Baum-Welch/EM به local optima حساس است، n_restarts بار با seed
      متفاوت fit می‌کنیم و بهترین log-likelihood را نگه می‌داریم.
    - بعد از fit، حالت‌ها بر اساس میانگین (صعودی) مرتب می‌شوند تا حالت ۰
      همیشه «سیگنال پایین‌تر» باشد (حل مشکل label switching).
    """
    train_data = train_signal.dropna().values.reshape(-1, 1)

    best_model, best_score = None, -np.inf
    for i in range(n_restarts):
        model = GaussianHMM(
            n_components=n_states,
            covariance_type="diag",
            n_iter=1000,
            random_state=random_state + i,
        )
        model.fit(train_data)
        score = model.score(train_data)
        if score > best_score:
            best_model, best_score = model, score

    order = np.argsort(best_model.means_.flatten())
    best_model.means_ = best_model.means_[order]
    # نکته: getter مربوط به covars_ برای covariance_type="diag" شکل
    # (n_components, n_dim, n_dim) برمی‌گرداند، ولی setter شکل فشرده‌ی
    # (n_components, n_dim) را انتظار دارد — بدون این reshape صریح، خطای
    # "'diag' covars must have shape (n_components, n_dim)" می‌گیریم.
    best_model.covars_ = best_model.covars_[order].reshape(n_states, -1)
    best_model.transmat_ = best_model.transmat_[order][:, order]
    best_model.startprob_ = best_model.startprob_[order]

    return best_model


def forward_filtered_proba(model: GaussianHMM, signal: pd.Series) -> pd.DataFrame:
    """
    احتمال فیلترشده‌ی رو-به-جلو: P(state_t | obs_1..obs_t) — یعنی حالت روز t
    فقط از روی داده‌های تا روز t محاسبه می‌شود، نه آینده (حتی اگر روز t در
    بازه‌ی train باشد).

    عمداً به‌جای model.predict_proba (که forward-backward/smoothing است و از
    آینده هم استفاده می‌کند)، الگوریتم forward استاندارد را با پارامترهای
    عمومی مدل (means_, covars_, startprob_, transmat_) پیاده‌سازی کرده‌ایم —
    این پارامترها بین نسخه‌های hmmlearn پایدارترند از متدهای خصوصی.
    """
    clean = signal.dropna()
    X = clean.values
    n_states = model.n_components
    means = model.means_.flatten()
    variances = model.covars_.flatten()  # covariance_type="diag", n_features=1

    log_emission = np.column_stack([
        norm.logpdf(X, loc=means[k], scale=np.sqrt(variances[k]))
        for k in range(n_states)
    ])
    log_startprob = np.log(model.startprob_ + 1e-300)
    log_transmat = np.log(model.transmat_ + 1e-300)

    T = len(X)
    log_alpha = np.zeros((T, n_states))
    log_alpha[0] = log_startprob + log_emission[0]
    log_alpha[0] -= logsumexp(log_alpha[0])

    for t in range(1, T):
        for j in range(n_states):
            log_alpha[t, j] = logsumexp(log_alpha[t - 1] + log_transmat[:, j]) + log_emission[t, j]
        log_alpha[t] -= logsumexp(log_alpha[t])

    filtered = np.exp(log_alpha)
    return pd.DataFrame(
        filtered, index=clean.index, columns=[f"state_{k}" for k in range(n_states)]
    )


def classify_hmm(credit_state, inflation_state):
    """نگاشت حالت‌های HMM (0=پایین/آرام، 1=بالا) به همان ۴ رژیم قدیمی —
    آنالوگ دقیق classify(c, i) که این نسخه جایگزینش کرده."""
    if pd.isna(credit_state) or pd.isna(inflation_state):
        return np.nan
    if credit_state == 0 and inflation_state == 1:
        return "Reflation"
    if credit_state == 1 and inflation_state == 1:
        return "Stagflation"
    if credit_state == 0 and inflation_state == 0:
        return "Goldilocks"
    return "Recession"  # credit_state == 1 and inflation_state == 0


def _attach_hmm_regime(out: pd.DataFrame) -> pd.DataFrame:
    """
    روی دو ستون CREDIT_SIGNAL و INFLATION_SIGNAL (که از قبل توسط
    compute_roc_signal یا compute_zscore_signal ساخته شده‌اند)، هرکدام جدا
    یک HMM دوحالته فیت می‌کند (روی TRAIN_FRAC اولِ تاریخچه‌ی مشترک هر دو
    ستون)، سپس احتمال فیلترشده‌ی رو-به-جلو را برای کل تاریخچه محاسبه و ستون
    Regime را اضافه می‌کند. Train_End_Date برای رسم خط جداکننده روی چارت
    نگه داشته می‌شود.
    """
    common_valid = out.dropna(subset=["CREDIT_SIGNAL", "INFLATION_SIGNAL"])
    # نکته: اگر این ستون را با np.nan مقداردهی کنیم، pandas آن را float64
    # می‌سازد و بعداً ریختن رشته‌های نام رژیم توی آن، در نسخه‌های جدید
    # pandas، به‌جای تبدیل خاموش به object، TypeError می‌دهد — پس از اول
    # صریحاً dtype=object می‌سازیم.
    out["Regime"] = pd.Series(np.nan, index=out.index, dtype=object)
    out["Train_End_Date"] = pd.NaT

    if len(common_valid) < MIN_OBS_FOR_HMM:
        return out

    n_train = max(int(len(common_valid) * TRAIN_FRAC), 20)
    train_end_date = common_valid.index[n_train - 1]

    credit_model = fit_regime_hmm(common_valid["CREDIT_SIGNAL"].loc[:train_end_date])
    inflation_model = fit_regime_hmm(common_valid["INFLATION_SIGNAL"].loc[:train_end_date])

    credit_proba = forward_filtered_proba(credit_model, common_valid["CREDIT_SIGNAL"])
    inflation_proba = forward_filtered_proba(inflation_model, common_valid["INFLATION_SIGNAL"])

    credit_state = credit_proba.values.argmax(axis=1)
    inflation_state = inflation_proba.values.argmax(axis=1)
    # اطمینانِ argmax — احتمالِ فیلترشده‌ی همون حالتی که برچسبِ روز از آن انتخاب
    # شده (نه فقط اینکه کدوم حالت برنده شده، بلکه چقدر با اطمینان برنده شده).
    credit_confidence = credit_proba.values.max(axis=1)
    inflation_confidence = inflation_proba.values.max(axis=1)
    regimes = [classify_hmm(c, i) for c, i in zip(credit_state, inflation_state)]

    out.loc[common_valid.index, "Regime"] = regimes
    out.loc[common_valid.index, "Credit_State"] = credit_state
    out.loc[common_valid.index, "Inflation_State"] = inflation_state
    out.loc[common_valid.index, "Credit_Confidence"] = credit_confidence
    out.loc[common_valid.index, "Inflation_Confidence"] = inflation_confidence
    out["Train_End_Date"] = train_end_date
    return out


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
    """طبق تصمیم مشترک: این جدول از کل داده‌ی موجود (train+test) استفاده
    می‌کند، بدون توجه به مرز train/test — آن مرز فقط برای نمایش روی چارت
    معناداره. اگر benchmark_ret داده بشه (سری بازدهی روزانه‌ی SP500، از
    پیش align نشده)، دو ستون اضافه می‌شن: میانگین بازدهی روزانه و نوسان
    روزانه (انحراف‌معیار خام، غیر سالانه‌شده) — پورت‌شده از regime_model1.py."""
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
#    نکته: لوک‌بک الان یک عدد واحد است (طبق تصمیم مشترک) برای هر دو محور
# ==========================================================================

def compute_roc_signal(df, credit_col, inflation_col, lookback: int) -> pd.DataFrame:
    out = _load_levels(df, credit_col, inflation_col)
    out["CREDIT_SIGNAL"] = out["CREDIT_BPS"].diff(lookback)
    out["INFLATION_SIGNAL"] = out["INFLATION_BPS"].diff(lookback)
    out = _attach_hmm_regime(out)
    out["Days_in_regime"] = _days_in_state(out["Regime"])
    return out


def compute_zscore_signal(df, credit_col, inflation_col, lookback: int,
                           zscore_window: int = ZSCORE_WINDOW) -> pd.DataFrame:
    out = _load_levels(df, credit_col, inflation_col)
    credit_roc = out["CREDIT_BPS"].diff(lookback)
    inflation_roc = out["INFLATION_BPS"].diff(lookback)
    out["CREDIT_SIGNAL"] = (
        (credit_roc - credit_roc.rolling(zscore_window, min_periods=30).mean())
        / credit_roc.rolling(zscore_window, min_periods=30).std()
    )
    out["INFLATION_SIGNAL"] = (
        (inflation_roc - inflation_roc.rolling(zscore_window, min_periods=30).mean())
        / inflation_roc.rolling(zscore_window, min_periods=30).std()
    )
    out = _attach_hmm_regime(out)
    out["Days_in_regime"] = _days_in_state(out["Regime"])
    return out


# ==========================================================================
# 5) رندر یک پنل کامل و مستقل (لوک‌بک مشترک، کارت‌ها، نمودار، آمار)
# ==========================================================================

def render_panel(raw, credit_col, inflation_col, start_date, end_date,
                  method_label, compute_fn, signal_unit, key_prefix,
                  benchmark_ret: pd.Series | None = None,
                  benchmark_prices: pd.Series | None = None,
                  sector_df: pd.DataFrame | None = None):
    st.markdown(f"### {method_label}")

    def _compact_lookback(container, label, widget_key):
        """لیبل و کادر عدد در یک ردیف."""
        lbl_col, inp_col = container.columns([3, 1], vertical_alignment="center")
        lbl_col.markdown(f"<div style='font-size:0.95rem;'>{label}</div>", unsafe_allow_html=True)
        return inp_col.number_input(
            label,
            min_value=LOOKBACK_MIN, max_value=LOOKBACK_MAX, value=LOOKBACK_DEFAULT, step=LOOKBACK_STEP,
            key=widget_key, label_visibility="collapsed",
        )

    # --- طبق تصمیم مشترک: یک لوک‌بک واحد برای هر دو محور (نه دو ورودی جدا) ---
    lookback = _compact_lookback(
        st, f"{method_label} Lookback (days) — shared for both axes", f"{key_prefix}_lookback"
    )

    df = compute_fn(raw, credit_col, inflation_col, int(lookback))
    df = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

    valid = df.dropna(subset=["Regime"])
    if valid.empty:
        st.warning("داده‌ای برای بازهٔ انتخاب‌شده با این لوک‌بک موجود نیست (یا داده برای فیت HMM کافی نیست).")
        return

    cur = valid.iloc[-1]
    train_end = df["Train_End_Date"].dropna().iloc[0] if df["Train_End_Date"].notna().any() else None

    # ---- کارت‌های خلاصه (واحد درست: bps یا σ) ----
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Regime", cur["Regime"])
    m2.metric(f"Credit Signal ({signal_unit})", f"{cur['CREDIT_SIGNAL']:.2f}")
    m3.metric(f"Inflation Signal ({signal_unit})", f"{cur['INFLATION_SIGNAL']:.2f}")
    m4.metric("Days in Current Regime", int(cur["Days_in_regime"]))

    if pd.notna(cur.get("Credit_Confidence")) and pd.notna(cur.get("Inflation_Confidence")):
        st.caption(
            f"اطمینانِ HMM برای برچسبِ امروز — اعتبار: **{cur['Credit_Confidence']:.0%}** · "
            f"تورم: **{cur['Inflation_Confidence']:.0%}** (احتمالِ فیلترشده‌ی همون حالتی که با argmax "
            "انتخاب شده؛ هرچی به ۱۰۰٪ نزدیک‌تر، مرزِ تشخیص کمتر مبهمه؛ نزدیکِ ۵۰٪ یعنی امروز دقیقاً لبه‌ی مرزه)."
        )

    if train_end is not None:
        st.caption(
            f"HMM fit window: start → {train_end.date()} (train, {int(TRAIN_FRAC*100)}٪). "
            "بعد از این تاریخ، احتمال فیلترشده‌ی رو-به-جلو (بدون دیدن آینده) اعمال شده — "
            "بخش out-of-sample (test) روی چارت با خط نقطه‌چین مشخص است."
        )

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

    # ---- SP500 (فقط close، لگاریتمی) روی محور سوم مستقل — بی‌صدا حذف می‌شه اگه ستون نباشه ----
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

    if train_end is not None and valid.index[0] <= train_end <= valid.index[-1]:
        fig.add_vline(x=train_end, line_dash="dot", line_color="#bbbbbb")
        fig.add_annotation(x=train_end, y=1.08, yref="paper", showarrow=False,
                            text="◄ train | test ►", font=dict(size=10, color="#bbbbbb"))

    fig.update_layout(
        yaxis=dict(title=f"Credit {method_label} ({signal_unit})"),
        yaxis2=dict(title=f"Inflation {method_label} ({signal_unit})", overlaying="y", side="right"),
        template="plotly_dark", height=380, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=1.1),
        **({"yaxis3": dict(overlaying="y", side="right", showticklabels=False, showgrid=False,
                            zeroline=False, type="log")} if has_sp500 else {}),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_chart")

    # ---- آمار رژیم (کل تاریخچه، بدون توجه به مرز train/test) ----
    with st.expander(f"📊 Regime Statistics — {method_label} (Selected Range)", expanded=False):
        if benchmark_ret is not None and not benchmark_ret.empty:
            bench_sub = benchmark_ret.reindex(valid.index)
            st.caption(
                f"مرجع مقایسه — میانگین بازدهی روزانه‌ی {BENCHMARK_COL} در کل بازه‌ی انتخابی "
                f"(بدون تفکیک رژیم): **{bench_sub.mean():.3f}٪** · نوسان روزانه: **{bench_sub.std():.3f}٪**."
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


# ==========================================================================
# 6) رابط کاربری اصلی
# ==========================================================================

def show() -> None:
    inject_global_style()
    st.markdown("# 📊 Credit & Inflation Regime Dashboard + HMM")
    st.caption("سیگنال سریع/تاکتیکی — الهام‌گرفته از داشبورد Credit & Inflation Regime (Capital Flows)")
    st.caption(
        "⚠️ محور «رشد» اینجا در واقع شرایط مالی/ریسک اعتباری (Credit Spread) را می‌سنجد، نه GDP واقعی. "
        "برای سیگنال کند/پایدار مبتنی بر رشد واقعی، تب Economic Regime (eco3min) را ببینید. "
        "تشخیص رژیم از این نسخه به بعد بر پایه‌ی HMM دوحالته (هر محور مستقل) است، نه آستانه‌ی ثابت."
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

    # ---- بازه‌ی تاریخ مشترک بین هر دو پنل (فقط برای نمایش؛ فیت HMM روی کل تاریخچه است) ----
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

    # ---- ماتریس طبقه‌بندی (مشترک، مستقل از روش — معنای رژیم‌ها عوض نشده) ----
    st.markdown("#### Regime Classification Matrix")
    mc1, mc2 = st.columns(2)
    mc1.markdown("**SPREADS FALLING (GROWTH+)**")
    mc1.markdown("🟡 **Reflation** — Spreads tightening + inflation up")
    mc1.markdown("🟢 **Goldilocks** — Spreads tightening + inflation down")
    mc2.markdown("**SPREADS RISING (GROWTH-)**")
    mc2.markdown("🔴 **Stagflation** — Spreads widening + inflation up")
    mc2.markdown("🔵 **Recession** — Spreads widening + inflation down")

    # ---- داده‌ی «بازدهی/نوسان هر رژیم» و «بازدهی هر زیربخش» — پورت‌شده از model1 ----
    benchmark_prices = load_benchmark(str(DB_PATH), os.path.getmtime(DB_PATH))
    benchmark_ret = benchmark_prices.pct_change().mul(100) if not benchmark_prices.empty else pd.Series(dtype=float)
    sector_df = load_sector_prices(str(DB_PATH), os.path.getmtime(DB_PATH))

    st.divider()
    render_panel(raw, credit_col, inflation_col, start_date, end_date,
                 method_label="Rate of Change", compute_fn=compute_roc_signal,
                 signal_unit="bps", key_prefix="roc",
                 benchmark_ret=benchmark_ret, benchmark_prices=benchmark_prices, sector_df=sector_df)

    st.divider()
    render_panel(raw, credit_col, inflation_col, start_date, end_date,
                 method_label="Z-Score", compute_fn=compute_zscore_signal,
                 signal_unit="σ", key_prefix="z",
                 benchmark_ret=benchmark_ret, benchmark_prices=benchmark_prices, sector_df=sector_df)

    st.caption(
        f"Source: {DB_PATH} (read-only) | Generated {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"
    )