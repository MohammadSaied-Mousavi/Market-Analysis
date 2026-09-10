import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import uuid
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
# Combine Assets — A (op) B
# ==========================================

OPERATORS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "×": lambda a, b: a * b,
    "÷": lambda a, b: a / b.replace(0, np.nan),
}


def compute_combo_series(column_a, op_symbol, column_b, timeframe_code):
    """دو ستون رو روی تاریخ‌های مشترک هم‌تراز می‌کنه و عملگر انتخابی رو اعمال می‌کنه.
    اگه هم‌پوشانی تاریخی نباشه یا عملگر نامعتبر باشه، None برمی‌گردونه."""

    df_a = get_data(column_a, timeframe_code)
    df_b = get_data(column_b, timeframe_code)

    if df_a is None or df_a.empty or df_b is None or df_b.empty:
        return None

    if op_symbol not in OPERATORS:
        return None

    merged = df_a.join(df_b, how="inner", lsuffix="_a", rsuffix="_b")

    if merged.empty:
        return None

    result = OPERATORS[op_symbol](merged["close_a"], merged["close_b"])
    result = result.replace([np.inf, -np.inf], np.nan).dropna()

    if result.empty:
        return None

    return result.to_frame(name="close")


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

NAV_PAGES = MARKET_PAGES + ["🧮 Combine Assets"]


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
# Normalize (Rebase to 100) Controls
# ==========================================

def normalize_controls(page_key):
    """چک‌باکس نرمال‌سازی + انتخاب اسکیل نمودار نرمال‌شده (خط جداگانه از
    اسکیل چارت اصلی، چون این دو تا مفهوماً مستقلن)."""

    nc1, nc2 = st.columns([1.4, 2])

    with nc1:
        normalize = st.checkbox(
            "📊 Rebase to 100 (مقایسه‌ی درصدی)", key=f"{page_key}_normalize"
        )

    normalize_scale = "linear"

    if normalize:
        with nc2:
            normalize_scale = scale_selector(
                f"{page_key}_normalize_scale", label="Normalized Scale"
            )

    return normalize, normalize_scale


# ==========================================
# Lookback (Time Range) Selector
# ==========================================
#
# چرا این جدا از rangeselector داخلی Plotly پیاده‌سازی شده:
# دکمه‌های rangeselector توی Plotly فقط xaxis.range رو عوض می‌کنن،
# محور Y هیچ‌وقت خودکار بر اساس بازه‌ی دیده‌شده rescale نمی‌شه (محدودیت
# شناخته‌شده‌ی خود Plotly.js). چون Streamlit با هر تعامل کل اسکریپت رو
# دوباره اجرا می‌کنه، به‌جای دست‌کاری تنظیمات محور، داده رو *قبل* از
# ساخت فیگور به همون بازه فیلتر می‌کنیم؛ اون‌وقت auto-range پیش‌فرض
# Plotly خودش محور Y رو متناسب با داده‌ی واقعی نمایش‌داده‌شده تنظیم می‌کنه.
# ==========================================

LOOKBACK_OPTIONS = {
    "1M": pd.DateOffset(months=1),
    "6M": pd.DateOffset(months=6),
    "1Y": pd.DateOffset(years=1),
    "5Y": pd.DateOffset(years=5),
    "10Y": pd.DateOffset(years=10),
    "All": None,
}


def lookback_selector(page_key):
    options = list(LOOKBACK_OPTIONS.keys())

    selection = st.segmented_control(
        "Range",
        options,
        default="All",
        key=f"{page_key}_lookback",
        label_visibility="collapsed",
    )

    if selection is None:
        selection = "All"

    return LOOKBACK_OPTIONS[selection]


# ==========================================
# Overlay Manager — "Add Chart" UI + session state
# ==========================================

def overlay_manager(page_key, df, exclude_columns=None):
    """Renders the 'Add Chart' widget for a page and returns the current
    list of overlays. Each overlay is either:
      {"kind": "single", "column": ..., "label": ..., "scale": ...}
      {"kind": "combo", "column_a": ..., "op": ..., "column_b": ..., "label": ..., "scale": ...}
    Overlay state is kept per page_key so each page has its own independent set."""

    exclude_columns = exclude_columns or set()
    state_key = f"overlays_{page_key}"

    if state_key not in st.session_state:
        st.session_state[state_key] = []

    overlays = st.session_state[state_key]
    asset_universe = get_asset_universe(df)

    st.markdown("---")
    st.markdown("**➕ Add Chart**")

    add_kind = st.radio(
        "Type", ["Single Asset", "Combination (A op B)"],
        horizontal=True, key=f"{page_key}_add_kind",
    )

    # ----------------------------------------
    # حالت ۱: یه دارایی تکی
    # ----------------------------------------
    if add_kind == "Single Asset":
        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])

        with c1:
            add_market = st.selectbox("Market", MARKET_PAGES, key=f"{page_key}_add_market")

        with c2:
            options = list(asset_universe[add_market].keys())

            if options:
                add_label = st.selectbox("Asset", options, key=f"{page_key}_add_asset")
            else:
                st.selectbox("Asset", ["—"], key=f"{page_key}_add_asset", disabled=True)
                add_label = None

        with c3:
            add_scale_choice = st.selectbox("Scale", ["Linear", "Log"], key=f"{page_key}_add_scale")

        with c4:
            st.write("")
            st.write("")
            add_clicked = st.button("Add", key=f"{page_key}_add_btn", use_container_width=True)

        if add_clicked and add_label is not None:
            column = asset_universe[add_market][add_label]

            if column in exclude_columns:
                st.warning(f"{add_label} همون دارایی‌ایه که همین الان چارت اصلیه.")
            elif any(o["kind"] == "single" and o["column"] == column for o in overlays):
                st.warning(f"{add_label} از قبل به چارت اضافه شده.")
            else:
                overlays.append(
                    {
                        "id": uuid.uuid4().hex,
                        "kind": "single",
                        "label": add_label,
                        "column": column,
                        "scale": "log" if add_scale_choice == "Log" else "linear",
                    }
                )

    # ----------------------------------------
    # حالت ۲: ترکیب دو دارایی (A op B)
    # ----------------------------------------
    else:
        st.caption("دو تا دارایی و یه عملگر انتخاب کنید — یه سری جدید از ترکیبشون ساخته می‌شه.")

        ac1, ac2 = st.columns(2)

        with ac1:
            a_market = st.selectbox("Market (A)", MARKET_PAGES, key=f"{page_key}_combo_market_a")
            a_options = list(asset_universe[a_market].keys())
            a_label = (
                st.selectbox("Asset (A)", a_options, key=f"{page_key}_combo_asset_a")
                if a_options else None
            )

        with ac2:
            b_market = st.selectbox("Market (B)", MARKET_PAGES, key=f"{page_key}_combo_market_b")
            b_options = list(asset_universe[b_market].keys())
            b_label = (
                st.selectbox("Asset (B)", b_options, key=f"{page_key}_combo_asset_b")
                if b_options else None
            )

        oc1, oc2, oc3 = st.columns([1, 1, 1])

        with oc1:
            op_symbol = st.selectbox("Operator", list(OPERATORS.keys()), key=f"{page_key}_combo_op")

        with oc2:
            combo_scale_choice = st.selectbox("Scale", ["Linear", "Log"], key=f"{page_key}_combo_scale")

        with oc3:
            st.write("")
            st.write("")
            combo_add_clicked = st.button(
                "Add", key=f"{page_key}_combo_add_btn", use_container_width=True
            )

        if combo_add_clicked and a_label is not None and b_label is not None:
            column_a = asset_universe[a_market][a_label]
            column_b = asset_universe[b_market][b_label]

            if column_a == column_b:
                st.warning("دو دارایی انتخابی نباید یکی باشن.")
            else:
                combo_label = f"{a_label} {op_symbol} {b_label}"
                already = any(
                    o["kind"] == "combo"
                    and o["column_a"] == column_a
                    and o["column_b"] == column_b
                    and o["op"] == op_symbol
                    for o in overlays
                )

                if already:
                    st.warning("این ترکیب از قبل به چارت اضافه شده.")
                else:
                    overlays.append(
                        {
                            "id": uuid.uuid4().hex,
                            "kind": "combo",
                            "label": combo_label,
                            "column_a": column_a,
                            "label_a": a_label,
                            "op": op_symbol,
                            "column_b": column_b,
                            "label_b": b_label,
                            "scale": "log" if combo_scale_choice == "Log" else "linear",
                        }
                    )

    # ----------------------------------------
    # لیست چارت‌های اضافه‌شده
    # ----------------------------------------
    if overlays:
        st.caption("چارت‌های اضافه‌شده:")

        remove_index = None

        for i, ov in enumerate(overlays):
            rc1, rc2, rc3 = st.columns([3, 1.2, 0.8])

            with rc1:
                tag = "Σ" if ov["kind"] == "combo" else "•"
                st.write(f"{tag} {ov['label']}")

            with rc2:
                current = "Log" if ov["scale"] == "log" else "Linear"
                new_scale = st.selectbox(
                    "Scale",
                    ["Linear", "Log"],
                    index=0 if current == "Linear" else 1,
                    key=f"{page_key}_ov_scale_{ov['id']}",
                    label_visibility="collapsed",
                )
                ov["scale"] = "log" if new_scale == "Log" else "linear"

            with rc3:
                if st.button("✕", key=f"{page_key}_ov_remove_{ov['id']}"):
                    remove_index = i

        if remove_index is not None:
            overlays.pop(remove_index)
            st.rerun()

    return overlays


# ==========================================
# Figure Builder
# ==========================================

COLORWAY = [
    "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
    "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
]


def _bottom_legend(legend_title=None):
    """Legend رو به‌جای کنار چارت (که فضای افقی می‌گیره)، افقی و زیر
    محور X می‌ذاره — پس عرض بیشتری برای خود پلات می‌مونه."""

    config = dict(
        orientation="h",
        yanchor="top",
        y=-0.2,
        xanchor="center",
        x=0.5,
    )

    if legend_title:
        config["title"] = dict(text=legend_title, side="left")

    return config


def _rebase_series(series):
    """سری رو نسبت به اولین مقدارش (بعد از حذف NaN) به ۱۰۰ نرمال می‌کنه.
    اگه مقدار پایه صفر یا منفی باشه، خالی برمی‌گردونه (نرمال‌سازی معنا نداره)."""
    series = series.dropna()

    if series.empty:
        return series

    base_value = series.iloc[0]

    if pd.isna(base_value) or base_value <= 0:
        return series.iloc[0:0]

    return (series / base_value) * 100


def build_figure(
    title, base_traces, base_scale, base_yaxis_title,
    overlays, timeframe_code, legend_title=None,
    normalize=False, normalize_scale="linear",
    lookback_offset=None,
):
    fig = go.Figure()

    # داده‌ی overlayها رو یک‌بار حل می‌کنیم — هم برای حالت عادی هم normalize لازمه
    resolved_overlays = []
    for ov in overlays:
        if ov.get("kind") == "combo":
            ov_df = compute_combo_series(ov["column_a"], ov["op"], ov["column_b"], timeframe_code)
        else:
            ov_df = get_data(ov["column"], timeframe_code)

        if ov_df is None or ov_df.empty:
            st.warning(f"داده‌ای برای «{ov['label']}» پیدا نشد — از چارت حذف شد.")
            continue

        resolved_overlays.append((ov, ov_df))

    # ==================================================
    # محدود کردن داده به بازه‌ی زمانی انتخابی (Lookback)
    # این باید قبل از رسم انجام بشه تا auto-range خود Plotly
    # محور Y رو متناسب با همین داده‌ی محدودشده تنظیم کنه.
    # ==================================================
    anchor_dates = [t["df"].index.max() for t in base_traces if not t["df"].empty]
    anchor_dates += [ov_df.index.max() for _, ov_df in resolved_overlays if not ov_df.empty]
    anchor_date = max(anchor_dates) if anchor_dates else None

    cutoff_date = None
    if lookback_offset is not None and anchor_date is not None:
        cutoff_date = anchor_date - lookback_offset

    if cutoff_date is not None:
        base_traces = [
            {"name": t["name"], "df": t["df"][t["df"].index >= cutoff_date]}
            for t in base_traces
        ]
        resolved_overlays = [
            (ov, ov_df[ov_df.index >= cutoff_date])
            for ov, ov_df in resolved_overlays
        ]

    # ==================================================
    # حالت Rebase به ۱۰۰ — همه‌ی سری‌ها روی یه محور مشترک
    # ==================================================
    if normalize:
        all_series = [(t["name"], t["df"]["close"]) for t in base_traces]
        all_series += [(ov["label"], ov_df["close"]) for ov, ov_df in resolved_overlays]

        valid_starts = [s.dropna().index.min() for _, s in all_series if not s.dropna().empty]

        if not valid_starts:
            st.warning("داده‌ی کافی برای نرمال‌سازی نیست.")
            return

        # جدیدترین تاریخ شروع بین همه‌ی سری‌ها — تنها نقطه‌ای که همه ازش به بعد داده دارن
        common_start = max(valid_starts)
        color_idx = 0
        plotted_any = False

        for name, series in all_series:
            trimmed = series[series.index >= common_start]
            rebased = _rebase_series(trimmed)

            if rebased.empty:
                st.warning(f"«{name}» رو نشد نرمال کرد (مقدار پایه صفر/منفی یا داده‌ی کافی نبود).")
                continue

            color = COLORWAY[color_idx % len(COLORWAY)]
            color_idx += 1
            plotted_any = True

            fig.add_trace(
                go.Scatter(
                    x=rebased.index, y=rebased.values, mode="lines",
                    name=name, line=dict(width=2, color=color),
                )
            )

        if not plotted_any:
            st.warning("هیچ سری‌ای قابل نرمال‌سازی نبود.")
            return

        xaxis_config = dict(title="", domain=[0, 1])

        fig.update_layout(
            template="plotly_dark", title=f"{title} — Rebased to 100",
            height=720, hovermode="x unified",
            xaxis=xaxis_config,
            yaxis=dict(title="Rebased Value (Start = 100)", type=normalize_scale),
            legend=_bottom_legend(legend_title),
            margin=dict(l=20, r=20, t=60, b=80),
        )

        st.plotly_chart(fig, use_container_width=True)
        return

    # ==================================================
    # حالت عادی — هر overlay محور خودشو داره
    # ==================================================
    color_idx = 0

    for t in base_traces:
        color = COLORWAY[color_idx % len(COLORWAY)]
        color_idx += 1
        fig.add_trace(
            go.Scatter(
                x=t["df"].index, y=t["df"]["close"], mode="lines",
                name=t["name"], yaxis="y", line=dict(width=2, color=color),
            )
        )

    layout_axes = {"yaxis": dict(title=base_yaxis_title, type=base_scale, side="left")}

    n_extra = max(0, len(resolved_overlays) - 1)
    domain_right = max(0.55, 1 - 0.08 * n_extra)

    for i, (ov, ov_df) in enumerate(resolved_overlays):
        axis_num = i + 2
        axis_id = f"yaxis{axis_num}"
        yref = f"y{axis_num}"
        color = COLORWAY[color_idx % len(COLORWAY)]
        color_idx += 1

        fig.add_trace(
            go.Scatter(
                x=ov_df.index, y=ov_df["close"], mode="lines",
                name=ov["label"], yaxis=yref,
                line=dict(width=2, dash="dot", color=color),
            )
        )

        axis_config = dict(
            title=dict(text=ov["label"], font=dict(color=color)),
            tickfont=dict(color=color),
            type=ov["scale"], overlaying="y", side="right", showgrid=False,
        )
        if i > 0:
            axis_config["anchor"] = "free"
            axis_config["position"] = min(0.98, domain_right + 0.08 * i)

        layout_axes[axis_id] = axis_config

    xaxis_config = dict(title="", domain=[0, domain_right if resolved_overlays else 1])

    fig.update_layout(
        template="plotly_dark", title=title, height=720, hovermode="x unified",
        xaxis=xaxis_config,
        legend=_bottom_legend(legend_title),
        margin=dict(l=20, r=20 + 60 * n_extra, t=60, b=80),
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

    overlays = overlay_manager("stock", df, exclude_columns={column})
    normalize, normalize_scale = normalize_controls("stock")
    lookback = lookback_selector("stock")

    build_figure(
        title=index,
        base_traces=[{"name": index, "df": data}],
        base_scale=yaxis_type,
        base_yaxis_title="Price",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Series",
        normalize=normalize,
        normalize_scale=normalize_scale,
        lookback_offset=lookback,
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

    overlays = overlay_manager("bond", df, exclude_columns=set(selected.values()))
    normalize, normalize_scale = normalize_controls("bond")
    lookback = lookback_selector("bond")

    build_figure(
        title=country,
        base_traces=base_traces,
        base_scale=yaxis_type,
        base_yaxis_title="Yield (%)",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Maturity",
        normalize=normalize,
        normalize_scale=normalize_scale,
        lookback_offset=lookback,
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

    overlays = overlay_manager("forex", df, exclude_columns={column})
    normalize, normalize_scale = normalize_controls("forex")
    lookback = lookback_selector("forex")

    build_figure(
        title=pair,
        base_traces=[{"name": pair, "df": data}],
        base_scale=yaxis_type,
        base_yaxis_title="Exchange Rate",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Pair",
        normalize=normalize,
        normalize_scale=normalize_scale,
        lookback_offset=lookback,
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

    overlays = overlay_manager("crypto", df, exclude_columns={column})
    normalize, normalize_scale = normalize_controls("crypto")
    lookback = lookback_selector("crypto")

    build_figure(
        title=coin,
        base_traces=[{"name": coin, "df": data}],
        base_scale=yaxis_type,
        base_yaxis_title="Price",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Asset",
        normalize=normalize,
        normalize_scale=normalize_scale,
        lookback_offset=lookback,
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

    overlays = overlay_manager("commodity", df, exclude_columns={column})
    normalize, normalize_scale = normalize_controls("commodity")
    lookback = lookback_selector("commodity")

    build_figure(
        title=commodity,
        base_traces=[{"name": commodity, "df": data}],
        base_scale=yaxis_type,
        base_yaxis_title="Price",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Series",
        normalize=normalize,
        normalize_scale=normalize_scale,
        lookback_offset=lookback,
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

    overlays = overlay_manager("other", df, exclude_columns={indicator})
    normalize, normalize_scale = normalize_controls("other")
    lookback = lookback_selector("other")

    build_figure(
        title=indicator,
        base_traces=[{"name": indicator, "df": data}],
        base_scale=yaxis_type,
        base_yaxis_title="Value",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Series",
        normalize=normalize,
        normalize_scale=normalize_scale,
        lookback_offset=lookback,
    )


# ==========================================
# Combine Assets
# ==========================================

def combine_market():
    st.title("🧮 Combine Assets")
    df = load_database()
    asset_universe = get_asset_universe(df)

    st.caption(
        "دو دارایی رو با یه عملگر ریاضی (جمع، تفریق، ضرب، تقسیم) با هم ترکیب کنید تا "
        "یه سری جدید (مثل نسبت طلا/نقره یا اسپرد دو شاخص) بسازید."
    )

    ac1, ac2 = st.columns(2)

    with ac1:
        a_market = st.selectbox("Market (A)", MARKET_PAGES, key="combine_market_a")
        a_options = list(asset_universe[a_market].keys())
        a_label = (
            st.selectbox("Asset (A)", a_options, key="combine_asset_a")
            if a_options else None
        )

    with ac2:
        b_market = st.selectbox("Market (B)", MARKET_PAGES, key="combine_market_b")
        b_options = list(asset_universe[b_market].keys())
        b_label = (
            st.selectbox("Asset (B)", b_options, key="combine_asset_b")
            if b_options else None
        )

    oc1, oc2, oc3 = st.columns([1, 1, 1])

    with oc1:
        op_symbol = st.selectbox("Operator", list(OPERATORS.keys()), key="combine_op")

    with oc2:
        timeframe = st.selectbox("Time Frame", list(TIMEFRAMES.keys()), key="combine_tf")

    with oc3:
        yaxis_type = scale_selector("combine_scale")

    if a_label is None or b_label is None:
        st.warning("برای هر دو طرف، حداقل یه دارایی باید موجود باشه.")
        return

    column_a = asset_universe[a_market][a_label]
    column_b = asset_universe[b_market][b_label]

    if column_a == column_b:
        st.warning("دو دارایی انتخابی نباید یکی باشن.")
        return

    data = compute_combo_series(column_a, op_symbol, column_b, TIMEFRAMES[timeframe])

    if data is None or data.empty:
        st.error("داده‌ی هم‌پوشانی بین این دو دارایی برای محاسبه پیدا نشد.")
        return

    combo_label = f"{a_label} {op_symbol} {b_label}"

    st.metric("Last Value", round(float(data["close"].iloc[-1]), 4))

    overlays = overlay_manager("combine", df, exclude_columns={column_a, column_b})
    normalize, normalize_scale = normalize_controls("combine")
    lookback = lookback_selector("combine")

    build_figure(
        title=combo_label,
        base_traces=[{"name": combo_label, "df": data}],
        base_scale=yaxis_type,
        base_yaxis_title="Value",
        overlays=overlays,
        timeframe_code=TIMEFRAMES[timeframe],
        legend_title="Series",
        normalize=normalize,
        normalize_scale=normalize_scale,
        lookback_offset=lookback,
    )


# ==========================================
# Main Function
# ==========================================

def show():
    inject_global_style()

    market = st.sidebar.selectbox("Market", NAV_PAGES)

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
    elif market == "🧮 Combine Assets":
        combine_market()