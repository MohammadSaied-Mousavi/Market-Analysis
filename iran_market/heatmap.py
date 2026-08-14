import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import finpy_tse as tse
from theme import inject_global_style
# ==========================================
# Industries
# ==========================================

INDUSTRIES = {

    "فلزات": [
        "فولاد",
        "فملی",
        "ذوب",
        "فخوز"
    ],

    "خودرو": [
        "خودرو",
        "خساپا",
        "خپارس"
    ],

    "بانک": [
        "وبملت",
        "وتجارت",
        "وبصادر"
    ],

    "پتروشیمی": [
        "فارس",
        "نوری",
        "پارس",
        "شپدیس"
    ],

    "دارویی": [
        "برکت",
        "دتماد",
        "دعبید"
    ]

}
# @st.cache_data(ttl=600)
def load_stock(symbol):

    try:

        df = tse.Get_Price_History(

            stock=symbol,

            start_date="1402-01-01",

            end_date="1404-12-29",

            ignore_date=False,

            adjust_price=True,

            show_weekday=False,

            double_date=True

        )

        if df is None:
            return None

        if df.empty:
            return None

        return df

    except:

        return None

def industry_returns():

    data = []

    for industry, symbols in INDUSTRIES.items():

        values = []

        for symbol in symbols:

            df = load_stock(symbol)

            if df is None:
                continue

            if len(df) < 2:
                continue

            r = (

                df["Close"].iloc[-1]

                /

                df["Close"].iloc[-2]

                - 1

            ) * 100

            values.append(r)

        if len(values):

            data.append({

                "Industry": industry,

                "Return": sum(values)/len(values)

            })

    return pd.DataFrame(data)

def show():
    inject_global_style()
    st.header("Heatmap صنایع")

    df = industry_returns()

    if df.empty:

        st.warning("داده‌ای وجود ندارد")

        return

    fig = go.Figure(

        go.Heatmap(

            z=[df["Return"]],

            x=df["Industry"],

            y=["Today"],

            text=np.round(df["Return"],2),

            texttemplate="%{text}%",

            colorscale="RdYlGn",

            zmid=0,

            colorbar=dict(

                title="Return %"

            )

        )

    )

    fig.update_layout(

        template="plotly_dark",

        height=250

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )