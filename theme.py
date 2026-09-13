"""
استایل مشترک کل پروژه — فونت + رنگ لهجه (accent) + استایل پایه‌ی دکمه‌ها.

چون Streamlit چندصفحه‌ای هر فایل را مستقل اجرا می‌کند،
تزریق CSS توی یک صفحه به بقیه سرایت نمی‌کند.

برای همین این تابع باید همان اول هر تابع show()
(توی هر صفحه‌ای که هست) صدا زده بشه:

    from theme import inject_global_style
    inject_global_style()

استایل‌های اختصاصی هر صفحه همچنان در همان فایل می‌مانند.
"""

import streamlit as st


# ==========================================================
# THEME
# ==========================================================

ACCENT = "#c9a24b"
ACCENT_SOFT = "rgba(201,162,75,0.45)"


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

        /*
        پایه: از طریق ارث‌بری معمولی CSS روی همه‌چیز اعمال می‌شود.
        عمداً روی span/div عمومی !important نگذاشته‌ایم تا فونت
        آیکون‌های Streamlit مثل Material Symbols خراب نشود.
        */

        html,
        body,
        .stApp,
        [data-testid="stAppViewContainer"] {{
            font-family: 'Vazirmatn', Arial, sans-serif;
        }}

        /*
        !important فقط روی عناصر متنی مشخص.
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
           SIDEBAR NAV
           یکپارچه‌سازی ظاهر دو نوع ناوبری
           ========================================================== */


        /* ----------------------------------------------------------
           ناوبری بومی چندصفحه‌ای
           app / iran market / world market
           ---------------------------------------------------------- */

        [data-testid="stSidebarNavItems"] > li > div > a {{
            border-radius: 8px;
            padding: 6px 10px !important;
            transition:
                background-color 0.15s ease,
                color 0.15s ease;
        }}

        [data-testid="stSidebarNavItems"] > li > div > a span {{
            font-size: 14px;
            color: #b8bcc4;
        }}

        [data-testid="stSidebarNavItems"] > li > div > a:hover {{
            background-color: rgba(255,255,255,0.05);
        }}

        [data-testid="stSidebarNavItems"]
        > li
        > div
        > a[aria-current="page"] {{
            background-color: {ACCENT}22;
        }}

        [data-testid="stSidebarNavItems"]
        > li
        > div
        > a[aria-current="page"]
        span {{
            color: {ACCENT};
            font-weight: 700;
        }}


        /* ----------------------------------------------------------
           منوی رادیویی دستی
           Dashboard / Charts / Correlation / ...
           ---------------------------------------------------------- */

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
            transition: background-color 0.15s ease;
        }}

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        label:hover {{
            background-color: rgba(255,255,255,0.05);
        }}

        /*
        دایره‌ی رادیو حذف می‌شود.
        فقط پس‌زمینه‌ی گزینه‌ی فعال نمایش داده می‌شود.
        */

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        label > div:first-child {{
            display: none;
        }}

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
           نام ثابت پایین سایدبار
           ========================================================== */

        [data-testid="stSidebar"] {{
            position: relative;
            padding-bottom: 46px;
        }}

        [data-testid="stSidebar"]::after {{
            content: "Seyed Mohammad Saeid Mousavi";
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;

            padding: 12px 16px;

            text-align: center;

            font-size: 12px;
            letter-spacing: 0.3px;

            color: #6b7280;

            border-top:
                1px solid rgba(255,255,255,0.08);

            background: inherit;
        }}


        /* ==========================================================
           END
           ========================================================== */

        </style>
        """,
        unsafe_allow_html=True,
    )