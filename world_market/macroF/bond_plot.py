import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# =====================================================
# Database
# =====================================================

DATABASE = (
    Path(__file__).parents[2]
    / "database"
    / "macro_database.csv"
)

# =====================================================
# Load Database
# =====================================================

def load_curve():

    df = pd.read_csv(DATABASE)

    numeric_cols = [
        "3M",
        "2Y",
        "5Y",
        "10Y",
        "30Y",
        "2s10s",
        "BullSteepener",
        "BearSteepener",
        "SteepenerTwist",
        "BullFlattener",
        "BearFlattener",
        "FlattenerTwist",
    ]

    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


    df["Date"] = pd.to_datetime(df["Date"])

    df = df.sort_values("Date").reset_index(drop=True)

    return df


# =====================================================
# Fixed Yield Scale
# =====================================================

def get_y_scale(df):

    values = (
        df.tail(30)[
            ["3M", "2Y", "5Y", "10Y", "30Y"]
        ]
        .to_numpy()
        .flatten()
    )

    values = values[~pd.isna(values)]

    padding = 0.20

    return (
        float(values.min() - padding),
        float(values.max() + padding)
    )


# =====================================================
# Color Map
# =====================================================

REGIME_COLORS = {

    "BullSteepener": "#66BB6A",

    "BearSteepener": "#C62828",

    "SteepenerTwist": "#F9A825",

    "BullFlattener": "#64B5F6",

    "BearFlattener": "#AB47BC",

    "FlattenerTwist": "#FFFFFF"

}
# =====================================================
# Yield Curve Figure
# =====================================================

def build_curve(
    df,
    lookback,
    y_range
):

    row = df.iloc[lookback]

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=[
                "3M",
                "2Y",
                "5Y",
                "10Y",
                "30Y"
            ],

            y=[
                row["3M"],
                row["2Y"],
                row["5Y"],
                row["10Y"],
                row["30Y"]
            ],

            mode="lines+markers",

            line=dict(
                width=4,
                color="#ff8c32"
            ),

            marker=dict(
                size=10
            ),

            hovertemplate=
            "<b>%{x}</b><br>"
            "Yield : %{y:.2f}%"
            "<extra></extra>"

        )

    )

    fig.update_layout(

        template="plotly_dark",

        height=420,

        margin=dict(
            l=5,
            r=5,
            t=5,
            b=5
        ),

        showlegend=False,

        xaxis=dict(
            title="",
            fixedrange=True
        ),

        yaxis=dict(
            title="Yield (%)",
            fixedrange=True,
            autorange=False,
            range=list(y_range)
        )

    )

    return fig

# =====================================================
# Dynamic Regime Calculation
# =====================================================

def calculate_curve_regime_short(
    df,
    lookback
):

    df = df.copy()

    df = df.tail(252).reset_index(drop=True)

    df["Spread"] = df["10Y"] - df["2Y"]

    df["Spread_prev"] = df["Spread"].shift(lookback)

    df["2Y_prev"] = df["2Y"].shift(lookback)

    df["10Y_prev"] = df["10Y"].shift(lookback)

    df["Regime"] = ""

    # --------------------------------------------------

    mask = (
        (df["Spread"] > df["Spread_prev"]) &
        (df["2Y"] < df["2Y_prev"]) &
        (df["10Y"] < df["10Y_prev"])
    )

    df.loc[mask, "Regime"] = "BullSteepener"

    # --------------------------------------------------

    mask = (
        (df["Spread"] > df["Spread_prev"]) &
        (df["2Y"] > df["2Y_prev"]) &
        (df["10Y"] > df["10Y_prev"])
    )

    df.loc[mask, "Regime"] = "BearSteepener"

    # --------------------------------------------------

    mask = (
        (df["Spread"] > df["Spread_prev"]) &
        (df["2Y"] < df["2Y_prev"]) &
        (df["10Y"] > df["10Y_prev"])
    )

    df.loc[mask, "Regime"] = "SteepenerTwist"

    # --------------------------------------------------

    mask = (
        (df["Spread"] < df["Spread_prev"]) &
        (df["2Y"] < df["2Y_prev"]) &
        (df["10Y"] < df["10Y_prev"])
    )

    df.loc[mask, "Regime"] = "BullFlattener"

    # --------------------------------------------------

    mask = (
        (df["Spread"] < df["Spread_prev"]) &
        (df["2Y"] > df["2Y_prev"]) &
        (df["10Y"] > df["10Y_prev"])
    )

    df.loc[mask, "Regime"] = "BearFlattener"

    # --------------------------------------------------

    mask = (
        (df["Spread"] < df["Spread_prev"]) &
        (df["2Y"] > df["2Y_prev"]) &
        (df["10Y"] < df["10Y_prev"])
    )

    df.loc[mask, "Regime"] = "FlattenerTwist"

    # اگر رژیمی تشخیص داده نشد، آخرین رژیم معتبر را نگه دار
    df["Regime"] = df["Regime"].replace("", pd.NA)

    df["Regime"] = df["Regime"].ffill()

    df["Color"] = df["Regime"].map(REGIME_COLORS)

    df["Color"] = df["Color"].fillna("rgba(0,0,0,0)")

    return df

# =====================================================
# Short-Term Regime Chart
# =====================================================

def build_curve_regime_chart_dynamic(
    df,
    lookback
):

    regime_df = calculate_curve_regime_short(
        df,
        lookback
    )

    fig = go.Figure()

    # --------------------------------------------------
    # Regime Bars
    # --------------------------------------------------

    fig.add_trace(

        go.Bar(

            x=regime_df["Date"],

            y=regime_df["Spread"],

            marker_color=regime_df["Color"],

            width=24 * 3600 * 1000,

            opacity=0.90,

            hovertemplate=
            "<b>%{x}</b><br>"
            "2s10s = %{y:.2f}%"
            "<extra></extra>",

            showlegend=False

        )

    )

    # --------------------------------------------------
    # Spread Line
    # --------------------------------------------------

    fig.add_trace(

        go.Scatter(

            x=regime_df["Date"],

            y=regime_df["Spread"],

            mode="lines",

            line=dict(

                color="#ff8c32",

                width=3

            ),

            hovertemplate=
            "<b>%{x}</b><br>"
            "Spread = %{y:.2f}%"
            "<extra></extra>",

            showlegend=False

        )

    )

    # --------------------------------------------------

    fig.update_layout(

        template="plotly_dark",

        height=430,

        margin=dict(
            l=5,
            r=5,
            t=10,
            b=5
        ),

        bargap=0,

        xaxis=dict(
            title="",
            fixedrange=True
        ),

        yaxis=dict(

            title="10Y - 2Y (%)",

            fixedrange=True,

            zeroline=True,

            zerolinewidth=2,

            zerolinecolor="white"

        )

    )

    current_regime = regime_df.iloc[-1]["Regime"]

    return fig, current_regime

# =====================================================
# Long-Term Structural Regime Chart
# =====================================================

def build_curve_regime_chart(df):

    regime = pd.Series("", index=df.index)

    regime[df["BullSteepener"] == df["2s10s"]] = "BullSteepener"
    regime[df["BearSteepener"] == df["2s10s"]] = "BearSteepener"
    regime[df["SteepenerTwist"] == df["2s10s"]] = "SteepenerTwist"
    regime[df["BullFlattener"] == df["2s10s"]] = "BullFlattener"
    regime[df["BearFlattener"] == df["2s10s"]] = "BearFlattener"
    regime[df["FlattenerTwist"] == df["2s10s"]] = "FlattenerTwist"

    colors = regime.map(REGIME_COLORS)

    colors = colors.fillna("rgba(0,0,0,0)")

    fig = go.Figure()

    # --------------------------------------------------

    fig.add_trace(

        go.Bar(

            x=df["Date"],

            y=df["2s10s"],

            marker_color=colors,

            width=24 * 3600 * 1000,

            opacity=0.90,

            hovertemplate=
            "<b>%{x}</b><br>"
            "2s10s = %{y:.2f}%"
            "<extra></extra>",

            showlegend=False

        )

    )

    # --------------------------------------------------

    fig.add_trace(

        go.Scatter(

            x=df["Date"],

            y=df["2s10s"],

            mode="lines",

            line=dict(

                color="#ff8c32",

                width=3

            ),

            hovertemplate=
            "<b>%{x}</b><br>"
            "Spread = %{y:.2f}%"
            "<extra></extra>",

            showlegend=False

        )

    )

    # --------------------------------------------------

    fig.update_layout(

        template="plotly_dark",

        height=450,

        margin=dict(
            l=5,
            r=5,
            t=10,
            b=5
        ),

        bargap=0,

        xaxis=dict(

            title="",

            fixedrange=False,

            rangeslider=dict(
                visible=True
            ),

            rangeselector=dict(

                buttons=[

                    dict(
                        count=1,
                        label="1Y",
                        step="year",
                        stepmode="backward"
                    ),

                    dict(
                        count=5,
                        label="5Y",
                        step="year",
                        stepmode="backward"
                    ),

                    dict(
                        count=10,
                        label="10Y",
                        step="year",
                        stepmode="backward"
                    ),

                    dict(
                        count=20,
                        label="20Y",
                        step="year",
                        stepmode="backward"
                    ),

                    dict(
                        step="all",
                        label="All"
                    )

                ]

            )

        ),

        yaxis=dict(

            title="10Y - 2Y (%)",

            fixedrange=False,

            zeroline=True,

            zerolinewidth=2,

            zerolinecolor="white"

        )

    )
    fig.update_xaxes(
        range=[
            pd.Timestamp("1980-01-01"),
            df["Date"].max()
        ]
    )
    return fig