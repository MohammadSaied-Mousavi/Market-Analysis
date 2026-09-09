import pandas as pd
import streamlit as st
from theme import inject_global_style
from .bond_plot import (
    load_curve,
    get_y_scale,
    build_curve,
    build_curve_regime_chart_dynamic,
    build_curve_regime_chart,
    build_regime_legend_figure,
    load_regime_growth_data,
    build_regime_growth_asset_table_forward,
    build_regime_growth_asset_table_episode,
    build_match_annotated_html,
    get_current_regime_growth_status,
    render_expected_results_html,
    build_regime_transition_matrix,
    build_transition_matrix_figure,
    get_current_episode_performance,
    render_current_episode_vs_history_html,
    GROWTH_ASSET_PROXIES,
)


def _fit_table_height(n_rows, row_px=35, header_px=38, pad_px=3):
    return header_px + row_px * n_rows + pad_px


def show():
    inject_global_style()
    df = load_curve()

    y_range = get_y_scale(df)

    if "bond_slider" not in st.session_state:
        st.session_state.bond_slider = -1

    if "curve_lookback" not in st.session_state:
        st.session_state.curve_lookback = 20

    # =====================================================
    # Yield Curve
    # =====================================================

    st.subheader("Yield Curve")

    fig = build_curve(df=df, lookback=st.session_state.bond_slider, y_range=y_range)
    st.plotly_chart(fig, use_container_width=True)

    st.slider("Curve History", min_value=-30, max_value=-1, key="bond_slider")

    st.divider()

    # =====================================================
    # Short-Term Regime
    # =====================================================

    st.subheader("Short-Term Curve Regime")

    col1, col2 = st.columns([1, 5])
    with col1:
        st.number_input("Lookback", min_value=5, max_value=60, step=1, key="curve_lookback")

    fig, current = build_curve_regime_chart_dynamic(df, st.session_state.curve_lookback)
    st.plotly_chart(fig, use_container_width=True)
    st.success(f"Current Regime : **{current}**")

    st.divider()

    # =====================================================
    # داده‌ی Growth زودتر لود می‌شه (هم برای وضعیت زیر چارت
    # بلندمدت لازمه، هم برای جدول‌های پایین صفحه)
    # =====================================================

    full_df = load_regime_growth_data()
    asset_labels = list(GROWTH_ASSET_PROXIES.values())
    table_episode = build_regime_growth_asset_table_episode(full_df, method="cfnai_level")

    # =====================================================
    # Long-Term Regime
    # =====================================================

    st.subheader("Long-Term Structural Regime")
    st.caption("Fixed Lookback = 20 Days")

    fig = build_curve_regime_chart(df)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"scrollZoom": True, "displaylogo": False},
    )

    status = get_current_regime_growth_status(full_df, method="cfnai_level")
    if status is not None:
        avg_length = table_episode.loc[(status["Growth"], status["Regime"]), "میانگین طول (روز)"]
        if pd.notna(avg_length) and avg_length > 0:
            ratio = status["Current Length"] / avg_length
            st.info(
                f"رژیم فعلی: **{status['Regime']}** — {status['Growth']}\n\n"
                f"از **{status['Since'].date()}** تا الان، **{status['Current Length']} روز** ادامه داشته "
                f"(میانگین تاریخی این ترکیب: **{avg_length:.1f} روز**، یعنی الان **{ratio:.1f}×** میانگین)."
            )
            perf = get_current_episode_performance(full_df, method="cfnai_level")
            if perf is not None:
                st.markdown("##### این اپیزود در برابر میانگین تاریخی همین رژیم")
                st.markdown(render_current_episode_vs_history_html(perf), unsafe_allow_html=True)

        else:
            st.info(
                f"رژیم فعلی: **{status['Regime']}** — {status['Growth']} "
                f"(**{status['Current Length']} روز** ادامه داشته؛ داده‌ی کافی برای میانگین تاریخی نیست)."
            )

    st.divider()
    with st.expander("راهنمای شکل رژیم‌ها"):
        st.plotly_chart(build_regime_legend_figure(), use_container_width=True)
    st.markdown("""
### Regime Legend   
🟩 Bull Steepener    🟥 Bear Steepener    🟨 Steepener Twist   🟦 Bull Flattener    🟪 Bear Flattener    ⬜ Flattener Twist
""")

    st.divider()
    st.subheader("ماتریس گذار بین رژیم‌ها")
    st.caption("از هر رژیم، دفعه‌ی بعد با چه احتمالی به کدوم رژیم رفتیم — مستقل از جهت رشد.")

    counts, prob = build_regime_transition_matrix(df)
    st.plotly_chart(build_transition_matrix_figure(counts, prob), use_container_width=True)
    
    st.divider()
    st.subheader("Growth × Regime × Asset Returns")

    with st.expander("نتایج مورد انتظار (تئوری کلاسیک Yield Curve Regime)"):
        st.caption("این جدول تجربی نیست — فقط انتظار تئوریک رایج رو نشون می‌ده تا با جدول واقعی زیر مقایسه بشه.")
        st.markdown(render_expected_results_html(), unsafe_allow_html=True)

    tab_forward, tab_episode = st.tabs([
        "بازدهی ۲۰ روز آینده (Forward)",
        "بازدهی کل طول رژیم (Per-Episode)",
    ])

    with tab_forward:
        table_forward = build_regime_growth_asset_table_forward(full_df, forward_days=20, method="cfnai_level")
        st.markdown(build_match_annotated_html(table_forward, asset_labels), unsafe_allow_html=True)
        st.caption(
            "میانگین بازدهی هر دارایی طیِ ۲۰ روز معاملاتیِ بعد از هر روزی که بازار توی همون رژیم "
            "و جهت رشد بوده — آمار توصیفیِ تاریخیه، نه پیش‌بینی. سبز/قرمز یعنی جهت واقعی با جدول «نتایج "
            "مورد انتظار» بالا هم‌خونی داره یا نه (فقط ۴ رژیم پایه؛ Twist مقایسه نمی‌شه)."
        )

    with tab_episode:
        st.markdown(build_match_annotated_html(table_episode, asset_labels), unsafe_allow_html=True)
        st.caption(
            "میانگین بازدهی کل هر دارایی طیِ کل مدتی که بازار پیوسته توی همون رژیم و جهت رشد "
            "مونده — «میانگین طول» نشون می‌ده این رژیم معمولاً چند روز دوام آورده."
        )