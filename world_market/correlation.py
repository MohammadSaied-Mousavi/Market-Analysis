import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from theme import inject_global_style
from pathlib import Path

# ==========================================================
# Database Path (فقط خواندن — هیچ‌چیز اینجا نوشته نمی‌شود)
# ==========================================================
# ساختار واقعی پروژه (تأیید شده از خروجی دیباگ):
#   D:\project\
#   ├── database\
#   │   └── macro_database.csv
#   └── world_market\
#       └── correlation.py   <- این فایل، یک پوشه پایین‌تر از database\
#
# پس یک سطح بالا (.parent.parent) کافی است

DATABASE_FILE = Path(__file__).parent.parent / "database" / "macro_database.csv"

# ==========================================================
# TimeFrames
# ==========================================================
# چون دیتابیس همیشه روزانه‌ست، برای Week/Month باید resample کنیم
# (آخرین مقدار هر هفته/ماه گرفته می‌شود)

TIMEFRAMES = {
    "1 Day": None,
    "1 Week": "W",
    "1 Month": "ME"
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
# Assets -> ستون متناظر در macro_database.csv
# ==========================================================
# نکته: چون NASDAQ توی updater.py الان ^NDX (Nasdaq-100) است،
# اینجا هم به همون معنا نگاشت شده.

ASSETS = {

    "S&P500": "SP500",
    "Nasdaq100": "NASDAQ",
    "Dow Jones": "DOW",
    "Russell2000": "RUSSELL",

    "DAX": "DAX",
    "FTSE100": "FTSE100",
    "Nikkei225": "Nikkei225",

    "China A50": "China A50",

    "US10Y": "10Y",
    "US02Y": "2Y",
    "VIX": "VIX",
    "VVIX": "VVIX",
    "VXN": "VXN",
    "VXD": "VXD",

    "Gold": "GOLD",
    "Silver": "SILVER",
    "Copper": "XCUUSD",

    "WTI": "WTI",
    "Natural Gas": "Natural Gas",

    "Iron Ore": "Iron Ore",

    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",

    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH"

}


# ==========================================================
# Load Database
# ==========================================================

@st.cache_data(ttl=600)
def load_database():

    if not DATABASE_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(DATABASE_FILE)

    df["Date"] = pd.to_datetime(df["Date"])

    df = df.sort_values("Date")

    df = df.set_index("Date")

    return df


# ==========================================================
# Return Series
# ==========================================================

def calculate_returns(series, resample_rule):

    series = series.dropna()

    if resample_rule is not None:
        series = series.resample(resample_rule).last()

    r = series.pct_change()

    return r.dropna()


# ==========================================================
# Sidebar
# ==========================================================

def sidebar():

    st.sidebar.header("Settings")

    timeframe_name = st.sidebar.selectbox(
        "Time Frame",
        list(TIMEFRAMES.keys())
    )

    window_name = st.sidebar.selectbox(
        "Rolling Window",
        list(WINDOWS.keys()),
        index=3
    )

    start_date = st.sidebar.date_input(
        "Start Date",
        pd.Timestamp("2019-01-01")
    )

    return (
        TIMEFRAMES[timeframe_name],
        WINDOWS[window_name],
        start_date
    )


# ==========================================================
# Load Market Returns (از دیتابیس محلی)
# ==========================================================

def load_market_returns(db, resample_rule):

    returns = pd.DataFrame()

    failed = []

    for asset, column in ASSETS.items():

        if column not in db.columns:

            failed.append(asset)

            continue

        r = calculate_returns(
            db[column],
            resample_rule
        )

        if len(r) == 0:

            failed.append(asset)

            continue

        returns[asset] = r

    if len(failed):

        st.sidebar.warning(
            f"{len(failed)} assets not found / empty in database:\n"
            + ", ".join(failed)
        )

    return returns


# ==========================================================
# Prepare Data
# ==========================================================

def prepare_returns(returns):

    if returns.empty:

        return returns

    returns = returns.sort_index()

    # حذف ستون‌هایی که کاملاً خالی هستند
    returns = returns.dropna(
        axis=1,
        how="all"
    )

    # پر کردن گپ‌های کوچک
    returns = returns.ffill(limit=5)

    # حذف ستون‌هایی که کمتر از 70٪ داده دارند
    min_obs = int(len(returns) * 0.70)

    returns = returns.dropna(
        axis=1,
        thresh=min_obs
    )

    # حذف ردیف‌هایی که همه چیز NaN است
    returns = returns.dropna(
        how="all"
    )

    return returns


# ==========================================================
# Asset Selector
# ==========================================================

def asset_selector(returns):

    st.subheader("Assets")

    col1, col2 = st.columns(2)

    asset1 = col1.selectbox(

        "Asset 1",

        returns.columns,

        index=0,

        key="asset1"

    )

    default_index = 1 if len(returns.columns) > 1 else 0

    asset2 = col2.selectbox(

        "Asset 2",

        returns.columns,

        index=default_index,

        key="asset2"

    )

    return asset1, asset2


# ==========================================================
# Correlation Matrix
# ==========================================================

def correlation_matrix(returns, window):

    st.subheader("Correlation Matrix")

    if len(returns.columns) < 2:
        st.warning("Need at least two assets.")
        return

    corr = returns.tail(window).corr()

    fig = go.Figure(

        go.Heatmap(

            z=corr.values,

            x=corr.columns,

            y=corr.columns,

            zmin=-1,
            zmax=1,

            colorscale="RdYlGn",

            text=np.round(corr.values, 2),

            texttemplate="%{text}",

            textfont=dict(
                color="white",
                size=11
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


# ==========================================================
# Historical Correlation
# ==========================================================

def historical_correlation(
    returns,
    asset1,
    asset2,
    window
):

    st.subheader("Historical Correlation")

    if asset1 == asset2:

        st.info("Please choose two different assets.")

        return

    if asset1 not in returns.columns:
        return

    if asset2 not in returns.columns:
        return

    rolling_corr = (

        returns[asset1]

        .rolling(window)

        .corr(

            returns[asset2]

        )

    )

    rolling_corr = rolling_corr.dropna()

    if rolling_corr.empty:

        st.warning("Not enough observations.")

        return

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

        yaxis=dict(

            range=[-1.05, 1.05]

        ),

        xaxis_title="",

        yaxis_title="Correlation"

    )

    st.markdown(

        f"### {asset1} ↔ {asset2}"

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )

    col1, col2, col3 = st.columns(3)

    col1.metric(

        "Latest",

        f"{rolling_corr.iloc[-1]:.2f}"

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

def show():
    inject_global_style()
    # Sidebar
    resample_rule, window, start_date = sidebar()

    # بارگذاری دیتابیس (فقط خواندن)
    db = load_database()

    if db.empty:
        st.error(
            "macro_database.csv پیدا نشد یا خالی است. اول updater.py را اجرا کن."
        )
        st.write("مسیری که چک شد:")
        st.code(str(DATABASE_FILE))
        st.write("آیا این مسیر وجود دارد؟", DATABASE_FILE.exists())
        st.write("محل فعلی این فایل (correlation.py):")
        st.code(str(Path(__file__).resolve()))
        return

    # محاسبه‌ی بازده‌ها از روی دیتابیس
    returns = load_market_returns(db, resample_rule)

    if returns.empty:

        st.error("No market data available.")

        return

    # ابتدا برش بر اساس Start Date (مهم: قبل از فیلتر پوشش ۷۰٪!)
    # چون اگر اول prepare_returns اجرا شود، دارایی‌هایی که تاریخچه‌
    # کوتاه‌تری دارند (مثلاً VVIX از ۲۰۱۳) نسبت به کل تاریخچه‌ی
    # طولانی S&P500 (از ۱۹۲۷) "ناقص" به‌حساب می‌آیند و حذف می‌شوند،
    # حتی اگر در همان بازه‌ی انتخابی کاربر کاملاً کامل باشند.
    returns = returns.loc[pd.Timestamp(start_date):]

    # حالا فیلتر پوشش ۷۰٪ را روی همان بازه‌ی انتخابی اعمال کن
    returns = prepare_returns(returns)

    if returns.empty:

        st.error("No market data available in the selected date range.")

        return

    if len(returns.columns) < 2:

        st.error("Less than two assets were available.")

        st.write("Available assets:")
        st.write(returns.columns.tolist())

        return

    # Heatmap
    correlation_matrix(
        returns,
        window
    )

    # Asset selection
    asset1, asset2 = asset_selector(returns)

    # Optional Debug
    with st.expander("Data Summary"):

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Assets",
            len(returns.columns)
        )

        col2.metric(
            "Observations",
            len(returns)
        )

        col3.metric(
            "Window",
            window
        )

        st.write("Available Assets")
        st.write(list(returns.columns))

    st.divider()

    # Historical Correlation
    historical_correlation(
        returns,
        asset1,
        asset2,
        window
    )


if __name__ == "__main__":
    show()