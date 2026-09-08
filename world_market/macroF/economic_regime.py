import streamlit as st

from world_market.macroF import regime_model1
from world_market.macroF import regime_model2
from world_market.macroF import regime_model3
from world_market.macroF import regime_model4
from world_market.macroF import regime_model5
from world_market.macroF import regime_model6
from theme import inject_global_style
def show() -> None:
    inject_global_style()
    model = st.selectbox(
        "Model",
        [
            "Model 1 - Credit & Inflation Regime Dashboard",
            "Model 2 - Credit & Inflation Regime Dashboard + HMM",
            "Model 3",
            "Model 4",
            "Model 5 - eco3min",
            "Model 6 - Markov-Switching Regime"
        ]
    )

    st.divider()

    if model == "Model 1 - Credit & Inflation Regime Dashboard":
        regime_model1.show()

    elif model == "Model 2 - Credit & Inflation Regime Dashboard + HMM":
        regime_model2.show()

    elif model == "Model 3":
        regime_model3.show()

    elif model == "Model 4":
        regime_model4.show()

    elif model == "Model 5 - eco3min":
        regime_model5.show()

    elif model == "Model 6 - Markov-Switching Regime":
        regime_model6.show()
