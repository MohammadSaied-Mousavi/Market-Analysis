"""
استایل مشترک کل پروژه — فونت + رنگ لهجه (accent) + استایل پایه‌ی دکمه‌ها.

چون Streamlit چندصفحه‌ای هر فایل رو مستقل اجرا می‌کنه، تزریق CSS توی یه
صفحه به بقیه سرایت نمی‌کنه. برای همین این تابع باید همون اول هر تابع
show() (توی هر صفحه‌ای که هست) صدا زده بشه:

    from theme import inject_global_style
    inject_global_style()

استایل‌های اختصاصیِ خودِ یه صفحه (مثل کارت‌های صفحه‌ی اصلی) همچنان توی
همون فایل می‌مونن؛ فقط چیزی که باید همه‌جا یکسان باشه (فونت، لهجه‌ی
دکمه‌ها) اینجاست.
"""

import streamlit as st

ACCENT = "#c9a24b"
ACCENT_SOFT = "rgba(201,162,75,0.45)"


def inject_global_style() -> None:
    st.markdown(
        """
        <style>

        @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap');

        /* پایه: از طریق ارث‌بری معمولی CSS (بدون !important) روی همه‌چیز
           اعمال می‌شه، از جمله آیکون‌ها — ولی چون قانون خودِ Streamlit
           برای فونت آیکون (Material Symbols) specificity بالاتری داره،
           آیکون‌ها دست‌نخورده می‌مونن. */
        html, body, .stApp, [data-testid="stAppViewContainer"] {
            font-family:'Vazirmatn', Arial, sans-serif;
        }

        /* !important فقط روی عنصرهای متنیِ مشخص — عمداً span/div عمومی
           اینجا نیست، چون دقیقاً همونجاست که فونت آیکون‌های Streamlit
           (مثل فلش جمع‌کردن سایدبار) زندگی می‌کنه؛ !important زدن روی
           span/div اون آیکون‌ها رو می‌شکنه و به‌جای فلش، متن خام
           (مثل "keyboard_double_arrow_left") نشون می‌ده. */
        h1, h2, h3, h4, h5, h6, p, label,
        .stMarkdown, div.stButton button, input, textarea {
            font-family:'Vazirmatn', Arial, sans-serif !important;
        }

        /* دکمه‌ی پیش‌فرض کل سایت — لهجه‌ی طلایی */
        /* راست‌چین خودکار برای متن‌هایی که با حروف فارسی/عربی شروع
           می‌شن، بدون خراب‌کردن چپ‌چینیِ متن انگلیسی — از الگوریتم
           استاندارد دوجهته‌ی یونیکد استفاده می‌کنه (دقیقاً همون کاری
           که ویژگی HTML به‌نام dir="auto" می‌کنه، ولی این‌جا سراسری
           و بدون نیاز به تغییر هر تگ به‌صورت دستی) */
        p, div, span, li, td, th, label,
        h1, h2, h3, h4, h5, h6 {
            unicode-bidi: plaintext;
        }

        div.stButton > button{
            border-radius:12px;
            border:1.5px solid rgba(201,162,75,0.45);
            background-color:rgba(201,162,75,0.08);
            color:#f2f2f2;
            transition:0.25s;
        }

        div.stButton > button:hover{
            background:#c9a24b;
            border-color:#c9a24b;
            color:#111111;
            box-shadow:0 0 18px rgba(201,162,75,0.4);
        }

        </style>
        """,
        unsafe_allow_html=True,
    )