import streamlit as st
import finpy_tse as tse
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from theme import inject_global_style
# ==========================================
# Download Stock
# ==========================================

# @st.cache_data(ttl=600)
def load_stock(symbol):

    try:

        df = tse.Get_Price_History(

            stock=symbol,

            start_date="1397-01-01",

            end_date="1404-12-29",

            ignore_date=False,

            adjust_price=True,

            show_weekday=False,

            double_date=True

        )

        if df is None:
            return pd.DataFrame()

        if df.empty:
            return pd.DataFrame()

        # تاریخ میلادی
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")

        return df

    except Exception as e:

        st.error(e)

        return pd.DataFrame()

# ==========================================
# Symbol Selector
# ==========================================

def symbol_selector():

    symbol = st.text_input(

        "نماد",

        value="فولاد"

    )

    return symbol.strip()

# ==========================================
# Stock Summary
# ==========================================

def stock_summary(df):

    if df.empty:

        st.warning("داده‌ای یافت نشد")

        return

    last = df.iloc[-1]

    c1, c2, c3 = st.columns(3)

    c1.metric(

        "آخرین قیمت",

        f"{last['Close']:,.0f}"

    )

    c2.metric(

        "حجم",

        f"{last['Volume']:,.0f}"

    )

    c3.metric(

        "ارزش معاملات",

        f"{last['Value']:,.0f}"

    )

# ==========================================
# Price Chart
# ==========================================

def price_chart(df):

    fig = make_subplots(

        rows=2,
        cols=1,

        shared_xaxes=True,

        vertical_spacing=0.05,

        row_heights=[0.75,0.25]

    )

    fig.add_trace(

        go.Scatter(

            x=df.index,

            y=df["Close"],

            mode="lines",

            name="Close",

            line=dict(
                width=2,
                color="#00CC96"
            )

        ),

        row=1,
        col=1

    )

    fig.add_trace(

        go.Bar(

            x=df.index,

            y=df["Volume"],

            name="Volume"

        ),

        row=2,
        col=1

    )

    fig.update_layout(

        template="plotly_dark",

        height=650,

        showlegend=False

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )

# ==========================================
# Daily Return
# ==========================================

def daily_return(df):

    returns = df["Close"].pct_change()*100

    fig = go.Figure()

    fig.add_trace(

        go.Bar(

            x=returns.index,

            y=returns,

            name="Return"

        )

    )

    fig.update_layout(

        template="plotly_dark",

        height=300,

        title="Daily Return (%)"

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )

def show():
    inject_global_style()
    symbol = symbol_selector()

    df = load_stock(symbol)

    if df.empty:

        st.error("نماد پیدا نشد")

        return

    stock_summary(df)

    st.divider()

    price_chart(df)

    st.divider()

    daily_return(df)