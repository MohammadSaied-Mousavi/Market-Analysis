from __future__ import annotations

import os
import sys
import time
import subprocess

import pandas as pd
import streamlit as st

from theme import inject_global_style, ACCENT


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

DB_PATH = os.path.join(PROJECT_ROOT, "database", "macro_database.csv")
UPDATER_PATH = os.path.join(PROJECT_ROOT, "updater.py")


def _stat_card(label: str, value: str) -> str:
    return f"""
    <div class="stat-card">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{value}</div>
    </div>
    """


def show():

    inject_global_style()

    st.markdown(
        f"""
        <style>
        .stat-card{{
            border:1px solid rgba(255,255,255,0.09);
            background:rgba(255,255,255,0.025);
            border-radius:14px;
            padding:16px 18px;
            transition:border-color .25s ease, transform .25s ease;
        }}
        .stat-card:hover{{
            border-color:{ACCENT};
            transform:translateY(-3px);
        }}
        .stat-label{{
            font-size:13px;
            color:#8a8f98;
            margin-bottom:6px;
        }}
        .stat-value{{
            font-size:28px;
            font-weight:800;
            color:#f2f2f2;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🌍 Global Market Dashboard")

    st.divider()

    # ----------------------------
    # Database Information
    # ----------------------------

    if os.path.exists(DB_PATH):

        df = pd.read_csv(DB_PATH)

        last_date = str(df.iloc[-1]["Date"])
        rows = len(df)
        last_index = df.index[-1]
        update_time = time.strftime(
            "%Y-%m-%d %H:%M",
            time.localtime(os.path.getmtime(DB_PATH))
        )

    else:

        last_date = "-"
        rows = "-"
        last_index = "-"
        update_time = "-"
        st.warning(f"فایل دیتابیس پیدا نشد: {DB_PATH}")

    col1, col2, col3, col4 = st.columns(4)

    col1.markdown(_stat_card("Last Data", last_date), unsafe_allow_html=True)
    col2.markdown(_stat_card("Rows", f"{rows:,}" if isinstance(rows, int) else rows), unsafe_allow_html=True)
    col3.markdown(_stat_card("Last Update", update_time), unsafe_allow_html=True)
    col4.markdown(_stat_card("Last Index", last_index), unsafe_allow_html=True)

    st.write("")
    st.divider()

    # ----------------------------
    # Update Database
    # ----------------------------

    if st.button("🔄 Update Database", use_container_width=True):

        st.info("Updating database...")

        log_box = st.empty()

        logs = ""

        process = subprocess.Popen(
            [sys.executable, UPDATER_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in process.stdout:

            logs += line

            log_box.code(logs)

        process.wait()

        if process.returncode == 0:

            st.success("Database Updated Successfully ✅")
            time.sleep(10)
            log_box.empty()
            st.rerun()

        else:
            st.error("Database Update Failed ❌")

        time.sleep(10)

        log_box.empty()