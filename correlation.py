import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from streamlit_plotly_events import plotly_events

from tvDatafeed import TvDatafeed, Interval

# ==========================================================
# TradingView Login
# ==========================================================

tv = TvDatafeed(
    username="saeedm21021377",
    password="S@eid210277!"
)

# ==========================================================
# TimeFrames
# ==========================================================

TIMEFRAMES = {
    "1 Day": Interval.in_daily,
    "1 Week": Interval.in_weekly,
    "1 Month": Interval.in_monthly
}

# ==========================================================
# Rolling Windows
# ==========================================================

WINDOWS = {
    "20 Days": 20,
    "60 Days": 60,
    "120 Days": 120,
    "250 Days": 250,
    "500 Days": 500
}

# ==========================================================
# Assets
# ==========================================================

ASSETS = {

    "S&P500": ("SPX500", "forexcom"),
    "Nasdaq100": ("nas100", "forexcom"),
    "Dow Jones": ("us30", "forexcom"),
    "Russell2000": ("us2000", "forexcom"),

    "DAX": ("ger40", "forexcom"),
    "FTSE100": ("uk100", "forexcom"),
    "Nikkei225": ("JP225", "forexcom"),

    "China A50": ("CHINA50", "forexcom"),

    "US10Y": ("US10Y", "TVC"),

    "Gold": ("XAUUSD", "forexcom"),
    "Silver": ("XAGUSD", "forexcom"),
    "Copper": ("COPPER", "forexcom"),

    "WTI": ("USOIL", "forexcom"),
    "Natural Gas": ("NATURALGAS", "forexcom"),

    "Iron Ore": ("FEF1!", "SGX"),

    "EURUSD": ("EURUSD", "forexcom"),
    "GBPUSD": ("GBPUSD", "forexcom"),
    "USDJPY": ("USDJPY", "forexcom"),
    "AUDUSD": ("AUDUSD", "forexcom"),
    "USDCAD": ("USDCAD", "forexcom"),

    "BTCUSDT": ("BTCUSDT", "BINANCE"),
    "ETHUSDT": ("ETHUSDT", "BINANCE")

}

# ==========================================================
# Download Market Data
# ==========================================================

# @st.cache_data(ttl=600)
def download_market(symbol, exchange, interval, window):

    try:

        df = tv.get_hist(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            n_bars=window
        )

        st.write(symbol, exchange, interval, df.shape, df.empty, df is None)
        st.write(df.head(5))

        if df is None:
            return None

        if df.empty:
            return None

        df = df.copy()

        df.index = pd.to_datetime(df.index)

        return df

    except Exception:

        return None

# ==========================================================
# Return Series
# ==========================================================

def calculate_returns(df):

    returns = df["close"].pct_change()

    returns.index = pd.to_datetime(
        returns.index
    ).normalize()

    returns.name = "return"

    return returns.dropna()

# ==========================================================
# Load All Markets
# ==========================================================

# @st.cache_data(ttl=600)
def load_market_returns(interval, window):

    series = []

    progress = st.progress(0)

    total = len(ASSETS)

    for i, (asset, info) in enumerate(ASSETS.items()):
        symbol, exchange = info
        df = download_market(
            symbol,
            exchange,
            interval,
            window
        )

        if df is None:
            progress.progress((i + 1) / total)
            continue

        r = calculate_returns(df)

        if r.empty:
            progress.progress((i + 1) / total)
            continue

        r.name = asset

        series.append(r)

        progress.progress((i + 1) / total)


    progress.empty()

    if len(series) == 0:

        return pd.DataFrame()

    returns = pd.concat(
        series,
        axis=1,
        join="outer"
    )

    return returns

# ==========================================================
# Clean Returns
# ==========================================================

def prepare_returns(data: pd.DataFrame):

    if data.empty:
        return data

    # مرتب سازی زمانی
    data = data.sort_index()

    # حذف ستون هایی که کاملاً خالی هستند
    data = data.dropna(axis=1, how="all")

    # حذف ستون هایی که کمتر از 70 درصد داده دارند
    min_obs = int(len(data) * 0.70)

    data = data.dropna(
        axis=1,
        thresh=min_obs
    )

    # پر کردن گپ های کوچک
    data = data.ffill(limit=5)

    # فقط ردیف هایی که حداقل دو دارایی دارند
    data = data.dropna(
        axis=0,
        thresh=2
    )

    return data

# ==========================================================
# Sidebar
# ==========================================================

def sidebar():

    st.sidebar.title("Settings")

    timeframe = st.sidebar.selectbox(
        "Time Frame",
        list(TIMEFRAMES.keys())
    )

    window_name = st.sidebar.selectbox(
        "Rolling Window",
        list(WINDOWS.keys()),
        index=3
    )

    return (
        TIMEFRAMES[timeframe],
        WINDOWS[window_name]
    )

# ==========================================================
# Default Selected Assets
# ==========================================================

def initialize_selected_assets(returns):

    if len(returns.columns) < 2:
        return

    if "asset1" not in st.session_state:

        st.session_state.asset1 = returns.columns[0]

    if "asset2" not in st.session_state:

        st.session_state.asset2 = returns.columns[1]
# ==========================================================
# Correlation Matrix
# ==========================================================

def correlation_matrix(returns, window):

    st.title("Correlation Matrix")

    if len(returns.columns) < 2:
        st.warning("Need at least two assets.")
        return

    corr = returns.tail(window).corr()

    fig = go.Figure(

        data=go.Heatmap(

            z=corr.values,

            x=corr.columns,

            y=corr.columns,

            zmin=-1,
            zmax=1,

            colorscale=[
                [0.00, "#7f0000"],
                [0.15, "#d73027"],
                [0.30, "#fc8d59"],
                [0.45, "#fee08b"],
                [0.50, "#2b2b2b"],
                [0.55, "#d9ef8b"],
                [0.70, "#91cf60"],
                [0.85, "#1a9850"],
                [1.00, "#006837"]
            ],

            text=np.round(corr.values, 2),

            texttemplate="%{text}",

            textfont=dict(
                size=11,
                color="white"
            ),

            hovertemplate=
            "<b>%{y}</b><br>"
            "vs<br>"
            "<b>%{x}</b><br><br>"
            "Correlation : %{z:.2f}"
            "<extra></extra>",

            colorbar=dict(
                title="Correlation"
            )

        )

    )

    fig.update_layout(

        template="plotly_dark",

        height=850,

        margin=dict(
            l=20,
            r=20,
            t=40,
            b=20
        ),

        xaxis=dict(
            tickangle=-45
        )

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    if selected:

        point = selected[0]

        st.session_state.asset1 = point["y"]

        st.session_state.asset2 = point["x"]

    st.caption(f"Rolling Window : {window}")


# ==========================================================
# Historical Correlation
# ==========================================================

def historical_correlation(returns, window):

    st.title("Historical Correlation")

    if len(returns.columns) < 2:
        return

    asset1 = st.session_state.get(
        "asset1",
        returns.columns[0]
    )

    asset2 = st.session_state.get(
        "asset2",
        returns.columns[1]
    )

    # اگر به هر دلیلی ستون حذف شده باشد
    if asset1 not in returns.columns:
        asset1 = returns.columns[0]

    if asset2 not in returns.columns:
        asset2 = returns.columns[1]

    st.markdown(f"### {asset1} ↔ {asset2}")

    rolling_corr = (
        returns[asset1]
        .rolling(window)
        .corr(returns[asset2])
    )

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=rolling_corr.index,

            y=rolling_corr,

            mode="lines",

            name="Rolling Correlation",

            line=dict(
                color="#00CC96",
                width=2
            )

        )

    )

    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="gray"
    )

    fig.add_hline(
        y=1,
        line_dash="dot",
        line_color="green"
    )

    fig.add_hline(
        y=-1,
        line_dash="dot",
        line_color="red"
    )

    fig.update_layout(

        template="plotly_dark",

        height=650,

        hovermode="x unified",

        xaxis_title="",

        yaxis_title="Correlation",

        yaxis=dict(
            range=[-1.05, 1.05]
        )

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    if rolling_corr.dropna().empty:
        return

    latest = rolling_corr.dropna().iloc[-1]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Latest",
        f"{latest:.2f}"
    )

    col2.metric(
        "Maximum",
        f"{rolling_corr.max():.2f}"
    )

    col3.metric(
        "Minimum",
        f"{rolling_corr.min():.2f}"
    )


# ==========================================================
# Main
# ==========================================================

# def show():
#
#     interval, window = sidebar()
#
#     returns = load_market_returns(interval)
#
#     returns = prepare_returns(returns)
#
#     st.write("Shape:", returns.shape)
#     st.write("Columns:", returns.columns.tolist())
#
#     if returns.empty:
#
#         st.error("No market data available.")
#
#         return
#
#     initialize_selected_assets(returns)
#
#     correlation_matrix(
#         returns,
#         window
#     )
#
#     st.divider()
#
#     historical_correlation(
#         returns,
#         window
#     )


# ==========================================================
# Main
# ==========================================================

def show():

    # تنظیمات سایدبار
    interval, window = sidebar()

    # دانلود داده‌ها
    returns = load_market_returns(interval, window)
    st.write("ADDWD AWD AWDW D", returns.head())
    # تمیز کردن داده‌ها
    returns = prepare_returns(returns)

    # اگر داده‌ای وجود نداشت
    if returns.empty:
        st.error("No market data available.")
        return

    # انتخاب پیش‌فرض دو دارایی
    initialize_selected_assets(returns)

    # فقط برای تست (بعداً حذف می‌کنیم)
    st.write("Shape:", returns.shape)
    st.write(returns.head())

    # نمایش Heatmap
    correlation_matrix(returns, window)

    st.divider()

    # نمایش Rolling Correlation
    historical_correlation(returns, window)