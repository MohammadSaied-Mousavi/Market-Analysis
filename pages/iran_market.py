import streamlit as st

from iran_market import stocks
from iran_market import heatmap
from iran_market import indices
from iran_market import funds
from iran_market import derivatives

st.set_page_config(
    page_title="بورس ایران",
    layout="wide"
)

# =====================================
# Header
# =====================================

st.title("🇮🇷 بورس ایران")

if st.button("🏠 صفحه اصلی"):
    st.switch_page("app.py")

st.write("به بخش بورس ایران خوش آمدید.")

# =====================================
# Sidebar
# =====================================

st.sidebar.title("منو")

main_menu = st.sidebar.radio(
    "بخش",
    [
        "سهام",
        "شاخص‌ها",
        "مشتقه",
        "صندوق‌ها"
    ],
    label_visibility="collapsed"
)

# =====================================
# STOCKS
# =====================================

if main_menu == "سهام":

    stock_menu = st.sidebar.radio(
        "زیر بخش سهام",
        [
            "اطلاعات سهم",
            "Heatmap صنایع"
        ]
    )

    if stock_menu == "اطلاعات سهم":
        stocks.show()

    elif stock_menu == "Heatmap صنایع":
        heatmap.show()

# =====================================
# INDICES
# =====================================

elif main_menu == "شاخص‌ها":

    indices.show()

# =====================================
# DERIVATIVES
# =====================================

elif main_menu == "مشتقه":

    derivatives.show()

# =====================================
# FUNDS
# =====================================

elif main_menu == "صندوق‌ها":

    funds.show()