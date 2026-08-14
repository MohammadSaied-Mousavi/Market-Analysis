import streamlit as st
from theme import inject_global_style
from .bond_plot import (
    load_curve,
    get_y_scale,
    build_curve,
    build_curve_regime_chart_dynamic,
    build_curve_regime_chart
)


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

    fig = build_curve(
        df=df,
        lookback=st.session_state.bond_slider,
        y_range=y_range
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.slider(
        "Curve History",
        min_value=-30,
        max_value=-1,
        key="bond_slider"
    )

    st.divider()

    # =====================================================
    # Short-Term Regime
    # =====================================================

    st.subheader("Short-Term Curve Regime")

    col1, col2 = st.columns([1,5])

    with col1:

        st.number_input(
            "Lookback",
            min_value=5,
            max_value=60,
            step=1,
            key="curve_lookback"
        )

    fig,current = build_curve_regime_chart_dynamic(
        df,
        st.session_state.curve_lookback
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.success(f"Current Regime : **{current}**")

    st.divider()

    # =====================================================
    # Long-Term Regime
    # =====================================================

    st.subheader("Long-Term Structural Regime")

    st.caption("Fixed Lookback = 20 Days")

    fig = build_curve_regime_chart(df)

    st.plotly_chart(
        fig,
        use_container_width=True,

        config={
            "scrollZoom": True,
            "displaylogo": False
        }
    )

    st.divider()

    st.markdown("""
### Regime Legend   
🟩 Bull Steepener    🟥 Bear Steepener    🟨 Steepener Twist   🟦 Bull Flattener    🟪 Bear Flattener    ⬜ Flattener Twist
""")