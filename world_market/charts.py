import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from theme import inject_global_style

# ==========================================
# Database
# ==========================================

DATABASE_PATH = r"D:\project\database\macro_database.csv"

# ==========================================
# Load Database
# ==========================================

@st.cache_data
def load_database():

    df = pd.read_csv(
        DATABASE_PATH,
        parse_dates=["Date"]
    )

    df.sort_values("Date", inplace=True)

    df.set_index("Date", inplace=True)

    return df


# ==========================================
# Time Frames
# ==========================================

TIMEFRAMES = {

    "1 Day": "D",

    "1 Week": "W",

    "1 Month": "M"

}


# ==========================================
# Read Data From CSV
# ==========================================

def get_data(column, timeframe):

    df = load_database()

    if column not in df.columns:

        return None

    data = df[[column]].copy()

    data.columns = ["close"]

    data = data.dropna()

    if timeframe == "D":

        return data

    elif timeframe == "W":

        data = (
            data
            .resample("W")
            .last()
            .dropna()
        )

        return data

    elif timeframe == "M":

        data = (
            data
            .resample("ME")
            .last()
            .dropna()
        )

        return data

    return data
# ==========================================
# Stock Market Symbols
# ==========================================

STOCKS = {

    "S&P500": "SP500",

    "Nasdaq 100": "NASDAQ",

    "Dow Jones": "DOW",

    "Russell 2000": "RUSSELL",

    "DAX": "DAX",

    "FTSE100": "FTSE100",

    "Nikkei225": "Nikkei225",

    "China A50": "China A50",

    "CSI 300": "CSI300"

}
# ==========================================
# Forex Symbols
# ==========================================

FOREX = {

    "🇪🇺 EUR/USD": "EURUSD",

    "🇬🇧 GBP/USD": "GBPUSD",

    "🇯🇵 USD/JPY": "USDJPY",

    "🇨🇦 USD/CAD": "USDCAD",

    "🇦🇺 AUD/USD": "AUDUSD"

}
# ==========================================
# Crypto Symbols
# ==========================================

CRYPTO = {

    "₿ Bitcoin": "BTC",

    "Ξ Ethereum": "ETH",

    "ETH / BTC Ratio": "ETHBTC"

}
# ==========================================
# Commodities
# ==========================================

COMMODITIES = {

    "WTI Crude Oil": "WTI",

    "Natural Gas": "Natural Gas",

    "Gold": "GOLD",

    "Silver": "SILVER",

    "Copper": "XCUUSD",

    "Iron Ore": "Iron Ore"

}
US_NOMINAL = {

    "3M": "3M",

    "2Y": "2Y",

    "5Y": "5Y",

    "10Y": "10Y",

    "30Y": "30Y"

}

US_REAL = {

    "5Y": "DFII5",

    "10Y": "DFII10"

}

BONDS = {

    "🇩🇪 Germany": {

        "2Y": "GER2Y",

        "10Y": "GER10Y"

    },

    "🇮🇹 Italy": {

        "2Y": "ITA2Y",

        "10Y": "ITA10Y"

    },

    "🇬🇧 United Kingdom": {

        "2Y": "UK2Y",

        "10Y": "UK10Y"

    },

    "🇨🇦 Canada": {

        "2Y": "CAN2Y",

        "10Y": "CAN10Y"

    },

    "🇯🇵 Japan": {

        "2Y": "JPN2Y",

        "10Y": "JPN10Y"

    },

    "🇦🇺 Australia": {

        "2Y": "AUS2Y",

        "10Y": "AUS10Y"

    }

}
# ==========================================
# Plot Function
# ==========================================

def draw_chart(df, title):

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=df.index,

            y=df["close"],

            mode="lines",

            name=title,

            line=dict(width=2)

        )

    )

    fig.update_layout(

        template="plotly_dark",

        title=title,

        height=700,

        hovermode="x unified",

        xaxis_title="",

        yaxis_title="Price",

        margin=dict(

            l=20,

            r=20,

            t=60,

            b=20

        )

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )


# ==========================================
# Stock Market
# ==========================================

def stock_market():

    st.title("📈 Stock Market")

    col1, col2 = st.columns([2,1])

    with col1:

        index = st.selectbox(

            "Index",

            list(STOCKS.keys())

        )

    with col2:

        timeframe = st.selectbox(

            "Time Frame",

            list(TIMEFRAMES.keys())

        )

    column = STOCKS[index]

    df = get_data(

        column,

        TIMEFRAMES[timeframe]

    )

    if df is None or df.empty:

        st.error("No Data Found")

        return

    st.metric(

        "Last Price",

        round(float(df["close"].iloc[-1]),2)

    )

    draw_chart(

        df,

        index

    )
# ==========================================
# Bond Market
# ==========================================

def bond_market():

    st.title("📉 Bond Market")

    # ==========================
    # Country
    # ==========================

    col1, col2 = st.columns([2,1])

    with col1:

        country = st.selectbox(

            "Country",

            ["🇺🇸 United States"] + list(BONDS.keys())

        )

    with col2:

        timeframe = st.selectbox(

            "Time Frame",

            list(TIMEFRAMES.keys()),

            key="bond_tf"

        )

    # ==========================
    # United States
    # ==========================

    if country == "🇺🇸 United States":

        yield_type = st.selectbox(

            "Yield Type",

            [

                "Nominal Yield",

                "Real Yield"

            ],

            key="yield_type"

        )

        if yield_type == "Nominal Yield":

            selected = US_NOMINAL

        else:

            selected = US_REAL

    # ==========================
    # Other Countries
    # ==========================

    else:

        selected = BONDS[country]

    # ==========================
    # Plot
    # ==========================

    fig = go.Figure()

    has_data = False

    for maturity, column in selected.items():

        df = get_data(

            column,

            TIMEFRAMES[timeframe]

        )

        if df is None or df.empty:

            continue

        has_data = True

        fig.add_trace(

            go.Scatter(

                x=df.index,

                y=df["close"],

                mode="lines",

                name=maturity,

                line=dict(width=2)

            )

        )

    if not has_data:

        st.warning("No Data Found")

        return

    fig.update_layout(

        template="plotly_dark",

        title=country,

        height=700,

        hovermode="x unified",

        xaxis_title="",

        yaxis_title="Yield (%)",

        legend_title="Maturity",

        margin=dict(

            l=20,

            r=20,

            t=60,

            b=20

        )

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )
# ==========================================
# Forex Market
# ==========================================

def forex_market():

    st.title("💱 Forex Market")

    col1, col2 = st.columns([2,1])

    with col1:

        pair = st.selectbox(

            "Currency Pair",

            list(FOREX.keys())

        )

    with col2:

        timeframe = st.selectbox(

            "Time Frame",

            list(TIMEFRAMES.keys()),

            key="forex_tf"

        )

    column = FOREX[pair]

    df = get_data(

        column,

        TIMEFRAMES[timeframe]

    )

    if df is None or df.empty:

        st.error("No Data Found")

        return

    st.metric(

        "Last Price",

        round(float(df["close"].iloc[-1]),5)

    )

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=df.index,

            y=df["close"],

            mode="lines",

            name=pair,

            line=dict(width=2)

        )

    )

    fig.update_layout(

        template="plotly_dark",

        title=pair,

        height=700,

        hovermode="x unified",

        xaxis_title="",

        yaxis_title="Exchange Rate",

        legend_title="Pair",

        margin=dict(

            l=20,

            r=20,

            t=60,

            b=20

        )

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )


# ==========================================
# Crypto Market
# ==========================================

def crypto_market():

    st.title("🪙 Crypto Market")

    col1, col2 = st.columns([2,1])

    with col1:

        coin = st.selectbox(

            "Asset",

            list(CRYPTO.keys())

        )

    with col2:

        timeframe = st.selectbox(

            "Time Frame",

            list(TIMEFRAMES.keys()),

            key="crypto_tf"

        )

    column = CRYPTO[coin]

    df = get_data(

        column,

        TIMEFRAMES[timeframe]

    )

    if df is None or df.empty:

        st.error("No Data Found")

        return

    st.metric(

        "Last Price",

        round(float(df["close"].iloc[-1]),4)

    )

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=df.index,

            y=df["close"],

            mode="lines",

            name=coin,

            line=dict(width=2)

        )

    )

    fig.update_layout(

        template="plotly_dark",

        title=coin,

        height=700,

        hovermode="x unified",

        xaxis_title="",

        yaxis_title="Price",

        legend_title="Asset",

        margin=dict(

            l=20,

            r=20,

            t=60,

            b=20

        )

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )


# ==========================================
# Commodity Market
# ==========================================

def commodity_market():

    st.title("🛢 Commodities")

    col1, col2 = st.columns([2,1])

    with col1:

        commodity = st.selectbox(

            "Commodity",

            list(COMMODITIES.keys())

        )

    with col2:

        timeframe = st.selectbox(

            "Time Frame",

            list(TIMEFRAMES.keys()),

            key="commodity_tf"

        )

    column = COMMODITIES[commodity]

    df = get_data(

        column,

        TIMEFRAMES[timeframe]

    )

    if df is None or df.empty:

        st.warning("No Data Found")

        return

    st.metric(

        "Last Price",

        round(float(df["close"].iloc[-1]),2)

    )

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=df.index,

            y=df["close"],

            mode="lines",

            name=commodity,

            line=dict(width=2)

        )

    )

    fig.update_layout(

        template="plotly_dark",

        title=commodity,

        height=700,

        hovermode="x unified",

        xaxis_title="",

        yaxis_title="Price",

        margin=dict(

            l=20,

            r=20,

            t=60,

            b=20

        )

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )
# ==========================================
# Other Market
# ==========================================

USED_COLUMNS = set()

USED_COLUMNS.update(STOCKS.values())

USED_COLUMNS.update(FOREX.values())

USED_COLUMNS.update(CRYPTO.values())

USED_COLUMNS.update(COMMODITIES.values())

USED_COLUMNS.update(US_NOMINAL.values())

USED_COLUMNS.update(US_REAL.values())

for country in BONDS.values():

    USED_COLUMNS.update(country.values())


def other_market():

    st.title("📊 Other Indicators")

    df = load_database()

    other_columns = [

        c for c in df.columns

        if c not in USED_COLUMNS

    ]

    if len(other_columns) == 0:

        st.info("No Other Data")

        return

    col1, col2 = st.columns([2,1])

    with col1:

        indicator = st.selectbox(

            "Indicator",

            sorted(other_columns)

        )

    with col2:

        timeframe = st.selectbox(

            "Time Frame",

            list(TIMEFRAMES.keys()),

            key="other_tf"

        )

    data = get_data(

        indicator,

        TIMEFRAMES[timeframe]

    )

    if data is None or data.empty:

        st.warning("No Data Found")

        return

    st.metric(

        "Last Value",

        round(float(data["close"].iloc[-1]),4)

    )

    draw_chart(

        data,

        indicator

    )


# ==========================================
# Main Function
# ==========================================

def show():

    inject_global_style()

    market = st.sidebar.selectbox(

        "Market",

        [

            "📈 Stock Market",

            "📉 Bond Market",

            "💱 Forex",

            "🪙 Crypto",

            "🛢 Commodities",

            "📊 Other"

        ]

    )

    if market == "📈 Stock Market":

        stock_market()

    elif market == "📉 Bond Market":

        bond_market()

    elif market == "💱 Forex":

        forex_market()

    elif market == "🪙 Crypto":

        crypto_market()

    elif market == "🛢 Commodities":

        commodity_market()

    elif market == "📊 Other":

        other_market()