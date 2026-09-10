import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from theme import inject_global_style

# ==========================================
# Database
# ==========================================

DATABASE_PATH = r"D:\project\database\macro_database.csv"


@st.cache_data
def load_database():
    df = pd.read_csv(DATABASE_PATH, parse_dates=["Date"])
    df.sort_values("Date", inplace=True)
    df.set_index("Date", inplace=True)
    return df


# ==========================================
# Time Frames
# ==========================================

TIMEFRAMES = {
    "1 Day": "D",
    "1 Week": "W",
    "1 Month": "M",
}


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
        return data.resample("W").last().dropna()
    elif timeframe == "M":
        return data.resample("ME").last().dropna()

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
    "CSI 300": "CSI300",
}

# ==========================================
# Forex Symbols
# ==========================================

FOREX = {
    "🇪🇺 EUR/USD": "EURUSD",
    "🇬🇧 GBP/USD": "GBPUSD",
    "🇯🇵 USD/JPY": "USDJPY",
    "🇨🇦 USD/CAD": "USDCAD",
    "🇦🇺 AUD/USD": "AUDUSD",
}

# ==========================================
# Crypto Symbols
# ==========================================

CRYPTO = {
    "₿ Bitcoin": "BTC",
    "Ξ Ethereum": "ETH",
    "ETH / BTC Ratio": "ETHBTC",
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
    "Iron Ore": "Iron Ore",
}

US_NOMINAL = {
    "3M": "3M",
    "2Y": "2Y",
    "5Y": "5Y",
    "10Y": "10Y",
    "30Y": "30Y",
}

US_REAL = {
    "5Y": "DFII5",
    "10Y": "DFII10",
}

BONDS = {
    "🇩🇪 Germany": {"2Y": "GER2Y", "10Y": "GER10Y"},
    "🇮🇹 Italy": {"2Y": "ITA2Y", "10Y": "ITA10Y"},
    "🇬🇧 United Kingdom": {"2Y": "UK2Y", "10Y": "UK10Y"},
    "🇨🇦 Canada": {"2Y": "CAN2Y", "10Y": "CAN10Y"},
    "🇯🇵 Japan": {"2Y": "JPN2Y", "10Y": "JPN10Y"},
    "🇦🇺 Australia": {"2Y": "AUS2Y", "10Y": "AUS10Y"},
}


def _build_bond_all():
    """Flattens the bond structure into a single {label: column} map
    so bonds can be picked in the two-step (market -> asset) overlay UI."""
    result = {}

    for maturity, col in US_NOMINAL.items():
        result[f"🇺🇸 US {maturity} (Nominal)"] = col

    for maturity, col in US_REAL.items():
        result[f"🇺🇸 US {maturity} (Real)"] = col

    for country, mats in BONDS.items():
        for maturity, col in mats.items():
            result[f"{country} {maturity}"] = col

    return result


BOND_ALL = _build_bond_all()

USED_COLUMNS = set()
USED_COLUMNS.update(STOCKS.values())
USED_COLUMNS.update(FOREX.values())
USED_COLUMNS.update(CRYPTO.values())
USED_COLUMNS.update(COMMODITIES.values())
USED_COLUMNS.update(US_NOMINAL.values())
USED_COLUMNS.update(US_REAL.values())
for _mats in BONDS.values():
    USED_COLUMNS.update(_mats.values())


MARKET_PAGES = [
    "📈 Stock Market",
    "📉 Bond Market",
    "💱 Forex",
    "🪙 Crypto",
    "🛢 Commodities",
    "📊 Other",
]


def get_asset_universe(df):
    """Market -> {label: column} map used by the 'Add Chart' overlay picker."""
    other_columns = sorted(c for c in df.columns if c not in USED_COLUMNS)

    return {
        "📈 Stock Market": STOCKS,
        "📉 Bond Market": BOND_ALL,
        "💱 Forex": FOREX,
        "🪙 Crypto": CRYPTO,
        "🛢 Commodities": COMMODITIES,
        "📊 Other": {c: c for c in other_columns},
    }


# ==========================================
# Scale Selector (Linear / Log)
# ==========================================

def scale_selector(key, label="Scale"):
    scale = st.radio(label, ["Linear", "Log"], horizontal=True, key=key)
    return "log" if scale == "Log" else "linear"


# ==========================================
# Overlay Manager — "Add Chart" UI + session state
# ==========================================

def overlay_manager(page_key, df):
    """Renders the 'Add Chart' widget for a page and returns the current
    list of overlays: [{"label", "column", "scale"}, ...].
    Overlay state is kept per page_key so each of the 6 market pages has
    its own independent set of added charts."""

    state_key = f"overlays_{page_key}"

    if state_key not in st.session_state:
        st.session_state[state_key] = []

    overlays = st.session_state[state_key]
    asset_universe = get_asset_universe(df)

    st.markdown("---")
    st.markdown("**➕ Add Chart**")

    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])

    with c1:
        add_market = st.selectbox(
            "Market", MARKET_PAGES, key=f"{page_key}_add_market"
        )

    with c2:
        options = list(asset_universe[add_market].keys())

        if options:
            add_label = st.selectbox("Asset", options, key=f"{page_key}_add_asset")
        else:
            st.selectbox("Asset", ["—"], key=f"{page_key}_add_asset", disabled=True)
            add_label = None

    with c3:
        add_scale_choice = st.selectbox(
            "Scale", ["Linear", "Log"], key=f"{page_key}_add_scale"
        )

    with c4:
        st.write("")
        st.write("")
        add_clicked = st.button(
            "Add", key=f"{page_key}_add_btn", use_container_width=True
        )

    if add_clicked and add_label is not None:
        column = asset_universe[add_market][add_label]
        already_added = any(o["column"] == column for o in overlays)

        if already_added:
            st.warning(f"{add_label} از قبل به چارت اضافه شده.")
        else:
            overlays.append(
                {
                    "label": add_label,
                    "column": column,
                    "scale": "log" if add_scale_choice == "Log" else "linear",
                }
            )

    if overlays:
        st.caption("چارت‌های اضافه‌شده:")

        remove_index = None

        for i, ov in enumerate(overlays):
            rc1, rc2, rc3 = st.columns([3, 1.2, 0.8])

            with rc1:
                st.write(f"• {ov['label']}")

            with rc2:
                current = "Log" if ov["scale"] == "log" else "Linear"
                new_scale = st.selectbox(
                    "Scale",
                    ["Linear", "Log"],
                    index=0 if current == "Linear" else 1,
                    key=f"{page_key}_ov_scale_{i}",
                    label_visibility="collapsed",
                )
                ov["scale"] = "log" if new_scale == "Log" else "linear"

            with rc3:
                if st.button("✕", key=f"{page_key}_ov_remove_{i}"):
                    remove_index = i

        if remove_index is not None:
            overlays.pop(remove_index)
            st.rerun()

    return overlays


# ==========================================
# Figure Builder
# Base traces share one y-axis/scale (exactly like the original page).
# Each overlay gets its own y-axis so its scale (log/linear) is fully
# independent from the base chart and from every other overlay.
# ==========================================

def build_figure(
    title,
    base_traces,
    base_scale,
    base_yaxis_title,
    overlays,
    timeframe_code,
    legend_title=None,
):
    fig = go.Figure()

    for t in base_traces:
        fig.add_trace(
            go.Scatter(
                x=t["df"].index,
                y=t["df"]["close"],
                mode="lines",
                name=t["name"],
                yaxis="y",
                line=dict(width=2),
            )
        )

    layout_axes = {
        "yaxis": dict(title=base_yaxis_title, type=base_scale, side="left")
    }

    resolved_overlays = []

    for ov in overlays:
        ov_df = get_data(ov["column"], timeframe_code)

        if ov_df is None or ov_df.empty:
            continue

        resolved_overlays.append((ov, ov_df))

    # Only the 2nd overlay onward needs a manually positioned "free" axis;
    # the 1st overlay can just sit on the standard right side.
    n_extra = max(0, len(resolved_overlays) - 1)
    domain_right = max(0.55, 1 - 0.08 * n_extra)

    for i, (ov, ov_df) in enumerate(resolved_overlays):
        axis_num = i + 2
        axis_id = f"yaxis{axis_num}"
        yref = f"y{axis_num}"

        fig.add_trace(
            go.Scatter(
                x=ov_df.index,
                y=ov_df["close"],
                mode="lines",
                name=ov["label"],
                yaxis=yref,
                line=dict(width=2, dash="dot"),
            )
        )

        axis_config = dict(
            title=ov["label"],
            type=ov["scale"],
            overlaying="y",
            side="right",
            showgrid=False,
        )

        if i > 0:
            axis_config["anchor"] = "free"
            axis_config["position"] = min(0.98, domain_right + 0.08 * i)

        layout_axes[axis_id] = axis_config

    fig.update_layout(
        template="plotly_dark",
        title=title,
        height=700,
        hovermode="x unified",
        xaxis=dict(title="", domain=[0, domain_right if resolved_overlays else 1]),
        legend_title=legend_title,
        margin=dict(l=20, r=20, t=60, b=60 if resolved_overlays else 20),
        **layout_axes,
    )

    st.plotly_chart(fig, use_container_width=True)


# ==========================================
# Stock Market
# ==========================================

def stock_market():
    st.title("📈 Stock Market")
    df = load_database()

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        index = st.selectbox("Index", list(STOCKS.keys()))

    with col2:
        timeframe = st.selectbox("Time Frame", list(TIMEFRAMES.keys()))

    with col3:
        yaxis_type = scale_selector("stock_scale")

    column = STOCKS[index]
    data = get_data(column, TIMEFRAMES[timeframe])

    if data is None or data.empty:
        st.error("No Data Found")
        return

    st.metric("Last Price", round(float(data["close"].iloc[-1]), 2))

    overlays = overlay_manager("stock", df)

    build_figure(
        title=index,
        base_traces=[{"name": index, "df": data}],
        base_scale=yaxis_type,
        base_yaxis_title="Price",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Series",
    )


# ==========================================
# Bond Market
# ==========================================

def bond_market():
    st.title("📉 Bond Market")
    df = load_database()

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        country = st.selectbox("Country", ["🇺🇸 United States"] + list(BONDS.keys()))

    with col2:
        timeframe = st.selectbox("Time Frame", list(TIMEFRAMES.keys()), key="bond_tf")

    with col3:
        yaxis_type = scale_selector("bond_scale")

    if country == "🇺🇸 United States":
        yield_type = st.selectbox(
            "Yield Type", ["Nominal Yield", "Real Yield"], key="yield_type"
        )
        selected = US_NOMINAL if yield_type == "Nominal Yield" else US_REAL
    else:
        selected = BONDS[country]

    base_traces = []

    for maturity, column in selected.items():
        data = get_data(column, TIMEFRAMES[timeframe])

        if data is None or data.empty:
            continue

        base_traces.append({"name": maturity, "df": data})

    if not base_traces:
        st.warning("No Data Found")
        return

    overlays = overlay_manager("bond", df)

    build_figure(
        title=country,
        base_traces=base_traces,
        base_scale=yaxis_type,
        base_yaxis_title="Yield (%)",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Maturity",
    )


# ==========================================
# Forex Market
# ==========================================

def forex_market():
    st.title("💱 Forex Market")
    df = load_database()

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        pair = st.selectbox("Currency Pair", list(FOREX.keys()))

    with col2:
        timeframe = st.selectbox("Time Frame", list(TIMEFRAMES.keys()), key="forex_tf")

    with col3:
        yaxis_type = scale_selector("forex_scale")

    column = FOREX[pair]
    data = get_data(column, TIMEFRAMES[timeframe])

    if data is None or data.empty:
        st.error("No Data Found")
        return

    st.metric("Last Price", round(float(data["close"].iloc[-1]), 5))

    overlays = overlay_manager("forex", df)

    build_figure(
        title=pair,
        base_traces=[{"name": pair, "df": data}],
        base_scale=yaxis_type,
        base_yaxis_title="Exchange Rate",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Pair",
    )


# ==========================================
# Crypto Market
# ==========================================

def crypto_market():
    st.title("🪙 Crypto Market")
    df = load_database()

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        coin = st.selectbox("Asset", list(CRYPTO.keys()))

    with col2:
        timeframe = st.selectbox("Time Frame", list(TIMEFRAMES.keys()), key="crypto_tf")

    with col3:
        yaxis_type = scale_selector("crypto_scale")

    column = CRYPTO[coin]
    data = get_data(column, TIMEFRAMES[timeframe])

    if data is None or data.empty:
        st.error("No Data Found")
        return

    st.metric("Last Price", round(float(data["close"].iloc[-1]), 4))

    overlays = overlay_manager("crypto", df)

    build_figure(
        title=coin,
        base_traces=[{"name": coin, "df": data}],
        base_scale=yaxis_type,
        base_yaxis_title="Price",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Asset",
    )


# ==========================================
# Commodity Market
# ==========================================

def commodity_market():
    st.title("🛢 Commodities")
    df = load_database()

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        commodity = st.selectbox("Commodity", list(COMMODITIES.keys()))

    with col2:
        timeframe = st.selectbox(
            "Time Frame", list(TIMEFRAMES.keys()), key="commodity_tf"
        )

    with col3:
        yaxis_type = scale_selector("commodity_scale")

    column = COMMODITIES[commodity]
    data = get_data(column, TIMEFRAMES[timeframe])

    if data is None or data.empty:
        st.warning("No Data Found")
        return

    st.metric("Last Price", round(float(data["close"].iloc[-1]), 2))

    overlays = overlay_manager("commodity", df)

    build_figure(
        title=commodity,
        base_traces=[{"name": commodity, "df": data}],
        base_scale=yaxis_type,
        base_yaxis_title="Price",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Series",
    )


# ==========================================
# Other Market
# ==========================================

def other_market():
    st.title("📊 Other Indicators")
    df = load_database()

    other_columns = [c for c in df.columns if c not in USED_COLUMNS]

    if len(other_columns) == 0:
        st.info("No Other Data")
        return

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        indicator = st.selectbox("Indicator", sorted(other_columns))

    with col2:
        timeframe = st.selectbox("Time Frame", list(TIMEFRAMES.keys()), key="other_tf")

    with col3:
        yaxis_type = scale_selector("other_scale")

    data = get_data(indicator, TIMEFRAMES[timeframe])

    if data is None or data.empty:
        st.warning("No Data Found")
        return

    st.metric("Last Value", round(float(data["close"].iloc[-1]), 4))

    overlays = overlay_manager("other", df)

    build_figure(
        title=indicator,
        base_traces=[{"name": indicator, "df": data}],
        base_scale=yaxis_type,
        base_yaxis_title="Value",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Series",
    )


# ==========================================
# Main Function
# ==========================================

def show():
    inject_global_style()

    market = st.sidebar.selectbox("Market", MARKET_PAGES)

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
