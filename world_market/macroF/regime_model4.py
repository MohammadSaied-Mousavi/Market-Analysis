"""
regime_model2.py — نسخهٔ کامل: Growth × Inflation × Liquidity + Probability Layer
                    + Shock Overlay، با محور تورمِ دوجزئیِ زمانی (این ماه + ماه بعد)
==========================================================================
جایگزین world_market/macroF/regime_model2.py

==========================================================================
*** نسخهٔ اصلاح‌شده — رفع باگ «Probability Layer / رژیم جهت = nan» ***
==========================================================================

علت دقیق باگ قبلی:
    Component_B(t) = PCETRIM(t+1)  (یعنی عدد واقعیِ ماه بعد، با shift(-1))

    این یعنی INFLATION_MEASURE هر ماه به دادهٔ ماهِ *بعدی*‌اش هم وابسته
    بود. حالا اگر در هر نقطه از کل تاریخچهٔ دیتابیس شما — حتی صدها ماه
    قبل، کاملاً نامرتبط به «الان» — یک ماه از قلم افتاده باشد (خیلی
    رایج در دیتابیس‌های واقعی)، آن یک شکاف باعث NaN شدن Component_B برای
    ماهِ *قبل* از آن شکاف می‌شود. سپس چون G_chg3m/I_chg3m با diff(3) کار
    می‌کنند (نیاز به مقدار «الان» و «۳ ماه قبل» دارند)، این یک NaN به
    چند ماه اطرافش هم سرایت می‌کند. و چون لایهٔ احتمال و رژیم جهت
    (Prometheus) هر دو مستقیماً از I_chg3m ساخته می‌شوند، اگر ماهِ مرجعِ
    گزارش (که فقط بر اساس CFNAI_MA3 و INFLATION_MEASURE انتخاب می‌شد)
    درست همان ماهی باشد که I_chg3m‌اش NaN است، کل لایهٔ احتمال و رژیم
    جهت آن ماه هم NaN می‌شوند — دقیقاً همان چیزی که در پروژهٔ شما دیده
    می‌شد. با یک تست عمدی (یک شکاف مصنوعی، ۱۰۰ ماه قبل از امروز) این را
    بازتولید و تأیید کردم.

    این یک محدودیت داده نیست؛ یک ضعف طراحی در Component_B بود.

راه‌حل اعمال‌شده:
    اگر Component_B نه از عدد واقعیِ ماه بعد و نه از نوکست کلیولند قابل
    محاسبه باشد (چه به‌خاطر شکاف تاریخی، چه چون کلیولند برای آن ماه
    چیزی نداشت)، به‌جای رها کردن NaN، از خودِ Component_A همان ماه
    استفاده می‌شود («اگر نشانه‌ای از تغییر نداریم، فرض می‌کنیم ماه بعد
    شبیه همین ماه است» — یک fallback شفاف و محافظه‌کارانه، نه حدس کور).
    این ضمانت می‌کند INFLATION_MEASURE هرجا Component_A موجود است، تعریف
    شده باشد؛ زنجیرهٔ diff(3) / رولینگ ۶۰ماهه / لایهٔ احتمال / رژیم جهت
    دیگر با یک شکاف دوردست در تاریخچه نمی‌شکند. ستون
    Component_B_Is_Fallback این موارد را علامت‌گذاری می‌کند تا شفاف
    بماند کِی این اتفاق افتاده.

    علاوه بر این، get_reference_row هم now به‌جای فقط چک‌کردن
    CFNAI_MA3/INFLATION_MEASURE، وجود Regime_direction و top_regime را
    هم شرط می‌کند — یعنی اگر به هر دلیل دیگری (مثلاً NET_LIQUIDITY یک
    مشکل جدا داشته باشد) هنوز جایی خالی بماند، گزارش خودش یک ماه عقب‌تر
    می‌رود تا یک ماهِ کاملاً پر پیدا کند، نه اینکه نصفه نمایش بدهد.

==========================================================================
دو اضافهٔ دیگر طبق درخواست شما
==========================================================================

۱) راهنمای خواندن لایهٔ احتمال (توضیح آنتروپی/margin/confidence) — که در
   فایل مستقل قبلی (us_regime_classifier_با_توضیحات.py) بود، حالا در
   خودِ صفحهٔ Streamlit هم به‌عنوان یک expander توضیحی آمده.

۲) راهنمای دارایی حالا هر ۸ ترکیب (G, I, L) را پوشش می‌دهد (نه فقط ۴
   ترکیب G×I که نقدینگی را نادیده می‌گرفت). این ۸ توصیف، برداشتِ کیفیِ
   من از الگوی جدول عملکرد دارایی‌ها به‌ازای رژیم است که فرستادید —
   عمداً کیفی و پارافریزشده نوشته شده (نه بازتولید دقیق اعداد جدول)،
   چون آن جدول از یک گزارش تحقیقاتی به نظر می‌رسد و بازتولید عینیِ کل
   ماتریس عددی‌اش درست نیست. اگر بخواهید اعداد دقیق خودتان را جایگزین
   کنید، دیکشنری DIRECTION_ASSET_HINTS_8 پایین را ویرایش کنید.


regime_model2.py — نسخهٔ کامل: Growth × Inflation × Liquidity + Probability Layer
                    + Shock Overlay، با محور تورمِ دوجزئیِ زمانی (این ماه + ماه بعد)
==========================================================================
جایگزین world_market/macroF/regime_model2.py

==========================================================================
*** نسخهٔ اصلاح‌شده — رفع باگ «Probability Layer / رژیم جهت = nan» ***
==========================================================================

علت دقیق باگ قبلی:
    Component_B(t) = PCETRIM(t+1)  (یعنی عدد واقعیِ ماه بعد، با shift(-1))

    این یعنی INFLATION_MEASURE هر ماه به دادهٔ ماهِ *بعدی*‌اش هم وابسته
    بود. حالا اگر در هر نقطه از کل تاریخچهٔ دیتابیس شما — حتی صدها ماه
    قبل، کاملاً نامرتبط به «الان» — یک ماه از قلم افتاده باشد (خیلی
    رایج در دیتابیس‌های واقعی)، آن یک شکاف باعث NaN شدن Component_B برای
    ماهِ *قبل* از آن شکاف می‌شود. سپس چون G_chg3m/I_chg3m با diff(3) کار
    می‌کنند (نیاز به مقدار «الان» و «۳ ماه قبل» دارند)، این یک NaN به
    چند ماه اطرافش هم سرایت می‌کند. و چون لایهٔ احتمال و رژیم جهت
    (Prometheus) هر دو مستقیماً از I_chg3m ساخته می‌شوند، اگر ماهِ مرجعِ
    گزارش (که فقط بر اساس CFNAI_MA3 و INFLATION_MEASURE انتخاب می‌شد)
    درست همان ماهی باشد که I_chg3m‌اش NaN است، کل لایهٔ احتمال و رژیم
    جهت آن ماه هم NaN می‌شوند — دقیقاً همان چیزی که در پروژهٔ شما دیده
    می‌شد. با یک تست عمدی (یک شکاف مصنوعی، ۱۰۰ ماه قبل از امروز) این را
    بازتولید و تأیید کردم.

    این یک محدودیت داده نیست؛ یک ضعف طراحی در Component_B بود.

راه‌حل اعمال‌شده:
    اگر Component_B نه از عدد واقعیِ ماه بعد و نه از نوکست کلیولند قابل
    محاسبه باشد (چه به‌خاطر شکاف تاریخی، چه چون کلیولند برای آن ماه
    چیزی نداشت)، به‌جای رها کردن NaN، از خودِ Component_A همان ماه
    استفاده می‌شود («اگر نشانه‌ای از تغییر نداریم، فرض می‌کنیم ماه بعد
    شبیه همین ماه است» — یک fallback شفاف و محافظه‌کارانه، نه حدس کور).
    این ضمانت می‌کند INFLATION_MEASURE هرجا Component_A موجود است، تعریف
    شده باشد؛ زنجیرهٔ diff(3) / رولینگ ۶۰ماهه / لایهٔ احتمال / رژیم جهت
    دیگر با یک شکاف دوردست در تاریخچه نمی‌شکند. ستون
    Component_B_Is_Fallback این موارد را علامت‌گذاری می‌کند تا شفاف
    بماند کِی این اتفاق افتاده.

    علاوه بر این، get_reference_row هم now به‌جای فقط چک‌کردن
    CFNAI_MA3/INFLATION_MEASURE، وجود Regime_direction و top_regime را
    هم شرط می‌کند — یعنی اگر به هر دلیل دیگری (مثلاً NET_LIQUIDITY یک
    مشکل جدا داشته باشد) هنوز جایی خالی بماند، گزارش خودش یک ماه عقب‌تر
    می‌رود تا یک ماهِ کاملاً پر پیدا کند، نه اینکه نصفه نمایش بدهد.

==========================================================================
دو اضافهٔ دیگر طبق درخواست شما
==========================================================================

۱) راهنمای خواندن لایهٔ احتمال (توضیح آنتروپی/margin/confidence) — که در
   فایل مستقل قبلی (us_regime_classifier_با_توضیحات.py) بود، حالا در
   خودِ صفحهٔ Streamlit هم به‌عنوان یک expander توضیحی آمده.

۲) راهنمای دارایی حالا هر ۸ ترکیب (G, I, L) را پوشش می‌دهد (نه فقط ۴
   ترکیب G×I که نقدینگی را نادیده می‌گرفت). این ۸ توصیف، برداشتِ کیفیِ
   من از الگوی جدول عملکرد دارایی‌ها به‌ازای رژیم است که فرستادید —
   عمداً کیفی و پارافریزشده نوشته شده (نه بازتولید دقیق اعداد جدول)،
   چون آن جدول از یک گزارش تحقیقاتی به نظر می‌رسد و بازتولید عینیِ کل
   ماتریس عددی‌اش درست نیست. اگر بخواهید اعداد دقیق خودتان را جایگزین
   کنید، دیکشنری DIRECTION_ASSET_HINTS_8 پایین را ویرایش کنید.

==========================================================================
==========================================================================
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
    "G_PLUS": 0.10, "G_MINUS": -0.50,
    "I_PLUS": 2.75, "I_MINUS": 1.50,
    "SAHM_TRIGGER": 0.50,
    "HYSTERESIS_MONTHS": 2,
    "ZSCORE_WINDOW_MONTHS": 60,
    "SIGMOID_SCALE": 1.0,
    "BRENT_SHOCK_YOY": 20.0,
    "DIVERGENCE_GAP_PP": 1.0,
    "DXY_SHOCK_3M": 5.0,
    "CREDIT_SPREAD_Z_SHOCK": 2.0,
}

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

QUADRANT_LABELS = {
    "p_gup_idown": "Growth Up / Inflation Down  (Disinflationary Expansion)",
    "p_gup_iup": "Growth Up / Inflation Up    (Overheating)",
    "p_gdown_idown": "Growth Down / Inflation Down (Disinflationary Contraction)",
    "p_gdown_iup": "Growth Down / Inflation Up   (Stagflation)",
}

# رنگ هر خانهٔ لایهٔ احتمال — عمداً همان رنگ رژیم هم‌معنایش در گرید سطح
# (Overheating زرد، Stagflation قرمز، ...) تا چشم بین دو نمودار راحت وصل شود.
QUADRANT_COLORS = {
    "p_gup_idown": "#2e7d32",    # هم‌رنگ Disinflationary Expansion
    "p_gup_iup": "#f9a825",      # هم‌رنگ Overheating
    "p_gdown_idown": "#1565c0",  # هم‌رنگ Disinflationary Contraction
    "p_gdown_iup": "#c62828",    # هم‌رنگ Stagflation
}

# رنگ هر خانهٔ لایهٔ احتمال — عمداً هم‌رنگ با گرید سطح (بالا) چون مفهوماً
# نزدیکند: Growth Up/Inflation Down ~ Disinflationary Expansion، و غیره.
QUADRANT_COLORS = {
    "p_gup_idown": "#2e7d32",
    "p_gup_iup": "#f9a825",
    "p_gdown_idown": "#1565c0",
    "p_gdown_iup": "#c62828",
}

# رنگ هر خانهٔ لایهٔ احتمال — عمداً همان رنگ رژیمِ هم‌معنایش در گرید سطح
# (Regime_level) را استفاده می‌کند تا وقتی هر دو نمودار را کنار هم می‌بینید،
# قابل‌مقایسه باشند (مثلاً «Growth Up / Inflation Down» همیشه سبز است، چه در
# گرید سطح چه در لایهٔ احتمال).
QUADRANT_COLORS = {
    "p_gup_idown": "#2e7d32",    # هم‌رنگ با Disinflationary Expansion
    "p_gup_iup": "#f9a825",      # هم‌رنگ با Overheating
    "p_gdown_idown": "#1565c0",  # هم‌رنگ با Disinflationary Contraction
    "p_gdown_iup": "#c62828",    # هم‌رنگ با Stagflation
}

# رنگ هر ربع از لایهٔ احتمال — عمداً هم‌رنگ با معادل‌شان در REGIME_COLORS
# (بالا) تا چشم بین دو نمودار (رژیم سطح و رژیم غالبِ احتمال) به‌راحتی ارتباط برقرار کند
QUADRANT_COLORS = {
    "p_gup_idown": "#2e7d32",    # همرنگ Disinflationary Expansion
    "p_gup_iup": "#f9a825",      # همرنگ Overheating
    "p_gdown_idown": "#1565c0",  # همرنگ Disinflationary Contraction
    "p_gdown_iup": "#c62828",    # همرنگ Stagflation
}

# رنگ هر خانهٔ لایهٔ احتمال — عمداً هم‌رنگ با معادل مفهومی‌اش در گرید سطح
# (Disinflationary Expansion/Overheating/Disinflationary Contraction/Stagflation)
# تا چشم به‌راحتی بین دو نمودار (سطح و احتمال) ارتباط برقرار کند.
QUADRANT_COLORS = {
    "p_gup_idown": "#2e7d32",
    "p_gup_iup": "#f9a825",
    "p_gdown_idown": "#1565c0",
    "p_gdown_iup": "#c62828",
}

# رنگ هر خانهٔ لایهٔ احتمال — عمداً هم‌رنگ با رژیم سطحِ معادلش در گرید
# سطح (بالا)، تا چشم راحت‌تر این دو نمودار را کنار هم بخواند.
QUADRANT_COLORS = {
    "p_gup_idown": "#2e7d32",    # هم‌رنگ Disinflationary Expansion
    "p_gup_iup": "#f9a825",      # هم‌رنگ Overheating
    "p_gdown_idown": "#1565c0",  # هم‌رنگ Disinflationary Contraction
    "p_gdown_iup": "#c62828",    # هم‌رنگ Stagflation
}

# رنگ هر خانهٔ لایهٔ احتمال — عمداً همان رنگ‌های گرید سطح استفاده شده تا
# چشم به‌راحتی بین دو نمودار (رژیم سطح / رژیم غالب احتمال) وصل شود
QUADRANT_COLORS = {
    "p_gup_idown": "#2e7d32",    # هم‌رنگ Disinflationary Expansion
    "p_gup_iup": "#f9a825",      # هم‌رنگ Overheating
    "p_gdown_idown": "#1565c0",  # هم‌رنگ Disinflationary Contraction
    "p_gdown_iup": "#c62828",    # هم‌رنگ Stagflation
}

# رنگ هر خانهٔ لایهٔ احتمال — عمداً هم‌رنگ با رژیم‌های هم‌معنی در گرید سطح
# (Growth Up/Inflation Down ~ Disinflationary Expansion و ...) تا چشم راحت‌تر
# بین دو نمودار (سطح در برابر جهت) ارتباط برقرار کند.
QUADRANT_COLORS = {
    "p_gup_idown": "#2e7d32",     # سبز — شبیه Disinflationary Expansion
    "p_gup_iup": "#f9a825",       # زرد — شبیه Overheating
    "p_gdown_idown": "#1565c0",   # آبی — شبیه Disinflationary Contraction
    "p_gdown_iup": "#c62828",     # قرمز — شبیه Stagflation
}

# رنگ هر خانهٔ لایهٔ احتمال — عمداً هم‌رنگ با معادل نزدیکش در گرید سطح
# (تا چشم بین دو نمودار راحت مقایسه کند): Growth Up/Inflation Down ~ سبز
# (شبیه Disinflationary Expansion)، Growth Up/Inflation Up ~ زرد (شبیه
# Overheating)، Growth Down/Inflation Down ~ آبی (شبیه Disinflationary
# Contraction)، Growth Down/Inflation Up ~ قرمز (شبیه Stagflation).
QUADRANT_COLORS = {
    "p_gup_idown": "#2e7d32",
    "p_gup_iup": "#f9a825",
    "p_gdown_idown": "#1565c0",
    "p_gdown_iup": "#c62828",
}

# رنگ هر خانهٔ لایهٔ احتمال — عمداً همان رنگ خانوادهٔ معنایی‌اش در گرید سطح
# (مثلاً "Growth Up/Inflation Down" همان رنگ "Disinflationary Expansion")
# تا وقتی دو نمودار (رژیم سطح و رژیم غالب) را کنار هم می‌بینید، بلافاصله
# بفهمید کدام رنگ به کدام مفهوم اشاره دارد.
QUADRANT_COLORS = {
    "p_gup_idown": "#2e7d32",
    "p_gup_iup": "#f9a825",
    "p_gdown_idown": "#1565c0",
    "p_gdown_iup": "#c62828",
}


# کلید: (G_dir, I_dir, L_dir) → توضیح قابل‌فهم و مختصر
DIRECTION_ASSET_HINTS_8 = {
    ("+", "-", "+"): (
        "رشد شتاب می‌گیرد، تورم فروکش می‌کند، نقدینگی هم رو به افزایش — "
        "کلاسیک‌ترین محیط صعودی برای سهام؛ سهام رشدی/مصرفی و املاک معمولاً "
        "جلوترند، کامودیتی و طلا معمولاً عقب می‌مانند."
    ),
    ("+", "-", "-"): (
        "رشد بالا و تورم پایین، اما نقدینگی رو به انقباض — سهام هنوز کار "
        "می‌کند ولی محتاطانه‌تر (بخش مالی و بلوچیپ‌ها معمولاً بهتر از "
        "رشدی‌های پرریسک)؛ کامودیتی و طلا اغلب بدترین عملکرد را دارند."
    ),
    ("+", "+", "+"): (
        "رشد و تورم هر دو بالا، نقدینگی هم فراوان — به‌طور کلی سالم‌ترین "
        "رژیم؛ کامودیتی‌ها (به‌خصوص کشاورزی) و سهام معمولاً هم‌زمان قوی "
        "عمل می‌کنند."
    ),
    ("+", "+", "-"): (
        "رشد و تورم هر دو بالا اما نقدینگی سخت‌تر — طلا و بخش فناوری "
        "معمولاً غیرمنتظره قوی‌اند؛ سهام به‌طور کلی ضعیف‌تر از حالت مشابه "
        "با نقدینگی آسان."
    ),
    ("-", "-", "+"): (
        "رشد و تورم هر دو رو به کاهش، نقدینگی هنوز آسان (تصویر کلاسیک شل‌"
        "کردن پولی در رکود) — اوراق قرضه و دارایی‌های دفاعی بهترین پناهگاه؛ "
        "کامودیتی، فناوری و بخش مالی معمولاً بیشترین آسیب را می‌بینند."
    ),
    ("-", "-", "-"): (
        "رشد ضعیف، تورم رو به کاهش، نقدینگی هم سخت — اوراق و بخش‌های دفاعی/"
        "مالی نسبتاً بهتر از میانگین‌اند؛ کامودیتی و انرژی معمولاً بدترین."
    ),
    ("-", "+", "+"): (
        "رشد ضعیف ولی تورم رو به افزایش، نقدینگی آسان — نزدیک به stagflation "
        "کلاسیک با یک سوپاپ‌اطمینان نقدینگی؛ طلا و کامودیتی نسبتاً بهتر، "
        "سهام (خصوصاً رشدی و مالی) ضعیف."
    ),
    ("-", "+", "-"): (
        "بدترین ترکیب ممکن: رشد ضعیف، تورم بالا، نقدینگی هم سخت — تقریباً "
        "همه‌چیز ضعیف است؛ املاک، فناوری و سهام رشدی معمولاً بیشترین افت را دارند."
    ),
}


# ==========================================================================
# 1) خواندن داده — فقط خواندنی، سازگار با دیتابیس raw (بدون forward-fill)
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


# ==========================================================================
# 1.b) اسکرپ نوکست تورم فدرال کلیولند (فقط برای Component B، لبهٔ زمان حال)
# ==========================================================================

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


# ==========================================================================
# 2) ابزارهای مشترک رگرسیون بریج (OLS با پنجرهٔ غلتان)
# ==========================================================================

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


# ==========================================================================
# 3) ساخت محور تورمِ دوجزئی: Component A (این ماه) + Component B (ماه بعد)
# ==========================================================================

def build_inflation_measure(monthly: pd.DataFrame, cleveland: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]:
    df = _add_yoy_predictors(monthly)
    diagnostics = {}

    # --- Component A: تورم خودِ همین ماه ---
    a_predictors = ["CORE_CPI_YOY"] + (["CORE_PPI_YOY"] if "CORE_PPI_YOY" in df.columns else [])
    if "CORE_PPI_EXTRADE_YOY" in df.columns:
        a_predictors.append("CORE_PPI_EXTRADE_YOY")

    if len(a_predictors) >= 2:
        comp_a, comp_a_is_now, diag_a = _fill_gap_with_bridge(
            df, "PCETRIM12M159SFRBDAL", a_predictors
        )
        diagnostics["component_a_enabled"] = True
    else:
        comp_a, comp_a_is_now = df["PCETRIM12M159SFRBDAL"].copy(), pd.Series(False, index=df.index)
        diag_a = {"fit_r2": np.nan, "fit_mae": np.nan, "n_train": 0}
        diagnostics["component_a_enabled"] = False
    diagnostics["component_a_diag"] = diag_a
    diagnostics["component_a_predictors"] = a_predictors

    df["Component_A"] = comp_a
    df["Component_A_Is_Nowcast"] = comp_a_is_now

    # --- Component B: تورمِ ماهِ بعد (t+1) ---
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

    # *** رفع باگ اصلی ***
    # اگر بعد از تلاش با عدد واقعی و بعد از تلاش با کلیولند هم هنوز
    # Component_B خالی مانده (چه به‌خاطر شکاف در دادهٔ تاریخی، چه چون
    # کلیولند برای آن ماه چیزی نداشت)، به‌جای رها کردن NaN — که زنجیرهٔ
    # diff(3)/رولینگ ۶۰ماهه/لایهٔ احتمال/رژیم جهت را در کل پروژه می‌شکند —
    # از خودِ Component_A همان ماه استفاده می‌کنیم: «اگر نشانه‌ای از تغییر
    # نداریم، فرض می‌کنیم ماه بعد شبیه همین ماه است». این fallback شفاف
    # و محافظه‌کارانه است (نه حدس کور) و با ستون زیر علامت‌گذاری می‌شود.
    df["Component_B_Is_Fallback"] = False
    still_missing = df["Component_B"].isna() & df["Component_A"].notna()
    df.loc[still_missing, "Component_B"] = df.loc[still_missing, "Component_A"]
    df.loc[still_missing, "Component_B_Is_Fallback"] = True

    df["INFLATION_MEASURE"] = 0.5 * df["Component_A"] + 0.5 * df["Component_B"]
    df["Inflation_Is_Nowcast"] = (
        df["Component_A_Is_Nowcast"] | df["Component_B_Is_Nowcast"] | df["Component_B_Is_Fallback"]
    )

    return df, diagnostics


# ==========================================================================
# 4) محاسبهٔ محورهای G / I / L + شرایط مالی + شوک overlay + پرچم واگرایی
# ==========================================================================

def compute_axes(monthly: pd.DataFrame, cleveland: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]:
    out, inflation_diag = build_inflation_measure(monthly, cleveland)

    out["CFNAI_MA3"] = out["CFNAI"].rolling(3, min_periods=1).mean()
    out["NET_LIQUIDITY"] = (out["WALCL"] - out["WTREGEN"] - out["RRPONTSYD"]) / 1000.0

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

    sahm_trigger = out["SAHMREALTIME"] >= THRESH["SAHM_TRIGGER"]
    out.loc[sahm_trigger, "G_level_raw"] = "G-"

    out["G_level"] = apply_hysteresis(out["G_level_raw"], sahm_trigger, THRESH["HYSTERESIS_MONTHS"])
    out["I_level"] = apply_hysteresis(out["I_level_raw"], pd.Series(False, index=out.index), THRESH["HYSTERESIS_MONTHS"])

    out["Regime_level"] = [
        REGIME_GRID_NAMES.get((g, i), np.nan) for g, i in zip(out["G_level"], out["I_level"])
    ]

    out["G_chg3m"] = out["CFNAI_MA3"].diff(3)
    out["I_chg3m"] = out["INFLATION_MEASURE"].diff(3)
    out["L_chg3m"] = out["NET_LIQUIDITY"].pct_change(3) * 100

    out["G_dir"] = np.where(out["G_chg3m"] >= 0, "+", "-")
    out["I_dir"] = np.where(out["I_chg3m"] >= 0, "+", "-")
    out["L_dir"] = np.where(out["L_chg3m"] >= 0, "+", "-")
    out.loc[out["G_chg3m"].isna(), "G_dir"] = np.nan
    out.loc[out["I_chg3m"].isna(), "I_dir"] = np.nan
    out.loc[out["L_chg3m"].isna(), "L_dir"] = np.nan

    out["Regime_direction"] = [
        f"({g})G({i})I({l})L" if pd.notna(g) and pd.notna(i) and pd.notna(l) else np.nan
        for g, i, l in zip(out["G_dir"], out["I_dir"], out["L_dir"])
    ]

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
    out["Days_in_financial_state"] = _days_in_state(out["Financial_state"])
    out["Days_in_regime_level"] = _days_in_state(out["Regime_level"])

    # --- لایهٔ احتمال ---
    win, scale = THRESH["ZSCORE_WINDOW_MONTHS"], THRESH["SIGMOID_SCALE"]

    def rolling_z(series):
        mu = series.rolling(win, min_periods=24).mean()
        sd = series.rolling(win, min_periods=24).std()
        return (series - mu) / sd.replace(0, np.nan)

    def sigmoid(z):
        return 1.0 / (1.0 + np.exp(-scale * z))

    out["p_growth_up"] = sigmoid(rolling_z(out["G_chg3m"]))
    out["p_growth_down"] = 1.0 - out["p_growth_up"]
    out["p_inflation_up"] = sigmoid(rolling_z(out["I_chg3m"]))
    out["p_inflation_down"] = 1.0 - out["p_inflation_up"]
    out["p_liquidity_easing"] = sigmoid(rolling_z(out["L_chg3m"]))
    out["p_liquidity_tightening"] = 1.0 - out["p_liquidity_easing"]

    out["p_gup_idown"] = out["p_growth_up"] * out["p_inflation_down"]
    out["p_gup_iup"] = out["p_growth_up"] * out["p_inflation_up"]
    out["p_gdown_idown"] = out["p_growth_down"] * out["p_inflation_down"]
    out["p_gdown_iup"] = out["p_growth_down"] * out["p_inflation_up"]

    quad_cols = ["p_gup_idown", "p_gup_iup", "p_gdown_idown", "p_gdown_iup"]
    quad_df = out[quad_cols]

    def safe_idxmax(row):
        return np.nan if row.notna().sum() == 0 else row.idxmax()

    def safe_second_label(row):
        return np.nan if row.notna().sum() < 2 else row.nlargest(2).index[-1]

    out["top_regime_key"] = quad_df.apply(safe_idxmax, axis=1)
    out["top_regime"] = out["top_regime_key"].map(QUADRANT_LABELS)
    out["top_regime_prob"] = quad_df.max(axis=1, skipna=True)
    out["second_regime"] = quad_df.apply(safe_second_label, axis=1).map(QUADRANT_LABELS)
    out["second_regime_prob"] = quad_df.apply(
        lambda r: r.nlargest(2).iloc[-1] if r.notna().sum() >= 2 else np.nan, axis=1
    )
    out["regime_margin"] = out["top_regime_prob"] - out["second_regime_prob"]
    out["confidence"] = out["top_regime_prob"]

    def entropy_row(row):
        vals = row[quad_cols].values.astype(float)
        if np.any(np.isnan(vals)):
            return np.nan
        vals = np.clip(vals, 1e-12, 1.0)
        return float(-np.sum(vals * np.log2(vals)))

    out["probability_entropy"] = out.apply(entropy_row, axis=1)

    # --- پرچم واگرایی Headline vs Underlying ---
    # شفافیت: علاوه بر خودِ درصد، سطح قیمت الان و سطح قیمت ۱۲ ماه پیش را هم
    # جداگانه نگه می‌داریم تا در صفحه نشان داده شوند — اگر عدد YoY غیرمنتظره
    # بود (مثلاً خیلی بزرگ‌تر از واقعیت بازار)، با دیدن این دو عدد و
    # تاریخ‌شان بلافاصله می‌شود فهمید مشکل از کجاست (رفرنس ماه اشتباه،
    # یا یک مقدار خراب در دیتابیس دقیقاً همان ۱۲ ماه قبل).
    out["BRENT_LEVEL_NOW"] = out["DCOILBRENTEU"]
    out["BRENT_LEVEL_12M_AGO"] = out["DCOILBRENTEU"].shift(12)
    out["BRENT_YOY"] = out["DCOILBRENTEU"].pct_change(12) * 100
    out["Headline_Underlying_Gap_pp"] = out["HEADLINE_CPI_YOY"] - out["INFLATION_MEASURE"]
    out["Headline_Underlying_Divergence_Flag"] = (
        (out["BRENT_YOY"].abs() > THRESH["BRENT_SHOCK_YOY"]) &
        (out["Headline_Underlying_Gap_pp"].abs() > THRESH["DIVERGENCE_GAP_PP"])
    )

    # --- Overlay شوک بیرونی ---
    out["DXY_PROXY_3M_CHG"] = out["DTWEXBGS"].pct_change(3) * 100
    out["CREDIT_SPREAD_BAA10Y"] = out["BAA10Y"]
    out["credit_spread_z"] = rolling_z(out["CREDIT_SPREAD_BAA10Y"])
    out["Shock_Alert"] = (
        (out["BRENT_YOY"].abs() > 30) |
        (out["DXY_PROXY_3M_CHG"].abs() > THRESH["DXY_SHOCK_3M"]) |
        (out["credit_spread_z"].abs() > THRESH["CREDIT_SPREAD_Z_SHOCK"])
    )

    return out, inflation_diag


def apply_hysteresis(raw_series: pd.Series, hard_gate: pd.Series, n_months: int) -> pd.Series:
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
    """
    آخرین ردیفی که هم محورهای اصلی (رشد، تورم) و هم محورهای وابسته به
    آن‌ها (رژیم جهت، لایهٔ احتمال) واقعاً مقدار دارند. این از نمایش یک
    ماهِ «نیمه‌کامل» (که مثلاً تورم دارد ولی لایهٔ احتمالش NaN است)
    جلوگیری می‌کند — دقیقاً همان مشکلی که در پروژهٔ شما دیده می‌شد.
    اگر چنین ماهی پیدا نشود، به‌ترتیب اولویت عقب‌تر می‌رود.

    ⚠️ این تابع فقط برای بخش‌های «رشد/تورم/جهت/احتمال» استفاده شود — این
    محورها واقعاً با تأخیر انتشار ماهانه مواجه‌اند (CFNAI، PCE و غیره)، پس
    منطقی است که منتظر کامل‌شدن همه بمانند. اما Brent/DXY/اسپرد اعتباری/
    NFCI هیچ‌کدام چنین تأخیری ندارند (روزانه/هفتگی‌اند)؛ برای آن‌ها از
    get_latest_overlay_row استفاده کنید، وگرنه این بخش پشت زنجیرهٔ رشد/
    تورم گیر می‌کند و عددهای بسیار قدیمی (مثلاً از دورهٔ کووید ۲۰۲۰-۲۰۲۱)
    را به‌جای «همین الان» نشان می‌دهد — این دقیقاً همان باگ Brent YoY بود.
    """
    full_anchor = ["CFNAI_MA3", "INFLATION_MEASURE", "Regime_direction", "top_regime"]
    valid_full = df.dropna(subset=full_anchor)
    if not valid_full.empty:
        return valid_full.iloc[-1]

    partial_anchor = ["CFNAI_MA3", "INFLATION_MEASURE"]
    valid_partial = df.dropna(subset=partial_anchor)
    if not valid_partial.empty:
        return valid_partial.iloc[-1]

    return df.iloc[-1]


def get_latest_overlay_row(df: pd.DataFrame) -> pd.Series:
    """
    برای معیارهای روزانه/هفتگیِ overlay (Brent YoY، تغییر ۳ماههٔ دلار،
    اسپرد اعتباری Baa-10Y، وضعیت NFCI) که هیچ تأخیر انتشار ماهانه‌ای مثل
    CFNAI/PCE ندارند: به‌جای گیر افتادن پشت زنجیرهٔ کامل رشد/تورم/جهت/
    احتمال (که get_reference_row برایش ساخته شده)، فقط آخرین ردیفی که
    خودِ همین چهار ستون مقدار دارند انتخاب می‌شود. این تضمین می‌کند این
    بخش از داشبورد همیشه واقعاً «همین الان» را نشان بدهد، نه ماهی که
    ممکن است رشد/نقدینگی هنوز در آن کامل نشده باشد.
    """
    cols = ["BRENT_YOY", "DXY_PROXY_3M_CHG", "CREDIT_SPREAD_BAA10Y", "Financial_state"]
    valid = df.dropna(subset=cols)
    return valid.iloc[-1] if not valid.empty else df.iloc[-1]


# ==========================================================================
# 5) رابط کاربری Streamlit
# ==========================================================================

def show():
    inject_global_style()
    st.markdown("## 📊 US Macro Regime — Growth × Inflation × Liquidity")
    st.caption("لایهٔ احتمال + Overlay شوک بیرونی + محور تورمِ دوجزئی (این ماه + ماه بعد)")

    try:
        monthly_raw = load_monthly_data()
    except (FileNotFoundError, KeyError) as e:
        st.error(str(e))
        return

    cleveland = fetch_cleveland_fed_nowcast()
    df, inflation_diag = compute_axes(monthly_raw, cleveland)
    ref = get_reference_row(df)
    is_lagged = ref.name != df.index[-1]

    # همیشه تاریخ ماهِ مرجع را نشان بده — حتی وقتی لگ ندارد — تا اگر یک روز
    # این تاریخ غیرمنتظره عقب افتاد (مثلاً به‌خاطر یک باگ جدید در محورها)
    # بلافاصله قابل‌تشخیص باشد، نه فقط وقتی هشدار نارنجی زده می‌شود.
    st.caption(f"📅 ماهِ مرجعِ این گزارش: **{ref.name.strftime('%B %Y')}**  |  "
               f"آخرین ردیف دیتابیس: {df.index[-1].strftime('%B %Y')}")

    missing_probability = pd.isna(ref.get("top_regime"))
    if missing_probability:
        st.error(
            "⚠️ حتی بعد از رفتن به آخرین ماهِ کامل، لایهٔ احتمال/رژیم جهت هنوز NaN است. "
            "این معمولاً یعنی محور نقدینگی (WALCL/WTREGEN/RRPONTSYD) یا پنجرهٔ ۶۰ماههٔ "
            "z-score هنوز به‌اندازهٔ کافی دادهٔ پیوسته ندارد — اگر تاریخچهٔ دیتابیستان "
            "کوتاه‌تر از ~۷ سال است، این طبیعی است، نه باگ."
        )

    if is_lagged:
        months_behind = (df.index[-1].to_period("M") - ref.name.to_period("M")).n
        st.warning(
            f"⚠️ این گزارش مربوط به آخرین ماهی است که همهٔ محورها (رشد، تورم، جهت، احتمال) "
            f"برایش کامل بودند: **{ref.name.strftime('%B %Y')}** "
            f"({months_behind} ماه عقب‌تر از آخرین ردیف دیتابیس)."
        )

    with st.expander("ℹ️ جزئیات فنی محور تورمِ دوجزئی"):
        a_status = "🔮 نوکست (بریج CPI/PPI)" if bool(ref.get("Component_A_Is_Nowcast", False)) else "✅ عدد رسمی"
        if bool(ref.get("Component_B_Is_Nowcast", False)):
            b_status = "🔮 نوکست (کلیولند)"
        elif bool(ref.get("Component_B_Is_Fallback", False)):
            b_status = "↩️ Fallback (چون نه عدد واقعی نه کلیولند در دسترس بود، از Component A استفاده شد)"
        else:
            b_status = "✅ عدد رسمی (شناخته‌شدهٔ گذشته‌نگر)"
        st.markdown(
            f"- **Component A** (تورم {ref.name.strftime('%B %Y')}): `{ref['Component_A']:.2f}%` — {a_status}\n"
            f"- **Component B** (تورم {(ref.name + pd.DateOffset(months=1)).strftime('%B %Y')}): "
            f"`{ref['Component_B']:.2f}%` — {b_status}\n"
            f"- **سنجهٔ نهایی** = 0.5×A + 0.5×B = `{ref['INFLATION_MEASURE']:.2f}%`\n\n"
            f"دقت رگرسیون بریج A (CPI/PPI): R²={inflation_diag['component_a_diag']['fit_r2']:.2f} در صورت فعال بودن، "
            f"با {inflation_diag['component_a_diag']['n_train']} ماه دادهٔ آموزشی.\n\n"
            f"دقت رگرسیون ترجمهٔ نوکست کلیولند (B): R²={inflation_diag['component_b_diag']['fit_r2']:.2f} در صورت فعال بودن، "
            f"با {inflation_diag['component_b_diag']['n_train']} ماه دادهٔ آموزشی."
        )
        if not inflation_diag["component_a_enabled"]:
            st.caption("برای فعال‌سازی نوکست Component A، ستون PPIFES را به دیتابیس اضافه کنید.")
        if not inflation_diag["component_b_cleveland_available"]:
            st.caption("اسکرپ صفحهٔ نوکست کلیولند الان ناموفق بود؛ Component B با fallback به Component A پر شده.")

    # --- کارت‌های رژیم فعلی ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CURRENT REGIME", ref["Regime_level"])
    c2.metric("CFNAI-MA3 (Growth)", f"{ref['CFNAI_MA3']:+.3f}")
    c3.metric("Inflation Measure", f"{ref['INFLATION_MEASURE']:.2f}%")
    c4.metric("Days in Regime", int(ref["Days_in_regime_level"]))

    dir_key = (ref.get("G_dir"), ref.get("I_dir"), ref.get("L_dir"))
    st.markdown(f"**رژیم جهت (Prometheus):** `{ref.get('Regime_direction', 'نامشخص')}`  |  "
                f"**راهنمای دارایی:** {DIRECTION_ASSET_HINTS_8.get(dir_key, 'نامشخص (داده ناکافی)')}")

    # --- لایهٔ احتمال ---
    st.markdown("### 🎲 Probability Layer")
    p1, p2, p3 = st.columns(3)
    p1.metric("رژیم غالب", ref.get("top_regime", "—"), help=f"احتمال: {ref.get('top_regime_prob', float('nan')):.1%}" if pd.notna(ref.get("top_regime_prob")) else None)
    p2.metric("رژیم رقیب", ref.get("second_regime", "—"), help=f"احتمال: {ref.get('second_regime_prob', float('nan')):.1%}" if pd.notna(ref.get("second_regime_prob")) else None)
    ent = ref.get("probability_entropy", np.nan)
    p3.metric("آنتروپی (0-2)", f"{ent:.2f}" if pd.notna(ent) else "—")

    with st.expander("📖 راهنمای خواندن لایهٔ احتمال"):
        st.markdown(
            "- **رژیم غالب**: خانه‌ای از چهار حالت رشد×تورم که بیشترین احتمال را دارد؛ "
            "**confidence** همان احتمال بیشینه است.\n"
            "- **رژیم رقیب**: دومین خانهٔ محتمل. اگر فاصله‌اش با رژیم غالب (**margin**) کم باشد، "
            "یعنی مدل بین دو رژیم مردد است.\n"
            "- **آنتروپی** بین 0 تا 2 است:\n"
            "    - نزدیک به **0** → یک رژیم به‌وضوح غالب است، مدل مطمئن است.\n"
            "    - نزدیک به **2** → احتمال هر چهار رژیم نزدیک هم (~۲۵٪) است، یعنی رژیم "
            "مختلط/نامشخص است.\n"
            "- این سه عدد (confidence / margin / آنتروپی) روی یک سکه‌اند: هرکدام اطمینان "
            "نشان بدهد، آن دو دیگر هم هم‌جهت با آن حرکت می‌کنند.\n"
        )
        st.markdown("---")
        st.markdown("**چرا «رژیم غالب» بالا با «Regime Classification Grid» پایین فرق می‌کند؟**")
        g_lvl, i_lvl = ref.get("G_level"), ref.get("I_level")
        g_chg, i_chg = ref.get("G_chg3m"), ref.get("I_chg3m")
        st.markdown(
            "این دو **دو سنجهٔ کاملاً متفاوت** هستند، نه دو نسخه از یک عدد — عمداً این‌طور طراحی شده:\n\n"
            "| | چه چیزی را می‌سنجد؟ | منطق |\n"
            "|---|---|---|\n"
            "| **Regime Classification Grid** (پایین) | **سطح** رشد/تورم نسبت به یک آستانهٔ مطلقِ ثابت | "
            "مثلاً آیا CFNAI-MA3 از +۰.۱۰ بالاتر است یا از −۰.۵۰ پایین‌تر؟ + هیسترزیس ۲ماهه برای ضدنویز |\n"
            "| **رژیم غالب** (بالا، Probability Layer) | **جهتِ تغییرِ ۳ماههٔ** رشد/تورم، نسبت‌به‌تاریخچهٔ خودش (z-score) | "
            "مثلاً آیا رشد نسبت به ۳ ماه پیش «شتاب گرفته» یا «کند شده»؟ بدون هیسترزیس |\n\n"
            f"**مثال دقیقاً همینِ الان شما:** CFNAI-MA3 برابر `{ref.get('CFNAI_MA3', float('nan')):+.3f}` است — "
            f"این عدد بین آستانه‌های ثابت (+۰.۱۰ تا −۰.۵۰) قرار دارد، پس رژیم سطح می‌شود **G=** "
            f"(نه رونق نه رکود، یعنی «Transition» در گرید). اما تغییر ۳ماههٔ همین عدد "
            f"(`{g_chg:+.3f}` در محور رشد) **مثبت** است — یعنی با اینکه رشد هنوز *در سطح* میانه است، "
            f"*جهتش* رو به بهتر شدن است. چون لایهٔ احتمال فقط به جهت (نه سطح) نگاه می‌کند، "
            f"غالب‌ترین خانه‌اش «Growth Up» می‌شود، درحالی‌که گرید سطح همچنان «Transition» نشان می‌دهد.\n\n"
            "این دقیقاً مثل این است که دمای هوا «معتدل» باشد (سطح) ولی «در حال گرم شدن» هم باشد "
            "(جهت) — هر دو جمله هم‌زمان درست‌اند، چون از دو زاویهٔ متفاوت به یک واقعیت نگاه می‌کنند. "
            "**این باگ نیست** — اگر این دو همیشه دقیقاً یک‌چیز را می‌گفتند، لایهٔ احتمال هیچ اطلاعات "
            "اضافه‌ای روی گرید سطح نمی‌داد."
        )

    # --- نمودار خط‌زمانیِ لایهٔ احتمال (تاریخچهٔ «رژیم غالب»، مثل نمودار رنگیِ گرید سطح) ---
    st.markdown("### 🎲 Probability Layer Timeline")
    prob_plotdf = df.dropna(subset=["top_regime_key"])
    if not prob_plotdf.empty:
        fig_prob = go.Figure()
        fig_prob.add_trace(go.Scatter(x=prob_plotdf.index, y=prob_plotdf["confidence"],
                                       name="Confidence (top_regime_prob)",
                                       line=dict(color="#2f9bd6", width=2)))
        fig_prob.add_trace(go.Scatter(x=prob_plotdf.index, y=2 - prob_plotdf["probability_entropy"],
                                       name="Certainty = 2 − Entropy",
                                       line=dict(color="#e8a33d", width=1, dash="dot"), yaxis="y2"))

        prob_shapes = []
        prev_key, seg_start = None, prob_plotdf.index[0]
        for date, key in prob_plotdf["top_regime_key"].items():
            if key != prev_key:
                if prev_key is not None:
                    prob_shapes.append(dict(type="rect", xref="x", yref="paper", x0=seg_start, x1=date,
                                             y0=0, y1=1, fillcolor=QUADRANT_COLORS.get(prev_key, "#888"),
                                             opacity=0.7, line_width=0))
                seg_start, prev_key = date, key
        if prev_key is not None:
            prob_shapes.append(dict(type="rect", xref="x", yref="paper", x0=seg_start, x1=prob_plotdf.index[-1],
                                     y0=0, y1=1, fillcolor=QUADRANT_COLORS.get(prev_key, "#888"),
                                     opacity=0.7, line_width=0))

        keys_present = prob_plotdf["top_regime_key"].unique().tolist()
        for key in keys_present:
            fig_prob.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                                           marker=dict(size=14, color=QUADRANT_COLORS.get(key, "#888"),
                                                       symbol="square", opacity=0.9),
                                           name=QUADRANT_LABELS.get(key, key), showlegend=True))

        fig_prob.update_layout(
            template="plotly_dark", height=380, shapes=prob_shapes,
            yaxis=dict(title="Confidence", range=[0, 1]),
            yaxis2=dict(title="Certainty (2−Entropy)", overlaying="y", side="right", range=[0, 2]),
            legend=dict(orientation="h", y=1.25, font=dict(size=10)),
            margin=dict(t=70, b=30),
        )
        st.plotly_chart(fig_prob, use_container_width=True)

        prob_legend_html = "<div style='display:flex;flex-wrap:wrap;gap:14px;margin-top:-10px;margin-bottom:10px;'>"
        for key in keys_present:
            color = QUADRANT_COLORS.get(key, "#888")
            prob_legend_html += (f"<div style='display:flex;align-items:center;gap:6px;'>"
                                  f"<span style='width:14px;height:14px;background:{color};border-radius:3px;'></span>"
                                  f"<span style='font-size:12px;color:#ddd;'>{QUADRANT_LABELS.get(key, key)}</span></div>")
        prob_legend_html += "</div>"
        st.markdown(prob_legend_html, unsafe_allow_html=True)
        st.caption(
            "این نمودار «جهتِ تغییر» رشد/تورم را نشان می‌دهد (لایهٔ احتمال)، نه سطح مطلقشان. "
            "برای مقایسه با سطح مطلق (رژیم سنتی Eco3min با هیسترزیس)، نمودار «Regime Timeline» پایین‌تر را ببینید."
        )

    # --- شرایط مالی + overlay شوک ---
    # نکتهٔ مهم: این بخش عمداً از overlay_ref استفاده می‌کند، نه ref.
    # Brent/DXY/اسپرد اعتباری/NFCI روزانه یا هفتگی‌اند و هیچ تأخیر انتشار
    # ماهانه‌ای مثل CFNAI/PCE ندارند؛ اگر از همان ref (که منتظر کامل‌شدن
    # زنجیرهٔ کامل رشد/تورم/جهت/احتمال می‌ماند) استفاده می‌شد، این بخش
    # می‌توانست پشت یک ماه بسیار قدیمی گیر بیفتد و اعداد بی‌ربط (مثلاً
    # Brent YoY متعلق به دورهٔ کووید ۲۰۲۰-۲۰۲۱) نشان بدهد — دقیقاً همان
    # باگی که گزارش شد.
    overlay_ref = get_latest_overlay_row(df)
    overlay_is_lagged = overlay_ref.name != df.index[-1]

    st.markdown("### 🏦 Financial Conditions & Shock Overlay")
    if overlay_ref.name != ref.name:
        st.caption(
            f"ℹ️ این بخش تاریخ مرجع جداگانه‌ای دارد (چون داده‌اش روزانه/هفتگی است، نه ماهانه): "
            f"**{overlay_ref.name.strftime('%Y-%m-%d')}** — درحالی‌که بخش رشد/تورم بالا مربوط به "
            f"**{ref.name.strftime('%B %Y')}** است."
        )
    if overlay_is_lagged:
        st.warning(
            f"⚠️ حتی این بخش هم به آخرین ردیف دیتابیس نرسیده — آخرین تاریخِ کاملِ Brent/DXY/اسپرد: "
            f"**{overlay_ref.name.strftime('%Y-%m-%d')}** (آخرین ردیف دیتابیس: {df.index[-1].strftime('%Y-%m-%d')}). "
            f"اگر این فاصله زیاد است، یکی از ستون‌های DCOILBRENTEU/DTWEXBGS/BAA10Y/NFCI در دیتابیس شما "
            f"مدتی است به‌روزرسانی نشده."
        )

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("NFCI State", overlay_ref.get("Financial_state", "—"))
    f2.metric("Brent YoY", f"{overlay_ref['BRENT_YOY']:+.1f}%" if pd.notna(overlay_ref.get("BRENT_YOY")) else "—")
    f3.metric("DXY 3M Δ", f"{overlay_ref['DXY_PROXY_3M_CHG']:+.1f}%" if pd.notna(overlay_ref.get("DXY_PROXY_3M_CHG")) else "—")
    f4.metric("Baa-10Y Spread", f"{overlay_ref['CREDIT_SPREAD_BAA10Y']:.2f}" if pd.notna(overlay_ref.get("CREDIT_SPREAD_BAA10Y")) else "—")

    # شفافیت: دقیقاً نشان بده کدام دو عدد و کدام دو تاریخ در محاسبهٔ Brent YoY
    # مقایسه شده‌اند — اگر عدد YoY غیرمنتظره بود، اینجا فوراً معلوم می‌شود
    # که ایراد از «ماه مرجع اشتباه» است یا «یک مقدار خراب در دیتابیس».
    brent_now, brent_ago = overlay_ref.get("BRENT_LEVEL_NOW"), overlay_ref.get("BRENT_LEVEL_12M_AGO")
    date_now = overlay_ref.name
    date_ago = overlay_ref.name - pd.DateOffset(months=12)
    with st.expander("🔍 محاسبهٔ دقیق Brent YoY (برای دیباگ عدد غیرمنتظره)"):
        st.markdown(
            f"- قیمت Brent در ماهِ مرجعِ overlay (**{date_now.strftime('%B %Y')}**): "
            f"`${brent_now:.2f}`" if pd.notna(brent_now) else f"- قیمت Brent در {date_now.strftime('%B %Y')}: نامعلوم (NaN)"
        )
        st.markdown(
            f"- قیمت Brent در ۱۲ ماه پیش از آن (**{date_ago.strftime('%B %Y')}**): "
            f"`${brent_ago:.2f}`" if pd.notna(brent_ago) else f"- قیمت Brent در {date_ago.strftime('%B %Y')}: نامعلوم (NaN)"
        )
        if pd.notna(brent_now) and pd.notna(brent_ago):
            st.markdown(f"- فرمول: `({brent_now:.2f} − {brent_ago:.2f}) / {brent_ago:.2f} × 100` = **{overlay_ref['BRENT_YOY']:+.1f}%**")
        st.markdown(
            "اگر تاریخ بالا با تاریخ امروز فاصلهٔ زیادی دارد، یا اگر یکی از این دو قیمت با قیمت "
            "واقعی بازار در همان تاریخ همخوانی ندارد، مشکل از یکی از این دو جاست:\n"
            "1. **ستون DCOILBRENTEU در دیتابیس شما مدتی است به‌روزرسانی نشده** — آخرین ردیف دیتابیس "
            f"را با آخرین تاریخِ بالا مقایسه کنید.\n"
            "2. **یک مقدار خراب/گم‌شده در ستون DCOILBRENTEU دیتابیس شما**, دقیقاً نزدیک یکی از "
            "این دو تاریخ (مثلاً یک شکاف در بک‌فیل دادهٔ نفت که با یک عدد اشتباه یا قیمت یک دورهٔ "
            "کاملاً متفاوت پر شده). برای رفع، مقدار DCOILBRENTEU را دقیقاً حوالی این دو تاریخ در "
            "فایل CSV خودتان چک کنید."
        )

    if bool(ref.get("Headline_Underlying_Divergence_Flag", False)):
        st.warning("⚠️ پرچم واگرایی تورمی فعال — شوک نفتی/کالایی از تورم ساختاری جداست.")
    if bool(overlay_ref.get("Shock_Alert", False)):
        st.error("⚠️ هشدار شوک بیرونی فعال (نفت/دلار/اسپرد اعتباری).")

    # --- گرید نام‌گذاری رژیم ---
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

    # --- راهنمای کامل دارایی برای هر ۸ ترکیب ---
    with st.expander("💰 راهنمای دارایی برای هر ۸ ترکیب Growth × Inflation × Liquidity"):
        for (g, i, l), text in DIRECTION_ASSET_HINTS_8.items():
            highlight = " 👈 **الان اینجاییم**" if (g, i, l) == dir_key else ""
            st.markdown(f"**({g})G({i})I({l})L**{highlight}\n\n{text}\n")

    # --- نمودار خط‌زمانی ---
    st.markdown("### Regime Timeline")
    plotdf = df.dropna(subset=["Regime_level"])
    REGIME_BAND_OPACITY = 0.7

    if not plotdf.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=plotdf.index, y=plotdf["CFNAI_MA3"], name="CFNAI-MA3 (Growth)",
                                  line=dict(color="#2f9bd6", width=2)))
        fig.add_trace(go.Scatter(x=plotdf.index, y=plotdf["INFLATION_MEASURE"], name="Inflation Measure (%)",
                                  line=dict(color="#e8a33d", width=2), yaxis="y2"))
        fig.add_trace(go.Scatter(x=plotdf.index, y=plotdf["confidence"], name="Model Confidence",
                                  line=dict(color="#bbbbbb", width=1, dash="dot"), yaxis="y3"))

        shapes = []
        prev, seg_start = None, plotdf.index[0]
        for date, regime in plotdf["Regime_level"].items():
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

        regimes_present = plotdf["Regime_level"].unique().tolist()
        for regime in regimes_present:
            color = REGIME_COLORS.get(regime, "#888")
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                                      marker=dict(size=14, color=color, symbol="square", opacity=0.9),
                                      name=regime, showlegend=True))

        fig.update_layout(
            template="plotly_dark", height=480, shapes=shapes,
            yaxis=dict(title="CFNAI-MA3"),
            yaxis2=dict(title="Inflation (%)", overlaying="y", side="right"),
            yaxis3=dict(overlaying="y", side="right", showticklabels=False, range=[0, 1]),
            legend=dict(orientation="h", y=1.18, font=dict(size=11)),
            margin=dict(t=60, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

        legend_html = "<div style='display:flex;flex-wrap:wrap;gap:14px;margin-top:-10px;margin-bottom:10px;'>"
        for regime in regimes_present:
            color = REGIME_COLORS.get(regime, "#888")
            legend_html += (f"<div style='display:flex;align-items:center;gap:6px;'>"
                             f"<span style='width:14px;height:14px;background:{color};border-radius:3px;'></span>"
                             f"<span style='font-size:13px;color:#ddd;'>{regime}</span></div>")
        legend_html += "</div>"
        st.markdown(legend_html, unsafe_allow_html=True)

    # --- تاریخچهٔ ۱۲ ماه اخیر ---
    st.markdown("### Last 12 Months")
    hist = plotdf[["G_level", "I_level", "Regime_level", "Financial_state",
                    "top_regime", "confidence", "Shock_Alert"]].tail(12).copy()
    hist.index = hist.index.strftime("%Y-%m")
    st.dataframe(hist, use_container_width=True)

    # --- توزیع رژیم‌ها ---
    st.markdown("### Time Spent in Each Regime (Full History)")
    if not plotdf.empty:
        st.bar_chart((plotdf["Regime_level"].value_counts(normalize=True) * 100).round(1))

    # --- بک‌تست Component A (بریج CPI/PPI) ---
    if inflation_diag["component_a_enabled"]:
        st.markdown("### 🔬 Backtest — Component A (CPI/PPI Bridge)")
        bt_a = walkforward_backtest(monthly_raw, "PCETRIM12M159SFRBDAL", tuple(inflation_diag["component_a_predictors"]))
        if not bt_a.empty:
            mae = bt_a["Error"].abs().mean()
            r2 = 1 - (bt_a["Error"] ** 2).sum() / ((bt_a["Actual"] - bt_a["Actual"].mean()) ** 2).sum()
            bc1, bc2 = st.columns(2)
            bc1.metric("MAE", f"{mae:.2f}")
            bc2.metric("R² (Out-of-Sample)", f"{r2:.2f}")
            fig_a = go.Figure()
            fig_a.add_trace(go.Scatter(x=bt_a.index, y=bt_a["Actual"], name="Actual", line=dict(color="#66bb6a")))
            fig_a.add_trace(go.Scatter(x=bt_a.index, y=bt_a["Nowcast"], name="Bridge Estimate",
                                        line=dict(color="#ff5252", dash="dot")))
            fig_a.update_layout(template="plotly_dark", height=300, margin=dict(t=20, b=20),
                                 legend=dict(orientation="h", y=1.15))
            st.plotly_chart(fig_a, use_container_width=True)

    st.caption(
        "منبع داده: macro_database.csv (فقط‌خواندنی) | روش‌شناسی رژیم: Eco3min + Prometheus | "
        f"آخرین ردیف دیتابیس: {df.index[-1].strftime('%Y-%m-%d')}"
    )