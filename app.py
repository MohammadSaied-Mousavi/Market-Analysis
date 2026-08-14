import streamlit as st
import os

from constants import ROOT_DIR
from theme import inject_global_style

# =====================================================
# تنظیمات صفحه
# =====================================================

st.set_page_config(
    page_title="Macro Analysis",
    page_icon="🌍",
    layout="wide"
)

# =====================================================
# مسیر فایل ها
# =====================================================

img_iran = os.path.join(ROOT_DIR, "Media", "2.jpg")
img_global = os.path.join(ROOT_DIR, "Media", "1.jpg")

# =====================================================
# استایل مشترک کل سایت (فونت + دکمه‌ی پایه) + CSS اختصاصی این صفحه
# =====================================================

inject_global_style()

st.markdown("""
<style>

/* عنوان */

h1{
    text-align:center;
    font-size:48px;
    font-weight:800;
    letter-spacing:-0.5px;
}

/* متن زیر عنوان */

.subtitle{
    text-align:center;
    font-size:17px;
    color:#8a8f98;
    letter-spacing:0.3px;
    margin-bottom:40px;
}

/* -----------------------------------------------------------
   کارت (عکس + برچسب + دکمه، همه با هم یک شکل واحد)
   st.container(key=...) یه API رسمی خودِ Streamlit‌ه (نه testid
   داخلی حدسی)، پس کلاس st-key-card-* بین نسخه‌ها ثابت می‌مونه.
----------------------------------------------------------- */

div[class*="st-key-card-"]{
    position:relative;
    overflow:hidden;
    border-radius:20px;
    border:1px solid rgba(255,255,255,0.09);
    background:rgba(255,255,255,0.025);
    padding-bottom:18px;
    transition:transform .35s cubic-bezier(.2,.8,.2,1),
               box-shadow .35s ease,
               border-color .35s ease;
}

div[class*="st-key-card-"]:hover{
    transform:translateY(-6px) scale(1.015);
    box-shadow:0 22px 42px rgba(0,0,0,0.45);
    border-color:rgba(201,162,75,0.55);
}

div[class*="st-key-card-"] img{
    border-radius:0;
    display:block;
}

/* برچسب کوچیک بالای دکمه (eyebrow) */

.card-eyebrow{
    font-size:13px;
    color:#c9a24b;
    letter-spacing:0.5px;
    font-weight:700;
    margin:16px 20px 2px 20px;
    text-align:center;
}

.card-desc{
    font-size:14px;
    color:#8a8f98;
    margin:0 20px 14px 20px;
    line-height:1.6;
    text-align:center;
}

/* سایز اختصاصی دکمه‌های همین صفحه (بزرگ‌تر از پیش‌فرض سایت) */
/* رنگ/هاور از theme.py مشترک میاد، فقط اندازه اینجا override می‌شه */

div.stButton{
    padding:0 20px;
}

div[class*="st-key-card-"] div.stButton > button{
    width:100%;
    height:56px;
    font-size:18px;
    font-weight:700;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# عنوان
# =====================================================

st.title("🌍 Macro Analysis")

st.markdown(
    "<div class='subtitle'>بخش مورد نظر را انتخاب کنید</div>",
    unsafe_allow_html=True
)

# =====================================================
# دو ستون
# =====================================================

col1, col2 = st.columns(2, gap="large")

# =====================================================
# بورس ایران
# =====================================================

with col1:
    with st.container(key="card-iran"):

        st.image(str(img_iran), width="stretch")

        st.markdown("<div class='card-eyebrow'>بازار داخلی</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='card-desc'>شاخص کل، صنایع، نمادها و صندوق‌های بورس تهران</div>",
            unsafe_allow_html=True,
        )

        if st.button(
            "📈  ورود به بخش تحلیل بورس ایران",
            use_container_width=True
        ):
            st.switch_page("pages/iran_market.py")

# =====================================================
# بازار جهانی
# =====================================================

with col2:
    with st.container(key="card-global"):

        st.image(str(img_global), width="stretch")

        st.markdown("<div class='card-eyebrow'>بازار بین‌المللی</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='card-desc'>بورس آمریکا، طلا، ارز، رمزارز و رژیم‌های اقتصادی</div>",
            unsafe_allow_html=True,
        )

        if st.button(
            "🌍  ورود به بخش تحلیل بازارهای جهانی",
            use_container_width=True
        ):
            st.switch_page("pages/world_market.py")