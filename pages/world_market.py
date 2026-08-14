import streamlit as st

from world_market import Dashboard
from world_market import correlation
from world_market import macro
from world_market import prediction
from world_market import charts
from world_market import HL_Funding_Explorer
from theme import inject_global_style

st.set_page_config(
    page_title="Global Market",
    page_icon="🌍",
    layout="wide"
)

# ---------------- Sidebar ---------------- #

st.sidebar.title("🌍 Global Market")
page = st.sidebar.radio(
    "Select Page",
    [
        "📊 Dashboard",
        "📈 Charts",
        "🔄 Correlation",
        "🪙 Macro",
        "💰 Hyper Liquid",
        "💸 Prediction"
    ]
)

# ---------------- Dashboard ---------------- #

if page == "📊 Dashboard":
    Dashboard.show()

# ---------------- Charts ---------------- #

elif page == "📈 Charts":
    charts.show()

# ---------------- Correlation ---------------- #

elif page == "🔄 Correlation":
    correlation.show()

# ---------------- Economic Regime ---------------- #

elif page == "🪙 Macro":
    macro.show()

# ---------------- Hyper Liquid ---------------- #

elif page == "💰 Hyper Liquid":
    HL_Funding_Explorer.show_hl_explorer()

# ---------------- Prediction ---------------- #

elif page == "💸 Prediction":
    prediction.show()