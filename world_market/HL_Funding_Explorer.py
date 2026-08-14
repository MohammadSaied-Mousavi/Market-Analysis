import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import math
import statistics
from hl_client import HLClient

def show_hl_explorer():
    client = HLClient(dex="xyz")

    ASSET_CLASSES = [
        ["EQUITY INDICES",      ["SP500","XYZ100","SPCX","NIFTY","JP225","KR200","IBOV","H100"]],
        ["VOLATILITY",          ["VIX","VOL"]],
        ["EQUITY ETFs",         ["EWY","EWJ","EWT","EWZ","XLE","URNM"]],
        ["US MEGA-CAP TECH",    ["AAPL","MSFT","AMZN","GOOGL","META","NVDA","TSLA","ORCL","AMD","INTC","MU"]],
        ["US EQUITIES — OTHER", ["COIN","HOOD","PLTR","MSTR","CRCL","NFLX","COST","LLY","CRWV","GME","RIVN","RKLB","HIMS","DKNG","BX","MRVL","LITE","BIRD","CBRS","USAR","ZM","EBAY","ARM","SNDK","SKHX"]],
        ["INTERNATIONAL EQUITIES", ["BABA","TSM","ASML","HYUNDAI","KIOXIA","SOFTBANK","SMSN","MINIMAX"]],
        ["ENERGY",              ["CL","BRENTOIL","NATGAS","TTF"]],
        ["METALS",              ["GOLD","SILVER","COPPER","PLATINUM","PALLADIUM","ALUMINIUM"]],
        ["AGRICULTURE",         ["CORN","WHEAT"]],
        ["FX",                  ["JPY","EUR","GBP","KRW","DXY"]],
        ["OTHER",               ["URANIUM","PURRDAT","DRAM"]],
    ]
    HEATMAP_WINDOWS = [("4h", 4), ("24h", 24), ("7d", 168), ("30d", 720)]

    @st.cache_data(ttl=3600, show_spinner="Loading universe...")
    def get_universe():
        return sorted(client.universe())

    @st.cache_data(ttl=10, show_spinner="Fetching data...")
    def get_bundle(coin, interval, lookback):
        return client.fetch_bundle(coin, interval, lookback)

    @st.cache_data(ttl=300, show_spinner="Building heatmaps (may take 20s)...")
    def get_heatmap_data(lookback):
        coins = client.universe()
        bundles = client.fetch_many(coins, interval="1h", lookback=lookback, workers=4)
        rows = []
        for coin, b in bundles.items():
            if b.get("error"): 
                rows.append({"coin": coin, "sigma_h": None, "ret_z": {w: None for w, _ in HEATMAP_WINDOWS}, "f_mu": {w: None for w, _ in HEATMAP_WINDOWS}})
                continue
            candles = b.get("candles") or []
            funding = b.get("funding") or []
            rets = []
            for i in range(1, len(candles)):
                try:
                    p0 = float(candles[i - 1]["c"]); p1 = float(candles[i]["c"])
                    if p0 > 0: rets.append(math.log(p1 / p0))
                except: pass
            sigma_h = statistics.pstdev(rets) if len(rets) >= 24 else None
            ret_z = {}
            f_mu = {}
            for w, h in HEATMAP_WINDOWS:
                if sigma_h and len(candles) >= h:
                    take = min(h, len(candles) - 1)
                    try:
                        p0 = float(candles[-(take + 1)]["c"]); p1 = float(candles[-1]["c"])
                        ret_z[w] = math.log(p1 / p0) / (sigma_h * math.sqrt(take)) if p0 > 0 else None
                    except: ret_z[w] = None
                else: ret_z[w] = None
                rates = []
                for r in funding[-h:] if len(funding) >= h else funding:
                    try: rates.append(float(r["fundingRate"]))
                    except: pass
                f_mu[w] = statistics.mean(rates) * 24 * 365 * 100 if rates else None
            rows.append({"coin": coin, "sigma_h": sigma_h, "ret_z": ret_z, "f_mu": f_mu})
        return rows

    def rolling_mean(arr, n):
        out = [None] * len(arr)
        if n <= 0: return out
        s = 0
        for i in range(len(arr)):
            s += arr[i]
            if i >= n: s -= arr[i - n]
            if i >= n - 1: out[i] = s / n
        return out

    def rolling_stdev(arr, n, mean_arr=None):
        out = [None] * len(arr)
        if n <= 1: return out
        s = 0; s2 = 0
        for i in range(len(arr)):
            s += arr[i]; s2 += arr[i] * arr[i]
            if i >= n:
                s -= arr[i - n]; s2 -= arr[i - n] * arr[i - n]
            if i >= n - 1:
                m = mean_arr[i] if mean_arr else s / n
                v = max(0, s2 / n - m * m)
                out[i] = math.sqrt(v)
        return out

    def rolling_sum(arr, n):
        out = [None] * len(arr)
        if n <= 0: return out
        s = 0
        for i in range(len(arr)):
            s += arr[i]
            if i >= n: s -= arr[i - n]
            if i >= n - 1: out[i] = s
        return out

    st.title("💰 HL Funding Explorer")
    st.markdown("HIP-3 perp analytics for Hyperliquid")

    with st.sidebar:
        st.header("⚙️ HL Controls")
        coins = get_universe()
        default_idx = coins.index("xyz:SP500") if "xyz:SP500" in coins else 0
        selected_coin = st.selectbox("PRIMARY TICKER", coins, index=default_idx)
        interval = st.selectbox("INTERVAL", ["5m", "15m", "1h", "4h", "1d"], index=2)
        lookback = st.selectbox("LOOKBACK", ["7d", "30d", "90d", "180d", "1y", "all"], index=1)
        st.markdown("---")
        mode = st.radio("FUNDING UNITS", ["annual", "hourly"], format_func=lambda x: "ANNUALIZED %" if x=="annual" else "HOURLY %")
        smooth_n = st.selectbox("SMOOTHED MA", [0, 24, 72, 168, 720], format_func=lambda x: "OFF" if x==0 else f"MA {x}h")
        band_sigma = st.selectbox("BAND σ", [0.5, 1, 2], index=1)
        rolling_n = st.selectbox("ROLLING COST", [0, 24, 168, 720], format_func=lambda x: "OFF" if x==0 else f"{x}h")
        st.markdown("---")
        show_hm = st.checkbox("Show Heatmaps", value=True)
        hm_lookback = st.selectbox("Heatmap Lookback", ["7d", "30d", "90d"], index=1)

    if selected_coin:
        bundle = get_bundle(selected_coin, interval, lookback)
        scale = 24 * 365 if mode == "annual" else 1
        unit = "ann %" if mode == "annual" else "hr %"
        df_c = pd.DataFrame(bundle["candles"])
        df_f = pd.DataFrame(bundle["funding"])
        rh = df_f["fundingRate"].astype(float).tolist() if not df_f.empty else []
        ma = rolling_mean(rh, smooth_n) if smooth_n > 0 else None
        sd = rolling_stdev(rh, smooth_n, ma) if smooth_n > 1 else None
        z_window = max(smooth_n, 24)
        z_ma = ma if z_window == smooth_n and ma else rolling_mean(rh, z_window)
        z_sd = sd if z_window == smooth_n and sd else rolling_stdev(rh, z_window, z_ma)
        z = [(rh[i] - z_ma[i]) / z_sd[i] if (z_ma[i] is not None and z_sd[i] not in [None, 0]) else None for i in range(len(rh))]
        rcost = rolling_sum(rh, rolling_n) if rolling_n > 0 else None
        rows = 2
        specs = [[{"secondary_y": True}], [{}]]
        if rolling_n > 0:
            rows = 3
            specs.append([{}])
        fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2] if rows==3 else [0.7, 0.3], specs=specs)
        if not df_c.empty:
            fig.add_trace(go.Candlestick(x=df_c["t"], open=df_c["o"], high=df_c["h"], low=df_c["l"], close=df_c["c"], name="Price", increasing_line_color="#14b8a6", decreasing_line_color="#dc2626"), row=1, col=1, secondary_y=False)
        if not df_f.empty:
            fig.add_trace(go.Scatter(x=df_f["time"], y=[v * scale for v in rh], name=f"Funding ({unit})", line=dict(color="#f59e0b", width=1.5)), row=1, col=1, secondary_y=True)
            if ma:
                fig.add_trace(go.Scatter(x=df_f["time"], y=[v * scale if v else None for v in ma], name=f"MA {smooth_n}h", line=dict(color="#fbbf24", width=2)), row=1, col=1, secondary_y=True)
            fig.add_trace(go.Scatter(x=df_f["time"], y=z, name="Z-Score", line=dict(color="#a78bfa", width=1.5)), row=2, col=1, secondary_y=False)
            if rolling_n > 0:
                fig.add_trace(go.Scatter(x=df_f["time"], y=rcost, name=f"Rolling Cost {rolling_n}h", line=dict(color="#38bdf8", width=1.5)), row=3, col=1, secondary_y=False)
        fig.update_layout(template="plotly_dark", height=750, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    if show_hm:
        st.markdown("---")
        st.header("🔥 HIP-3 DEX HEATMAPS")
        st.markdown("""<small><b>left:</b> realized return in σ-units across trailing windows · <b>right:</b> mean funding rate (annualized %) across trailing windows (signed: + = longs pay)</small>""", unsafe_allow_html=True)
        hm_data = get_heatmap_data(hm_lookback)
        by_class = {}
        for r in hm_data:
            bare = r["coin"].split(":")[-1]
            cls = "OTHER"
            for c, members in ASSET_CLASSES:
                if bare in members: cls = c; break
            if cls not in by_class: by_class[cls] = []
            by_class[cls].append(r)
        ordered_classes = [c[0] for c in ASSET_CLASSES] + ["OTHER"]
        labels = []
        z_returns = []
        z_funding = []
        text_returns = []
        text_funding = []
        for cls in ordered_classes:
            if cls not in by_class: continue
            grp = sorted(by_class[cls], key=lambda x: max([abs(v) if v else 0 for v in x["f_mu"].values()]), reverse=True)
            labels.append(f"─── {cls} ───")
            z_returns.append([None]*len(HEATMAP_WINDOWS))
            z_funding.append([None]*len(HEATMAP_WINDOWS))
            text_returns.append([""]*len(HEATMAP_WINDOWS))
            text_funding.append([""]*len(HEATMAP_WINDOWS))
            for r in grp:
                labels.append(r["coin"])
                z_ret_row = [r["ret_z"].get(w, None) for w, _ in HEATMAP_WINDOWS]
                z_fund_row = [r["f_mu"].get(w, None) for w, _ in HEATMAP_WINDOWS]
                z_returns.append(z_ret_row)
                z_funding.append(z_fund_row)
                text_returns.append([f"{v:.2f}σ" if v is not None else "" for v in z_ret_row])
                text_funding.append([f"{v:+.1f}%" if v is not None else "" for v in z_fund_row])
        x_labels = [w for w, _ in HEATMAP_WINDOWS]
        hm_height = max(800, len(labels) * 28)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**PRICE MOVE in σ-UNITS — log-return ÷ (ticker hourly σ × √hours)**")
            fig_hm1 = go.Figure(data=go.Heatmap(z=z_returns, x=x_labels, y=labels, text=text_returns, texttemplate="%{text}", textfont={"size": 13, "color": "#f4f4f4"}, colorscale=[[0, "#14b8a6"], [0.25, "#0d3833"], [0.5, "#2e2e2e"], [0.75, "#3d1212"], [1, "#dc2626"]], zmid=0, xgap=2, ygap=2))
            fig_hm1.update_layout(template="plotly_dark", height=hm_height, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", yaxis=dict(autorange="reversed", tickfont=dict(size=12)), xaxis=dict(side="top", tickfont=dict(size=14, color="#f59e0b")))
            st.plotly_chart(fig_hm1, use_container_width=True)
        with col2:
            st.markdown("**FUNDING RATE (ANNUALIZED %) — trailing-window mean · red = longs pay · teal = shorts pay**")
            fig_hm2 = go.Figure(data=go.Heatmap(z=z_funding, x=x_labels, y=labels, text=text_funding, texttemplate="%{text}", textfont={"size": 13, "color": "#f4f4f4"}, colorscale=[[0, "#14b8a6"], [0.25, "#0d3833"], [0.5, "#2e2e2e"], [0.75, "#3d1212"], [1, "#dc2626"]], zmid=0, xgap=2, ygap=2))
            fig_hm2.update_layout(template="plotly_dark", height=hm_height, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", yaxis=dict(autorange="reversed", tickfont=dict(size=12)), xaxis=dict(side="top", tickfont=dict(size=14, color="#f59e0b")))
            st.plotly_chart(fig_hm2, use_container_width=True)

    st.markdown("---")
    st.header("📚 راهنمای مفاهیم (Concept Guide)")
    st.markdown("""
    <div dir="rtl" style="text-align: right; line-height: 1.8; font-size: 15px;">
    <h4>نرخ فاندینگ (Funding Rate) چیست؟</h4>
    <p>نرخ فاندینگ مکانیزمی است که قیمت قراردادهای فیوچرز دائمی را به قیمت واقعی دارایی (اسپات) متصل می‌کند. این نرخ هر ساعت یکبار پرداخت یا دریافت می‌شود.</p>
    <ul>
        <li><b>فاندینگ مثبت (+):</b> یعنی قیمت فیوچرز بالاتر از قیمت اسپات است. در این حالت، <b>تریدرهای Long (خریدار) به تریدرهای Short (فروشنده) هزینه می‌پردازند</b>. این نشان‌دهنده سنتیمنت خوش‌بینانه و طمع در بازار است. اگر فاندینگ به شدت مثبت باشد، احتمال ریزش قیمت (Long Squeeze) افزایش می‌یابد.</li>
        <li><b>فاندینگ منفی (-):</b> یعنی قیمت فیوچرز پایین‌تر از قیمت اسپات است. در این حالت، <b>تریدرهای Short به تریدرهای Long هزینه می‌پردازند</b>. این نشان‌دهنده ترس در بازار است. اگر فاندینگ به شدت منفی باشد، احتمال پامپ قیمت (Short Squeeze) افزایش می‌یابد.</li>
    </ul>
    <h4>Z-Score (زی‌اسکور) چیست؟</h4>
    <p>این اندیکاتور نشان می‌دهد که نرخ فاندینگ فعلی چند «انحراف معیار» از میانگین تاریخی خود فاصله دارد.</p>
    <ul>
        <li>اگر Z-Score بالای <b>+2</b> یا زیر <b>-2</b> برود، یعنی بازار به صورت غیرعادی و آماری افراطی شده است. این یک سیگنال عالی برای معامله‌گران ضد-روند (Mean Reversion) است که بازار به زودی به حالت نرمال برمی‌گردد.</li>
    </ul>
    <h4>هزینه تجمعی (Rolling Cost) چیست؟</h4>
    <p>این نمودار مجموع هزینه‌هایی که یک پوزیشن Long در بازه‌های زمانی مختلف (مثلا ۷ روز یا ۳۰ روز) به عنوان فاندینگ پرداخت کرده است را نشان می‌دهد. این به شما کمک می‌کند تا بفهمید نگهداری طولانی‌مدت یک پوزیشن چقدر هزینه (یا سود) فاندینگ برای شما خواهد داشت.</p>
    <h4>میانگین متحرک (Smoothed MA) و باندها</h4>
    <p>خط میانگین متحرک (MA) نوسانات کوتاه‌مدت فاندینگ را صاف می‌کند تا روند اصلی را ببینید. باندهای بالا و پایین (بر اساس ضریب σ) نشان می‌دهند که نرخ فعلی چه زمانی از محدوده طبیعی خود خارج شده است.</p>
    </div>
    """, unsafe_allow_html=True)