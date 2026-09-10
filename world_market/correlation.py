import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from theme import inject_global_style
from pathlib import Path

# ==========================================================
# Database Path (فقط خواندن — هیچ‌چیز اینجا نوشته نمی‌شود)
# ==========================================================
# ساختار واقعی پروژه:
#   D:\project\
#   ├── database\
#   │   └── macro_database.csv
#   └── world_market\
#       └── correlation.py

DATABASE_FILE = Path(__file__).parent.parent / "database" / "macro_database.csv"


# ==========================================================
# TimeFrames
# ==========================================================
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
# Lead / Lag Settings
# ==========================================================
LAG_RANGE = {
    "±5 Days": 5,
    "±10 Days": 10,
    "±20 Days": 20
}


# ==========================================================
# Assets -> ستون متناظر در macro_database.csv
# ==========================================================
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

    lag_range_name = st.sidebar.selectbox(
        "Lead / Lag Range",
        list(LAG_RANGE.keys()),
        index=1
    )

    start_date = st.sidebar.date_input(
        "Start Date",
        pd.Timestamp("2019-01-01")
    )

    return (
        TIMEFRAMES[timeframe_name],
        WINDOWS[window_name],
        LAG_RANGE[lag_range_name],
        start_date
    )


# ==========================================================
# Load Market Returns
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

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Latest",
        f"{rolling_corr.iloc[-1]:.2f}"
    )

    col2.metric(
        "Mean",
        f"{rolling_corr.mean():.2f}"
    )

    col3.metric(
        "Maximum",
        f"{rolling_corr.max():.2f}"
    )

    col4.metric(
        "Minimum",
        f"{rolling_corr.min():.2f}"
    )

    col5.metric(
        "Std",
        f"{rolling_corr.std():.2f}"
    )


# ==========================================================
# Scatter Plot + Regression
# ==========================================================
def scatter_correlation(
    returns,
    asset1,
    asset2,
    window
):

    st.subheader("Scatter / Regression")

    if asset1 == asset2:

        st.info("Please choose two different assets.")

        return

    pair = returns[[asset1, asset2]].dropna()

    if pair.empty:

        st.warning("No overlapping observations.")

        return

    # محدود کردن به آخرین Window
    pair = pair.tail(window)

    if len(pair) < 3:

        st.warning("Not enough observations for scatter analysis.")

        return

    x = pair[asset1]
    y = pair[asset2]

    correlation = x.corr(y)

    # Linear regression
    slope, intercept = np.polyfit(
        x,
        y,
        1
    )

    y_pred = slope * x + intercept

    # R²
    ss_res = np.sum(
        (y - y_pred) ** 2
    )

    ss_tot = np.sum(
        (y - y.mean()) ** 2
    )

    if ss_tot == 0:

        r_squared = np.nan

    else:

        r_squared = 1 - (
            ss_res / ss_tot
        )

    # Create regression line using sorted x
    x_line = np.linspace(
        x.min(),
        x.max(),
        100
    )

    y_line = (
        slope * x_line
        + intercept
    )

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=x,

            y=y,

            mode="markers",

            name="Observations",

            marker=dict(
                size=7,
                opacity=0.65
            ),

            customdata=pair.index,

            hovertemplate=
            "<b>Date</b>: %{customdata|%Y-%m-%d}<br>"
            f"<b>{asset1}</b>: %{{x:.4f}}<br>"
            f"<b>{asset2}</b>: %{{y:.4f}}"
            "<extra></extra>"

        )

    )

    fig.add_trace(

        go.Scatter(

            x=x_line,

            y=y_line,

            mode="lines",

            name="Regression Line",

            line=dict(
                color="#EF553B",
                width=2
            )

        )

    )

    fig.update_layout(

        template="plotly_dark",

        height=650,

        hovermode="closest",

        xaxis_title=f"{asset1} Return",

        yaxis_title=f"{asset2} Return",

        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Correlation",
        f"{correlation:.2f}"
    )

    col2.metric(
        "R²",
        f"{r_squared:.2f}"
        if pd.notna(r_squared)
        else "N/A"
    )

    col3.metric(
        "Observations",
        f"{len(pair):,}"
    )

    st.caption(
        f"Using the latest {window} observations with valid data."
    )


# ==========================================================
# Lead / Lag Correlation
# ==========================================================
def calculate_lag_correlations(
    series1,
    series2,
    max_lag
):

    results = []

    combined = pd.concat(
        [series1, series2],
        axis=1
    )

    combined.columns = [
        "asset1",
        "asset2"
    ]

    combined = combined.dropna()

    if combined.empty:

        return pd.DataFrame()

    for lag in range(
        -max_lag,
        max_lag + 1
    ):

        if lag > 0:

            # Asset 1 leads Asset 2
            x = combined["asset1"].iloc[:-lag]
            y = combined["asset2"].iloc[lag:]

        elif lag < 0:

            # Asset 2 leads Asset 1
            lag_abs = abs(lag)

            x = combined["asset1"].iloc[lag_abs:]
            y = combined["asset2"].iloc[:-lag_abs]

        else:

            # Same-day correlation
            x = combined["asset1"]
            y = combined["asset2"]

        valid = pd.concat(
            [x, y],
            axis=1
        ).dropna()

        if len(valid) < 3:

            correlation = np.nan
            observations = 0

        else:

            correlation = valid.iloc[:, 0].corr(
                valid.iloc[:, 1]
            )

            observations = len(valid)

        results.append(
            {
                "Lag": lag,
                "Correlation": correlation,
                "Observations": observations
            }
        )

    return pd.DataFrame(results)


# ==========================================================
# Lead / Lag Analysis
# ==========================================================
# ==========================================================
# Lead / Lag Analysis
# ==========================================================
def lead_lag_analysis(
    returns,
    asset1,
    asset2,
    window,
    max_lag
):

    st.subheader("Lead / Lag Correlation")

    if asset1 == asset2:

        st.info("Please choose two different assets.")

        return

    if asset1 not in returns.columns:
        return

    if asset2 not in returns.columns:
        return

    pair = returns[
        [asset1, asset2]
    ].dropna()

    # آخرین Window مشاهده
    pair = pair.tail(window)

    if len(pair) < 3:

        st.warning(
            "Not enough overlapping observations for lead / lag analysis."
        )

        return

    lag_df = calculate_lag_correlations(
        pair[asset1],
        pair[asset2],
        max_lag
    )

    if lag_df.empty:

        st.warning(
            "Could not calculate lead / lag correlations."
        )

        return

    lag_df = lag_df.dropna(
        subset=["Correlation"]
    )

    if lag_df.empty:

        st.warning(
            "Could not calculate valid correlations."
        )

        return

    # ======================================================
    # Find the strongest absolute correlation
    # ======================================================
    lag_df["AbsCorrelation"] = lag_df["Correlation"].abs()

    max_abs_corr = lag_df["AbsCorrelation"].max()

    # ======================================================
    # Tolerance برای جلوگیری از انتخاب تصادفی در
    # صورت برابر یا تقریباً برابر بودن
    # ======================================================
    tolerance = 1e-6

    best_candidates = lag_df[
        np.isclose(
            lag_df["AbsCorrelation"],
            max_abs_corr,
            atol=tolerance,
            rtol=tolerance
        )
    ].copy()

    # ======================================================
    # اگر چند Lag بهترین correlation مشابه داشتند،
    # اولویت با کمترین فاصله از صفر است.
    #
    # مثلاً اگر:
    # -8 = 0.54
    # +8 = 0.54
    #
    # هر دو نگه داشته می‌شوند.
    # ======================================================
    best_candidates["AbsLag"] = (
        best_candidates["Lag"].abs()
    )

    min_abs_lag = best_candidates["AbsLag"].min()

    best_candidates = best_candidates[
        best_candidates["AbsLag"] == min_abs_lag
    ].copy()

    # ======================================================
    # تعیین نتیجه
    # ======================================================
    candidate_lags = (
        best_candidates["Lag"]
        .astype(int)
        .tolist()
    )

    candidate_lags = sorted(candidate_lags)

    # ------------------------------------------------------
    # حالت 1: فقط یک Lag
    # ------------------------------------------------------
    if len(candidate_lags) == 1:

        best_lag = candidate_lags[0]

        best_row = best_candidates.iloc[0]

        best_corr = float(
            best_row["Correlation"]
        )

        observations = int(
            best_row["Observations"]
        )

        best_lag_text = f"{best_lag:+d} Days"

        # ----------------------------------------------
        # Determine direction
        # ----------------------------------------------
        if best_lag > 0:

            direction_text = (
                f"{asset1} leads {asset2} by "
                f"{best_lag} day(s)."
            )

        elif best_lag < 0:

            direction_text = (
                f"{asset2} leads {asset1} by "
                f"{abs(best_lag)} day(s)."
            )

        else:

            direction_text = (
                "No lead / lag detected. "
                "The strongest relationship occurs at lag 0."
            )

    # ------------------------------------------------------
    # حالت 2: چند Lag با بهترین correlation
    # ------------------------------------------------------
    else:

        # مثلاً [-8, +8]
        lag_values = candidate_lags

        # --------------------------------------------------
        # اگر دقیقاً دو طرف صفر وجود داشته باشند:
        # -8 و +8
        # --------------------------------------------------
        symmetric_pairs = []

        for lag in lag_values:

            if lag > 0 and -lag in lag_values:

                symmetric_pairs.append(lag)

        if len(symmetric_pairs) > 0:

            # در صورت چند جفت، نزدیک‌ترین جفت به صفر
            symmetric_lag = min(
                symmetric_pairs
            )

            best_lag_text = (
                f"±{symmetric_lag} Days"
            )

            # correlation مشترک / بهترین مقدار
            symmetric_rows = best_candidates[
                best_candidates["Lag"].isin(
                    [-symmetric_lag, symmetric_lag]
                )
            ]

            best_corr = float(
                symmetric_rows["Correlation"]
                .abs()
                .max()
            )

            observations = int(
                symmetric_rows["Observations"]
                .min()
            )

            direction_text = (
                "No clear leader. "
                f"Both +{symmetric_lag} and "
                f"-{symmetric_lag} days show "
                "an equally strong relationship."
            )

        else:

            # ------------------------------------------------
            # چند Lag مشابه ولی غیرمتقارن
            # در این حالت هنوز نمی‌توانیم یک Leader
            # قطعی اعلام کنیم.
            # ------------------------------------------------
            best_lag_text = (
                "Multiple Lags"
            )

            best_corr = float(
                best_candidates["Correlation"]
                .abs()
                .max()
            )

            observations = int(
                best_candidates["Observations"]
                .min()
            )

            direction_text = (
                "No clear leader. "
                "Multiple lags have essentially "
                "the same strongest correlation."
            )

    # ======================================================
    # Chart
    # ======================================================
    fig = go.Figure()

    fig.add_trace(

        go.Bar(

            x=lag_df["Lag"],

            y=lag_df["Correlation"],

            name="Correlation",

            hovertemplate=
            "Lag: %{x} Days<br>"
            "Correlation: %{y:.4f}"
            "<extra></extra>"

        )

    )

    fig.add_hline(

        y=0,

        line_dash="dash",

        line_color="gray"

    )

    fig.add_vline(

        x=0,

        line_dash="dot",

        line_color="gray"

    )

    # ======================================================
    # Highlight ALL best candidate lags
    # ======================================================
    for lag in candidate_lags:

        fig.add_vline(

            x=lag,

            line_dash="dash",

            line_color="#00CC96",

            line_width=2,

            annotation_text=(
                f"Best {lag:+d}"
            ),

            annotation_position="top"

        )

    fig.update_layout(

        template="plotly_dark",

        height=600,

        hovermode="x",

        xaxis=dict(

            title="Lag (Days)",

            dtick=1

        ),

        yaxis=dict(

            title="Correlation",

            range=[-1.05, 1.05]

        )

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ======================================================
    # Metrics
    # ======================================================
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Best Lag",
        best_lag_text
    )

    col2.metric(
        "Best Correlation",
        f"{best_corr:.2f}"
    )

    col3.metric(
        "Observations",
        f"{observations:,}"
    )

    # ======================================================
    # Interpretation
    # ======================================================
    st.info(
        direction_text
    )

    st.caption(
        f"Lead / Lag calculated using the latest "
        f"{window} observations."
    )

# ==========================================================
# Main
# ==========================================================
def show():

    inject_global_style()

    # ======================================================
    # Sidebar
    # ======================================================
    (
        resample_rule,
        window,
        max_lag,
        start_date
    ) = sidebar()

    # ======================================================
    # Load Database
    # ======================================================
    db = load_database()

    if db.empty:

        st.error(
            "macro_database.csv پیدا نشد یا خالی است. اول updater.py را اجرا کن."
        )

        st.write("مسیری که چک شد:")

        st.code(
            str(DATABASE_FILE)
        )

        st.write(
            "آیا این مسیر وجود دارد؟",
            DATABASE_FILE.exists()
        )

        st.write(
            "محل فعلی این فایل (correlation.py):"
        )

        st.code(
            str(Path(__file__).resolve())
        )

        return

    # ======================================================
    # Calculate Returns
    # ======================================================
    returns = load_market_returns(
        db,
        resample_rule
    )

    if returns.empty:

        st.error(
            "No market data available."
        )

        return

    # ======================================================
    # Start Date Filter
    # ======================================================
    returns = returns.loc[
        pd.Timestamp(start_date):
    ]

    # ======================================================
    # Prepare Returns
    # ======================================================
    returns = prepare_returns(
        returns
    )

    if returns.empty:

        st.error(
            "No market data available in the selected date range."
        )

        return

    if len(returns.columns) < 2:

        st.error(
            "Less than two assets were available."
        )

        st.write(
            "Available assets:"
        )

        st.write(
            returns.columns.tolist()
        )

        return

    # ======================================================
    # Correlation Matrix
    # ======================================================
    correlation_matrix(
        returns,
        window
    )

    # ======================================================
    # Asset Selection
    # ======================================================
    asset1, asset2 = asset_selector(
        returns
    )

    # ======================================================
    # Data Summary
    # ======================================================
    with st.expander(
        "Data Summary"
    ):

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

        st.write(
            "Available Assets"
        )

        st.write(
            list(returns.columns)
        )

    st.divider()

    # ======================================================
    # Historical Correlation
    # ======================================================
    historical_correlation(
        returns,
        asset1,
        asset2,
        window
    )

    st.divider()

    # ======================================================
    # Scatter + Regression
    # ======================================================
    scatter_correlation(
        returns,
        asset1,
        asset2,
        window
    )

    st.divider()

    # ======================================================
    # Lead / Lag Analysis
    # ======================================================
    lead_lag_analysis(
        returns,
        asset1,
        asset2,
        window,
        max_lag
    )


# ==========================================================
# Run
# ==========================================================
if __name__ == "__main__":
    show()