import streamlit as st
import sys
from pathlib import Path
from theme import inject_global_style
sys.path.append(str(Path(__file__).parent))
from macroF import summary
from macroF import bond
from macroF import economic_regime


def show():
    inject_global_style()
    tab_summary, tab_bond, tab_regime = st.tabs(
        [
            "📋 Summary",
            "📑 Bond",
            "🏛 Economic Regime"
        ]
    )

    with tab_summary:
        summary.show()

    with tab_bond:
        bond.show()

    with tab_regime:
        economic_regime.show()
