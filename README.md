# Global Market & Iran Bourse Analysis

یک داشبورد تحلیلی (Streamlit) برای رصد و مدل‌سازی رژیم‌های اقتصادی/بازار — با تمرکز روی بازارهای جهانی (آمریکا) و بورس تهران — و مسیری به سمت پیش‌بینی چندین دارایی (بورس ایران، طلا، بورس آمریکا، بیت‌کوین، یورو-دلار) بر پایه‌ی مدل‌های رژیم اقتصادی.

این پروژه صرفاً یه dashboard ساده نیست؛ بخش زیادی از کارش **نقد و بازسازیِ روش‌شناسیِ مدل‌های آماری شناخته‌شده** (Markov-Switching Regime Models) بوده — شامل پیدا‌کردن و رفع باگ‌های ظریفِ *look-ahead bias*، replication یه پایان‌نامه‌ی دانشگاهی واقعی (Srivastava, 2018 — WorldQuant University) و مقایسه‌ی عددیِ نتایج با اون، و طراحیِ فیچرهای walk-forward بدون نگاه‌به‌آینده برای استفاده‌ی نهایی در یادگیری ماشین.

---

## بخش‌های اصلی

### 🇮🇷 بورس ایران
داده‌ی نماد/شاخص از طریق `finpy_tse`؛ نمای کلی سهم‌ها و heatmap صنایع. (شاخص‌ها، مشتقه و صندوق‌ها هنوز در دست توسعه‌ست.)

### 🌍 بازار جهانی
- **Dashboard** — وضعیت کلی دیتابیس و به‌روزرسانی
- **Charts** — نمودار زنده (TradingView)
- **Correlation** — ماتریس همبستگی بین دارایی‌ها
- **Summary** — نمای سریع بازار: نسبت نوسان ضمنی/واقعی، رشد/کاهش شاخص‌های بخشی (S&P Sector ETFs)، شاخص SKEW، ساختار تایم‌اسپرد VIX
- **Hyper Liquid** — دیتای فاندینگ

### 📐 مدل‌های رژیم اقتصادی (Macro → Economic Regime)
شش مدل مستقل، هرکدوم یه رویکرد متفاوت برای تشخیص رژیم بازار:

| مدل | رویکرد | ویژگی |
|---|---|---|
| **Model 1** | Credit Spread × Inflation (Rate-of-Change / Z-Score) | دو پنل کاملاً مستقل، فیلتر ضدنویز، اعتبارسنجی خودکار با بازدهی ۱۲ شاخص بخشی روی اپیزود فعلی/قبلی رژیم |
| **Model 2** | Hidden Markov Model (GaussianHMM) | تشخیص خودکار رژیم بدون آستانه‌ی دستی |
| **Model 3** | eco3min (CFNAI × Trimmed Mean PCE) | چارچوب رشد/تورم با Sahm Rule و hysteresis، nowcast با walk-forward validation |
| **Model 4** | eco3min + نقدینگی + لایه‌ی احتمال | شوک‌اورلی (نفت/دلار/اسپرد) |
| **Model 5** | Model 4 + پیش‌بینی با Logistic Regression | — |
| **Model 6** | Markov-Switching Variance (statsmodels) — replication مقاله‌ی SSRN 3144169 | تفکیک S&P500 به ۴ رژیم Wyckoff (Advance/Accumulation/Decline/Distribution)؛ فیچرهای walk-forward (امروز/دیروز/دو‌روز‌پیش) بدون نگاه‌به‌آینده، آماده برای یادگیری ماشین |

---

## چند نکته‌ی روش‌شناسی که این پروژه رو از یه dashboard معمولی متفاوت می‌کنه

- **کشف Look-Ahead Bias واقعی:** توی یکی از مدل‌ها (Model 4)، سیگنال تورم به‌صورت میانگین «این ماه + ماه بعد» ساخته شده بود — یعنی برای هر نقطه‌ی تاریخی، مدل داشت از داده‌ی *واقعیِ آینده* استفاده می‌کرد. این مشکل شناسایی و مستند شد.
- **Smoothed vs Filtered Probability:** برای Model 6، تفاوت بین احتمال «با دید کامل تاریخچه» (مناسب مطالعه‌ی تاریخی) و احتمال «فقط با داده‌ی تا همین لحظه» (مناسب فیچر زنده‌ی ML) به‌صورت صریح جدا شده، و فیچرهای walk-forward با فیت مجدد مدل (نه فقط برش دادن خروجی یک فیت مشترک) ساخته شدن.
- **Replication یه مقاله‌ی آکادمیک واقعی:** روش‌شناسی Model 6 (Markov-Switching Variance + Triangular MA + Keltner Channel ATR) از یه پایان‌نامه‌ی MSc واقعی (SSRN 3144169) بازسازی شده و نتایج عددی (نسبت واریانس رژیم‌ها، توزیع رژیم‌ها) با جدول‌های اصلی مقاله مقایسه شده — همراه با فهرست صادقانه‌ای از این‌که چرا اعداد دقیقاً یکی نیستن (تفاوت بازه‌ی زمانی، نوع بازدهی، optimum محلی — همه تست و رد شدن؛ تفاوت باقی‌مونده احتمالاً از نسخه‌ی داده‌ست، نه از خطای روش).
- **اعتبارسنجی Cross-Asset:** به‌جای اینکه فقط به خروجیِ خامِ یه مدل رژیم اعتماد کنیم، بازدهیِ ۱۲ شاخص بخشیِ S&P (XLK, XLF, XLV, ...) رو روی طول واقعیِ اپیزودِ فعلی و قبلیِ هر رژیم اندازه می‌گیریم — تا ببینیم رفتار واقعی بازار با ادعای رژیم همخونی داره یا نه.

---

## Tech Stack

- **Frontend:** Streamlit (چندصفحه‌ای)، Plotly برای نمودارها
- **مدل‌سازی:** `statsmodels` (Markov-Switching Regression)، `hmmlearn` (Gaussian HMM)، `scikit-learn`
- **داده:** FRED API، Yahoo Finance (`yfinance`)، TradingView (`tvDatafeed`)، MacroMicro، `finpy_tse` (بورس ایران)

---

## ساختار پروژه

```
├── app.py                     # صفحه‌ی اصلی
├── theme.py                   # استایل/فونت مشترک کل پروژه
├── constants.py                # ROOT_DIR
├── requirements.txt
├── database/                  # دیتابیس (در گیت نیست — پایین‌تر توضیح داده شده)
├── iran_market/                # صفحات بورس ایران
├── world_market/
│   ├── Dashboard.py, charts.py, correlation.py, macro.py
│   └── macroF/
│       ├── summary.py, bond.py, economic_regime.py
│       └── regime_model1.py ... regime_model6.py
└── Media/                      # تصاویر صفحه‌ی اصلی
```

---

## راه‌اندازی

```bash
git clone <this-repo>
cd project
pip install -r requirements.txt
```

یه فایل `.streamlit/secrets.toml` بساز (نمونه‌ش `.streamlit/secrets.toml.example`):

```toml
TRADINGVIEW_USERNAME = "..."
TRADINGVIEW_PASSWORD = "..."
```

```bash
streamlit run app.py
```

### ⚠️ نکته‌ی مهم درباره‌ی داده
اسکریپت به‌روزرسانیِ دیتابیس (`updater.py`) عمداً در این ریپو نیست** (توی `.gitignore`). این ریپو کد تحلیل/مدل‌سازی رو نشون می‌ده؛ برای اجرای به روز، به دیتابیس/pipeline خودتون نیاز دارید (یا با من تماس بگیرید).
---

## Disclaimer

این پروژه صرفاً برای اهداف آموزشی/تحلیلی ساخته شده و **توصیه‌ی مالی نیست**. هیچ‌کدوم از مدل‌های رژیم اینجا تضمینی برای پیش‌بینی آینده‌ی بازار نمی‌دن.
