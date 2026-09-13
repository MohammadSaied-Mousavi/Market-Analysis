"""
Global theme for Macro × Bond Regime Framework.

این فایل استایل مشترک کل پروژه را مدیریت می‌کند:
- فونت
- RTL / bidirectional text
- رنگ Accent
- دکمه‌ها
- Sidebar
- Sidebar footer
- حذف Navigation پیش‌فرض Streamlit
"""

import streamlit as st


# ==========================================================
# THEME
# ==========================================================

ACCENT = "#c9a24b"
ACCENT_SOFT = "rgba(201,162,75,0.45)"


# ==========================================================
# GLOBAL STYLE
# ==========================================================

def inject_global_style() -> None:
    st.markdown(
        f"""
        <style>

        /* ==========================================================
           GLOBAL FONT
           ========================================================== */

        @import url(
            'https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap'
        );

        html,
        body,
        .stApp,
        [data-testid="stAppViewContainer"] {{
            font-family: 'Vazirmatn', Arial, sans-serif;
        }}

        /*
        فقط عناصر متنی مشخص را با !important کنترل می‌کنیم
        تا Material Symbols و آیکون‌های Streamlit خراب نشوند.
        */

        h1,
        h2,
        h3,
        h4,
        h5,
        h6,
        p,
        label,
        .stMarkdown,
        div.stButton button,
        input,
        textarea {{
            font-family: 'Vazirmatn', Arial, sans-serif !important;
        }}


        /* ==========================================================
           RTL / BIDIRECTIONAL TEXT
           ========================================================== */

        p,
        div,
        span,
        li,
        td,
        th,
        label,
        h1,
        h2,
        h3,
        h4,
        h5,
        h6 {{
            unicode-bidi: plaintext;
        }}


        /* ==========================================================
           GLOBAL BUTTON
           ========================================================== */

        div.stButton > button {{
            border-radius: 12px;
            border: 1.5px solid {ACCENT_SOFT};
            background-color: rgba(201,162,75,0.08);
            color: #f2f2f2;
            transition: 0.25s;
        }}

        div.stButton > button:hover {{
            background: {ACCENT};
            border-color: {ACCENT};
            color: #111111;
            box-shadow: 0 0 18px rgba(201,162,75,0.4);
        }}


        /* ==========================================================
           SIDEBAR
           ========================================================== */

        [data-testid="stSidebar"] {{
            position: relative;
            padding-bottom: 76px;
        }}

        /* ==========================================================
           CUSTOM SIDEBAR RADIO NAVIGATION
           ========================================================== */

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        > div[role="radiogroup"] {{
            gap: 2px;
        }}

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        label {{
            border-radius: 8px;
            padding: 6px 10px;
            width: 100%;
            transition:
                background-color 0.15s ease,
                color 0.15s ease;
        }}

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        label:hover {{
            background-color: rgba(255,255,255,0.05);
        }}

        /*
        حذف دایره‌ی Radio
        */

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        label > div:first-child {{
            display: none;
        }}

        /*
        گزینه‌ی فعال
        */

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        label:has(input:checked) {{
            background-color: {ACCENT}22;
        }}

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        label:has(input:checked) p {{
            color: {ACCENT};
            font-weight: 700;
        }}

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        label p {{
            font-size: 14px;
            color: #b8bcc4;
            margin: 0;
        }}


        /* ==========================================================
           SIDEBAR FOOTER
           ========================================================== */

        [data-testid="stSidebar"]::after {{
            content:
                "Macro Analysis App\\A"
                "Framework · v0.8\\A"
                "Seyed Mohammad Saeid Mousavi";

            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;

            padding: 12px 16px 14px 16px;

            text-align: center;

            white-space: pre-line;

            font-family:
                'Vazirmatn',
                Arial,
                sans-serif;

            font-size: 11px;
            line-height: 1.7;

            letter-spacing: 0.2px;

            color: #6b7280;

            border-top:
                1px solid rgba(255,255,255,0.08);

            background: inherit;
        }}


        /* ==========================================================
           SIDEBAR FOOTER TITLE
           ========================================================== */

        /*
        این بخش عمداً خیلی subtle نگه داشته شده تا
        Footer با Navigation رقابت نکند.
        */


        /* ==========================================================
           END
           ========================================================== */

        </style>
        """,
        unsafe_allow_html=True,
    )