import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from plotly.subplots import make_subplots
import numpy as np
import os
import streamlit as st
from theme import ACCENT

# =====================================================
# Database
# =====================================================

DATABASE = (
    Path(__file__).parents[2]
    / "database"
    / "macro_database.csv"
)

# =====================================================
# Regime Shape Legend (Illustrative — نه دیتای واقعی)
# =====================================================

_REGIME_SHAPE_DEF = {
    # (دلتای سر کوتاه، دلتای سر بلند) — فقط علامت و بزرگی نسبی مهمه
    "BullFlattener":  (-0.3, -1.0),
    "BearFlattener":  (+1.0, +0.3),
    "BullSteepener":  (-1.0, -0.3),
    "BearSteepener":  (+0.3, +1.0),
    "SteepenerTwist": (-0.8, +0.8),
    "FlattenerTwist": (+0.8, -0.8),
}

_BASE_CURVE_X = ["3M", "2Y", "5Y", "10Y", "30Y"]
_BASE_CURVE_Y = [1.0, 1.6, 2.3, 2.8, 3.1]  # فقط برای شکل، نه دیتای واقعی


def build_regime_legend_figure():

    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=list(_REGIME_SHAPE_DEF.keys()),
    )
    for ann, regime in zip(fig.layout.annotations, _REGIME_SHAPE_DEF.keys()):
        ann.font = dict(color=REGIME_COLORS.get(regime, "white"), size=14)

    for i, regime in enumerate(_REGIME_SHAPE_DEF.keys()):
        idx = i + 1
        xref = "x domain" if idx == 1 else f"x{idx} domain"
        yref = "y domain" if idx == 1 else f"y{idx} domain"
        fig.add_shape(
            type="rect", xref=xref, yref=yref,
            x0=0, x1=1, y0=0, y1=1,
            fillcolor=REGIME_COLORS.get(regime, "white"),
            opacity=0.06, line_width=0, layer="below",
        )

    positions = [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)]

    for i, ((regime, (short_d, long_d)), (r, c)) in enumerate(
        zip(_REGIME_SHAPE_DEF.items(), positions)
    ):
        idx = i + 1
        xref = "x" if idx == 1 else f"x{idx}"
        yref = "y" if idx == 1 else f"y{idx}"

        y_before = _BASE_CURVE_Y
        y_after = [
            y_before[0] + short_d,
            y_before[1] + short_d * 0.6,
            y_before[2] + (short_d + long_d) / 2,
            y_before[3] + long_d * 0.6,
            y_before[4] + long_d,
        ]

        fig.add_trace(
            go.Scatter(x=_BASE_CURVE_X, y=y_before, mode="lines",
                       line=dict(color="#7fa8c9", width=2), showlegend=False),
            row=r, col=c,
        )
        fig.add_trace(
            go.Scatter(x=_BASE_CURVE_X, y=y_after, mode="lines",
                       line=dict(color=ACCENT, width=2, dash="dash"), showlegend=False),
            row=r, col=c,
        )

        short_color = "#d9534f" if short_d > 0 else "#4caf50"
        long_color = "#d9534f" if long_d > 0 else "#4caf50"

        fig.add_annotation(
            x=_BASE_CURVE_X[0], y=y_after[0], ax=_BASE_CURVE_X[0], ay=y_before[0],
            xref=xref, yref=yref, axref=xref, ayref=yref,
            showarrow=True, arrowcolor=short_color, arrowwidth=2, arrowhead=3,
        )
        fig.add_annotation(
            x=_BASE_CURVE_X[-1], y=y_after[-1], ax=_BASE_CURVE_X[-1], ay=y_before[-1],
            xref=xref, yref=yref, axref=xref, ayref=yref,
            showarrow=True, arrowcolor=long_color, arrowwidth=2, arrowhead=3,
        )

    fig.update_layout(
        template="plotly_dark", height=520, showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True, showticklabels=False)

    return fig


GROWTH_ASSET_PROXIES = {
    "RUSSELL": "سهام چرخه‌ای (Russell 2000)",
    "NASDAQ": "سهام رشدی (Nasdaq 100)",
    "GOLD": "طلا",
    "WTI": "کامودیتی (نفت WTI)",
    "XCUUSD": "مس (Copper)",
    "DXY": "دلار (DXY)",
}

REGIME_ORDER = [
    "BullFlattener", "BearFlattener",
    "BullSteepener", "BearSteepener",
    "SteepenerTwist", "FlattenerTwist",
]

def load_regime_growth_data():
    return _load_regime_growth_data_cached(str(DATABASE), os.path.getmtime(DATABASE))


@st.cache_data(show_spinner=False)
def _load_regime_growth_data_cached(path, mtime):
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    needed = (
        ["2s10s"] + list(REGIME_COLORS.keys())
        + ["A191RO1Q156NBEA", "CFNAI", "CFNAIMA3"]
        + list(GROWTH_ASSET_PROXIES.keys())
    )
    for c in needed:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _tag_regime(df):
    regime = pd.Series(pd.NA, index=df.index, dtype="object")
    for name in REGIME_ORDER:
        if name in df.columns:
            regime[df[name] == df["2s10s"]] = name
    return regime.ffill()


def _tag_growth_gdp(df):
    gdp = df.set_index("Date")["A191RO1Q156NBEA"].dropna()
    gdp_by_quarter = gdp.groupby(gdp.index.to_period("Q")).last()
    daily_quarter = df["Date"].dt.to_period("Q")
    growth_val = daily_quarter.map(gdp_by_quarter)
    return np.where(growth_val >= 0, "Growth Up", "Growth Down")


GROWTH_METHODS = {
    "cfnai_level": "سطح CFNAI-MA3 (≥ ۰ نسبت به روند بلندمدت)",
    "cfnai_momentum": "شتاب رشد (CFNAI ماهانه > CFNAI-MA3)",
}

def _tag_growth_cfnai_level(df):
    cfnai_ma3 = df.set_index("Date")["CFNAIMA3"].ffill()
    tag = pd.Series(pd.NA, index=cfnai_ma3.index, dtype="object")
    tag[cfnai_ma3 >= 0] = "Growth Up"
    tag[cfnai_ma3 < 0] = "Growth Down"
    return tag.to_numpy()
def _tag_growth_cfnai_momentum(df):
    d = df.set_index("Date")
    cfnai = d["CFNAI"].ffill()
    cfnai_ma3 = d["CFNAIMA3"].ffill()
    valid = cfnai.notna() & cfnai_ma3.notna()

    tag = pd.Series(pd.NA, index=d.index, dtype="object")
    tag[valid & (cfnai > cfnai_ma3)] = "Growth Up"
    tag[valid & (cfnai <= cfnai_ma3)] = "Growth Down"
    return tag.to_numpy()


_GROWTH_TAGGERS = {
    "cfnai_level": _tag_growth_cfnai_level,
    "cfnai_momentum": _tag_growth_cfnai_momentum,
}

def build_regime_growth_asset_table(df, forward_days=20, method="cfnai_level"):
    work = df.copy()
    work["Regime"] = _tag_regime(work)
    work["Growth"] = _GROWTH_TAGGERS[method](work)

    for col in GROWTH_ASSET_PROXIES:
        if col in work.columns:
            work[f"{col}_fwd"] = work[col].shift(-forward_days) / work[col] - 1

    rows = []
    for growth_dir in ["Growth Up", "Growth Down"]:
        for regime in REGIME_ORDER:
            mask = (work["Growth"] == growth_dir) & (work["Regime"] == regime)
            row = {"Growth": growth_dir, "Regime": regime, "N (روز)": int(mask.sum())}
            for col, label in GROWTH_ASSET_PROXIES.items():
                fwd_col = f"{col}_fwd"
                if fwd_col in work.columns:
                    row[label] = work.loc[mask, fwd_col].mean() * 100
            rows.append(row)

    return pd.DataFrame(rows).set_index(["Growth", "Regime"])

EXPECTED_RESULTS = {
    "Growth Up": {
        "Bull Flattening": {"Cyclical Stocks": "+",  "Growth Stocks": "++", "Gold": "++", "Commodities": "",   "USD": "-"},
        "Bull Steepening": {"Cyclical Stocks": "++", "Growth Stocks": "+",  "Gold": "+",  "Commodities": "",   "USD": "--"},
        "Bear Flattening": {"Cyclical Stocks": "+",  "Growth Stocks": "",   "Gold": "",   "Commodities": "+",  "USD": ""},
        "Bear Steepening": {"Cyclical Stocks": "++", "Growth Stocks": "",   "Gold": "--", "Commodities": "++", "USD": "+"},
    },
    "Growth Down": {
        "Bull Flattening": {"Cyclical Stocks": "-",  "Growth Stocks": "",   "Gold": "+",  "Commodities": "--", "USD": "-"},
        "Bull Steepening": {"Cyclical Stocks": "--", "Growth Stocks": "",   "Gold": "",   "Commodities": "-",  "USD": ""},
        "Bear Flattening": {"Cyclical Stocks": "-",  "Growth Stocks": "-",  "Gold": "",   "Commodities": "",   "USD": "+"},
        "Bear Steepening": {"Cyclical Stocks": "--", "Growth Stocks": "--", "Gold": "--", "Commodities": "",   "USD": "++"},
    },
}

_SIGN_BG = {
    "++": "#a5d6a5",
    "+":  "#d9ecd9",
    "":   "#eef1f6",
    "-":  "#f6d9d9",
    "--": "#e6a5a5",
}


def _render_expected_block(title, header_color, data, columns):
    cols_html = "".join(
        f"<th style='background:{header_color};color:white;padding:8px 12px;border:1px solid #ccc;'>{c}</th>"
        for c in columns
    )
    rows_html = ""
    for regime, values in data.items():
        cells = "".join(
            f"<td style='background:{_SIGN_BG.get(values.get(c, ''), '#eef1f6')};"
            f"text-align:center;padding:8px 12px;border:1px solid #ccc;color:#222;font-weight:600;'>"
            f"{values.get(c, '')}</td>"
            for c in columns
        )
        rows_html += (
            f"<tr><td style='background:#dbe4f0;font-weight:700;padding:8px 12px;"
            f"border:1px solid #ccc;color:#222;text-decoration:underline;'>{regime}</td>{cells}</tr>"
        )

    return f"""
    <table style="border-collapse:collapse;width:100%;margin-bottom:18px;font-family:inherit;">
      <tr>
        <th style="background:{header_color};color:white;padding:8px 12px;border:1px solid #ccc;">{title}</th>
        {cols_html}
      </tr>
      {rows_html}
    </table>
    """


def render_expected_results_html():
    columns = ["Cyclical Stocks", "Growth Stocks", "Gold", "Commodities", "USD"]
    html = _render_expected_block("Growth Up", "#5a9c5a", EXPECTED_RESULTS["Growth Up"], columns)
    html += _render_expected_block("Growth Down", "#c0504d", EXPECTED_RESULTS["Growth Down"], columns)
    return html

@st.cache_data(show_spinner=False)
def build_regime_growth_asset_table_forward(df, forward_days=20, method="cfnai_level"):
    work = df.copy()
    work["Regime"] = _tag_regime(work)
    work["Growth"] = _GROWTH_TAGGERS[method](work)

    for col in GROWTH_ASSET_PROXIES:
        if col in work.columns:
            work[f"{col}_fwd"] = work[col].shift(-forward_days) / work[col] - 1

    rows = []
    for growth_dir in ["Growth Up", "Growth Down"]:
        for regime in REGIME_ORDER:
            mask = (work["Growth"] == growth_dir) & (work["Regime"] == regime)
            row = {"Growth": growth_dir, "Regime": regime, "N (روز)": int(mask.sum())}
            for col, label in GROWTH_ASSET_PROXIES.items():
                fwd_col = f"{col}_fwd"
                if fwd_col in work.columns:
                    row[label] = work.loc[mask, fwd_col].mean() * 100
            rows.append(row)

    return pd.DataFrame(rows).set_index(["Growth", "Regime"])

@st.cache_data(show_spinner=False)
def _build_episode_frame(df, method="cfnai_level"):
    """کمکی مشترک: هر ردیف رو به یه اپیزودِ پیوسته‌ی (Regime, Growth) نگاشت می‌کنه.
    هم جدول Per-Episode هم وضعیت «رژیم فعلی» از همین استفاده می‌کنن."""
    work = df.copy()
    for col in ("CFNAI", "CFNAIMA3"):
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    work["Regime"] = _tag_regime(work)
    work["Growth"] = _GROWTH_TAGGERS[method](work)

    valid = work["Regime"].notna() & work["Growth"].notna()
    work = work.loc[valid].reset_index(drop=True)

    changed = (
        (work["Regime"] != work["Regime"].shift())
        | (work["Growth"] != work["Growth"].shift())
    )
    work["Episode"] = changed.cumsum()
    return work


def _build_episode_frame(df, method="cfnai_level"):
    """کمکی مشترک: هر ردیف رو به یه اپیزودِ پیوسته‌ی (Regime, Growth) نگاشت می‌کنه.
    هم جدول Per-Episode هم وضعیت «رژیم فعلی» از همین استفاده می‌کنن."""
    work = df.copy()
    for col in ("CFNAI", "CFNAIMA3"):
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    work["Regime"] = _tag_regime(work)
    work["Growth"] = _GROWTH_TAGGERS[method](work)

    valid = work["Regime"].notna() & work["Growth"].notna()
    work = work.loc[valid].reset_index(drop=True)

    changed = (
        (work["Regime"] != work["Regime"].shift())
        | (work["Growth"] != work["Growth"].shift())
    )
    work["Episode"] = changed.cumsum()
    return work


@st.cache_data(show_spinner=False)
def build_regime_growth_asset_table_episode(df, method="cfnai_level"):
    work = _build_episode_frame(df, method)

    episode_rows = []
    for ep_id, ep in work.groupby("Episode"):
        row = {
            "Growth": ep["Growth"].iloc[0],
            "Regime": ep["Regime"].iloc[0],
            "Length": len(ep),
        }
        for col, label in GROWTH_ASSET_PROXIES.items():
            if col not in ep.columns:
                continue
            series = ep[col].dropna()
            row[label] = (series.iloc[-1] / series.iloc[0] - 1) if len(series) >= 2 else np.nan
        episode_rows.append(row)

    episodes_df = pd.DataFrame(episode_rows)
    asset_labels = list(GROWTH_ASSET_PROXIES.values())

    summary = episodes_df.groupby(["Growth", "Regime"]).agg(
        **{"N (اپیزود)": ("Length", "count"), "میانگین طول (روز)": ("Length", "mean")},
        **{label: (label, "mean") for label in asset_labels},
    )

    summary = summary.reindex(
        pd.MultiIndex.from_product(
            [["Growth Up", "Growth Down"], REGIME_ORDER], names=["Growth", "Regime"]
        )
    )

    for label in asset_labels:
        summary[label] = summary[label] * 100

    return summary


@st.cache_data(show_spinner=False)
def build_regime_transition_matrix(df):
    work = df.copy()
    work["Regime"] = _tag_regime(work)
    work = work.dropna(subset=["Regime"]).reset_index(drop=True)

    changed = work["Regime"] != work["Regime"].shift()
    work["Episode"] = changed.cumsum()
    episode_regimes = work.groupby("Episode")["Regime"].first().tolist()

    counts = pd.DataFrame(0, index=REGIME_ORDER, columns=REGIME_ORDER, dtype=int)
    for frm, to in zip(episode_regimes[:-1], episode_regimes[1:]):
        if frm in counts.index and to in counts.columns:
            counts.loc[frm, to] += 1

    row_sums = counts.sum(axis=1)
    prob = counts.div(row_sums.replace(0, np.nan), axis=0) * 100
    return counts, prob


def build_transition_matrix_figure(counts, prob):
    text = [
        [
            f"{prob.loc[r, c]:.0f}%<br>({int(counts.loc[r, c])})" if pd.notna(prob.loc[r, c]) else "—"
            for c in REGIME_ORDER
        ]
        for r in REGIME_ORDER
    ]

    fig = go.Figure(data=go.Heatmap(
        z=prob.reindex(index=REGIME_ORDER, columns=REGIME_ORDER).values,
        x=REGIME_ORDER,
        y=REGIME_ORDER,
        colorscale="YlOrRd",
        text=text,
        texttemplate="%{text}",
        textfont={"size": 11},
        hovertemplate="از %{y} به %{x}<br>احتمال: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="%"),
    ))

    fig.update_layout(
        template="plotly_dark",
        height=480,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(title="رژیم بعدی", side="top"),
        yaxis=dict(title="رژیم فعلی", autorange="reversed"),
    )
    return fig

@st.cache_data(show_spinner=False)
def get_current_episode_performance(df, method="cfnai_level"):
    work = _build_episode_frame(df, method)
    if work.empty:
        return None

    last_episode_id = work["Episode"].iloc[-1]
    current_ep = work[work["Episode"] == last_episode_id]
    growth = current_ep["Growth"].iloc[0]
    regime = current_ep["Regime"].iloc[0]

    current_returns = {}
    for col, label in GROWTH_ASSET_PROXIES.items():
        if col not in current_ep.columns:
            continue
        series = current_ep[col].dropna()
        current_returns[label] = (
            (series.iloc[-1] / series.iloc[0] - 1) * 100 if len(series) >= 2 else np.nan
        )

    past = work[work["Episode"] != last_episode_id]
    hist_rows = []
    for ep_id, ep in past.groupby("Episode"):
        if ep["Growth"].iloc[0] != growth or ep["Regime"].iloc[0] != regime:
            continue
        row = {}
        for col, label in GROWTH_ASSET_PROXIES.items():
            if col not in ep.columns:
                continue
            series = ep[col].dropna()
            row[label] = (series.iloc[-1] / series.iloc[0] - 1) * 100 if len(series) >= 2 else np.nan
        hist_rows.append(row)

    hist_df = pd.DataFrame(hist_rows)
    hist_avg = hist_df.mean().to_dict() if not hist_df.empty else {}

    return {
        "Growth": growth,
        "Regime": regime,
        "Current Length": len(current_ep),
        "Since": current_ep["Date"].iloc[0],
        "N Past Episodes": len(hist_rows),
        "current": current_returns,
        "historical_avg": hist_avg,
    }


def _val_bg(v):
    if pd.isna(v):
        return "#333", "#888"
    return ("#a5d6a5", "#222") if v >= 0 else ("#e6a5a5", "#222")


def render_current_episode_vs_history_html(perf):
    asset_labels = list(GROWTH_ASSET_PROXIES.values())
    col_headers = "".join(
        f"<th style='background:#345f7a;color:white;padding:8px 12px;border:1px solid #ccc;'>{a}</th>"
        for a in asset_labels
    )

    def build_row(label, values_dict):
        cells = ""
        for a in asset_labels:
            v = values_dict.get(a, np.nan)
            bg, color = _val_bg(v)
            text = "—" if pd.isna(v) else f"{v:+.1f}%"
            cells += (
                f"<td style='background:{bg};text-align:center;padding:8px 12px;"
                f"border:1px solid #ccc;color:{color};font-weight:600;'>{text}</td>"
            )
        return (
            f"<tr><td style='background:#dbe4f0;font-weight:700;padding:8px 12px;"
            f"border:1px solid #ccc;color:#222;'>{label}</td>{cells}</tr>"
        )

    rows_html = build_row(f"این اپیزود (تاکنون، {perf['Current Length']} روز)", perf["current"])
    rows_html += build_row(f"میانگین {perf['N Past Episodes']} اپیزود قبلی", perf["historical_avg"])

    return f"""
    <table style="border-collapse:collapse;width:100%;margin-bottom:10px;font-family:inherit;">
      <tr>
        <th style="background:#345f7a;color:white;padding:8px 12px;border:1px solid #ccc;">دارایی</th>
        {col_headers}
      </tr>
      {rows_html}
    </table>
    """



def get_current_regime_growth_status(df, method="cfnai_level"):
    work = _build_episode_frame(df, method)
    if work.empty:
        return None

    last_episode_id = work["Episode"].iloc[-1]
    current_episode = work[work["Episode"] == last_episode_id]

    return {
        "Regime": current_episode["Regime"].iloc[0],
        "Growth": current_episode["Growth"].iloc[0],
        "Current Length": len(current_episode),
        "Since": current_episode["Date"].iloc[0],
    }


ASSET_TO_EXPECTED_CATEGORY = {
    "RUSSELL": "Cyclical Stocks",
    "NASDAQ": "Growth Stocks",
    "GOLD": "Gold",
    "WTI": "Commodities",
    "XCUUSD": "Commodities",
    "DXY": "USD",
}

REGIME_TO_EXPECTED_NAME = {
    "BullFlattener": "Bull Flattening",
    "BearFlattener": "Bear Flattening",
    "BullSteepener": "Bull Steepening",
    "BearSteepener": "Bear Steepening",
    # SteepenerTwist / FlattenerTwist عمداً نیستن — تئوری براشون تعریف نشده
}


def _expected_sign_for(growth, regime, asset_key):
    expected_regime = REGIME_TO_EXPECTED_NAME.get(regime)
    category = ASSET_TO_EXPECTED_CATEGORY.get(asset_key)
    if expected_regime is None or category is None:
        return None
    return EXPECTED_RESULTS.get(growth, {}).get(expected_regime, {}).get(category, "")


_INT_META_COLS = {"N (روز)", "N (اپیزود)"}
_FLOAT_META_COLS = {"میانگین طول (روز)"}


_MATCH_BG = {
    True: "#a5d6a5",
    False: "#e6a5a5",
    None: "#eef1f6",
}


def _match_result(value, expected_sign):
    if pd.isna(value):
        return None, "—"
    if expected_sign in ("+", "++"):
        match = value > 0
    elif expected_sign in ("-", "--"):
        match = value < 0
    else:
        match = None
    return match, f"{value:+.1f}%"


def _render_growth_block_html(title, header_color, table, growth_dir, meta_cols, asset_labels, asset_key_by_label):
    meta_headers = "".join(
        f"<th style='background:{header_color};color:white;padding:8px 12px;border:1px solid #ccc;'>{m}</th>"
        for m in meta_cols
    )
    asset_headers = "".join(
        f"<th style='background:{header_color};color:white;padding:8px 12px;border:1px solid #ccc;'>{a}</th>"
        for a in asset_labels
    )

    rows_html = ""
    for regime in REGIME_ORDER:
        if (growth_dir, regime) not in table.index:
            continue
        row = table.loc[(growth_dir, regime)]

        meta_cells = ""
        for m in meta_cols:
            v = row[m]
            if pd.isna(v):
                text = ""
            elif m in _INT_META_COLS:
                text = f"{int(v)}"
            else:
                text = f"{v:.1f}"
            meta_cells += (
                f"<td style='background:#dbe4f0;text-align:center;padding:8px 12px;"
                f"border:1px solid #ccc;color:#222;'>{text}</td>"
            )

        asset_cells = ""
        for label in asset_labels:
            value = row[label]
            asset_key = asset_key_by_label.get(label)
            expected_sign = _expected_sign_for(growth_dir, regime, asset_key)
            match, text = _match_result(value, expected_sign)
            bg = "#333" if pd.isna(value) else _MATCH_BG[match]
            color = "#888" if pd.isna(value) else "#222"
            asset_cells += (
                f"<td style='background:{bg};text-align:center;padding:8px 12px;"
                f"border:1px solid #ccc;color:{color};font-weight:600;'>{text}</td>"
            )

        rows_html += (
            f"<tr><td style='background:#dbe4f0;font-weight:700;padding:8px 12px;"
            f"border:1px solid #ccc;color:#222;text-decoration:underline;'>{regime}</td>"
            f"{meta_cells}{asset_cells}</tr>"
        )

    return f"""
    <table style="border-collapse:collapse;width:100%;margin-bottom:18px;font-family:inherit;">
      <tr>
        <th style="background:{header_color};color:white;padding:8px 12px;border:1px solid #ccc;">{title}</th>
        {meta_headers}{asset_headers}
      </tr>
      {rows_html}
    </table>
    """


def build_match_annotated_html(table, asset_labels):
    asset_key_by_label = {v: k for k, v in GROWTH_ASSET_PROXIES.items()}
    meta_cols = [c for c in table.columns if c not in asset_labels]

    html = _render_growth_block_html("Growth Up", "#5a9c5a", table, "Growth Up", meta_cols, asset_labels, asset_key_by_label)
    html += _render_growth_block_html("Growth Down", "#c0504d", table, "Growth Down", meta_cols, asset_labels, asset_key_by_label)
    return html


# =====================================================
# Load Database
# =====================================================

def load_curve():
    return _load_curve_cached(str(DATABASE), os.path.getmtime(DATABASE))


@st.cache_data(show_spinner=False)
def _load_curve_cached(path, mtime):
    df = pd.read_csv(path)
    numeric_cols = [
        "3M", "2Y", "5Y", "10Y", "30Y", "2s10s",
        "BullSteepener", "BearSteepener", "SteepenerTwist",
        "BullFlattener", "BearFlattener", "FlattenerTwist",
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
                color=ACCENT
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
                color=ACCENT,
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

    cfnai_ma3 = pd.to_numeric(df.get("CFNAIMA3"), errors="coerce").ffill()
    growth_label = pd.Series(
        np.where(cfnai_ma3 >= 0, "Growth Up", "Growth Down"), index=df.index
    )
    growth_label[cfnai_ma3.isna()] = ""

    fig = go.Figure()

    # --------------------------------------------------

    fig.add_trace(

        go.Bar(
            x=df["Date"],
            y=df["2s10s"],
            marker_color=colors,
            width=24 * 3600 * 1000,
            opacity=0.90,
            customdata=growth_label,
            hovertemplate=
             "<b>%{x}</b><br>"
            "2s10s = %{y:.2f}%<br>"
            "Growth: %{customdata}"
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
                color=ACCENT,
                width=3
            ),

            customdata=growth_label,

            hovertemplate=
            "<b>%{x}</b><br>"
            "Spread = %{y:.2f}%"
            "Growth: %{customdata}"
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