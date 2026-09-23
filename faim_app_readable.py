"""
FAIM Survey Dashboard — Streamlit App
Author: David Liu MS (converted from R Markdown)
Pipeline: Raw REDCap CSV → Auto-clean → Analysis tabs
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from io import BytesIO
from copy import deepcopy
import re
from collections import Counter

# Statsmodels/scipy power the Site Comparison and Statistical Modeling tabs
# (chi-square test, binomial/Poisson/negative-binomial GLMs). Both tabs
# degrade gracefully with a warning if these aren't installed.
try:
    import statsmodels.api as sm; import statsmodels.formula.api as smf; from scipy.stats import chi2_contingency; HAS_STATS = True
except ImportError:
    HAS_STATS = False

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="FAIM Enrollment Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: #0f1f3d;
}
[data-testid="stAppViewContainer"] { background: #f4f6fb; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0b1a36;
    border-right: 1px solid #1e3260;
}
[data-testid="stSidebar"] * { color: #e0e8f7 !important; }
[data-testid="stSidebar"] .stMarkdown h2 {
    color: #7eb8f7 !important;
    font-family: 'DM Serif Display', serif;
    font-size: 1.05rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-top: 1.4rem;
    border-bottom: 1px solid #1e3260;
    padding-bottom: 0.35rem;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: #152848;
    border-radius: 8px;
    padding: 6px;
    border: 1px dashed #2e4d80;
}
[data-testid="stSidebar"] .stMultiSelect > div,
[data-testid="stSidebar"] .stDateInput > div {
    background: #152848 !important;
    border-radius: 8px;
}
[data-testid="stSidebar"] [data-testid="stButton"] button {
    background: #1e6fd9;
    color: #ffffff !important;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    width: 100%;
}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
    background: #175ab1;
}
.help-box {
    background: #152848;
    border: 1px solid #2e4d80;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    margin-top: 0.5rem;
    font-size: 0.78rem;
    line-height: 1.55;
}
.help-box b { color: #ffffff; }
.table-download-row {
    display: flex;
    justify-content: flex-end;
    margin: 0.25rem 0 0.5rem 0;
}

/* ── Page header ── */
.page-header {
    background: linear-gradient(135deg, #0b1a36 0%, #14306b 60%, #1a4a8a 100%);
    border-radius: 14px;
    padding: 1.8rem 2.4rem 1.5rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 4px 24px rgba(11,26,54,0.18);
}
.page-header h1 {
    font-family: 'DM Serif Display', serif;
    color: #fff; font-size: 1.9rem; margin: 0 0 0.25rem 0;
}
.page-header p { color: #a0bcdf; font-size: 0.88rem; margin: 0; }
.badge {
    display: inline-block; background: #1e6fd9;
    color: #e8f0fe !important; font-size: 0.7rem; font-weight: 600;
    padding: 3px 10px; border-radius: 20px;
    letter-spacing: 0.06em; text-transform: uppercase; margin-top: 0.55rem;
}

/* ── Pipeline stepper ── */
.pipeline-bar {
    display: flex; align-items: center; gap: 0.4rem;
    background: #fff; border-radius: 12px;
    padding: 1rem 1.6rem; margin-bottom: 1.4rem;
    box-shadow: 0 2px 10px rgba(11,26,54,0.06);
    flex-wrap: wrap;
}
.step {
    display: flex; align-items: center; gap: 0.5rem;
    padding: 0.45rem 1rem; border-radius: 8px;
    font-size: 0.8rem; font-weight: 600; letter-spacing: 0.03em;
}
.step.done   { background: #e6f6ee; color: #1a7a40; }
.step.active { background: #e8f1fb; color: #1249a0; }
.step.idle   { background: #f2f3f6; color: #9aa3b5; }
.step-arrow  { color: #c8d0de; font-size: 1rem; }

/* ── Cleaning audit card ── */
.audit-card {
    background: #fff; border-radius: 12px;
    border-left: 4px solid #2a9d5c;
    padding: 1.3rem 1.6rem; margin-bottom: 1.4rem;
    box-shadow: 0 2px 12px rgba(11,26,54,0.06);
}
.audit-card h3 {
    font-family: 'DM Serif Display', serif;
    font-size: 1.1rem; color: #0b1a36; margin: 0 0 0.9rem 0;
}
.audit-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 0.8rem; margin-bottom: 1rem;
}
.audit-stat {
    background: #f4f8ff; border-radius: 8px;
    padding: 0.7rem 1rem; text-align: center;
}
.audit-stat .av { font-size: 1.6rem; font-weight: 600; color: #0b1a36; line-height: 1; }
.audit-stat .al {
    font-size: 0.7rem; font-weight: 600; color: #6b7a99;
    text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.25rem;
}
.audit-stat.green .av { color: #1a7a40; }
.audit-stat.red   .av { color: #c0392b; }
.audit-stat.blue  .av { color: #1249a0; }
.audit-step-list { list-style: none; padding: 0; margin: 0; }
.audit-step-list li {
    font-size: 0.82rem; color: #3a4a6a;
    padding: 0.3rem 0; border-bottom: 1px solid #eef1f7;
    display: flex; align-items: flex-start; gap: 0.5rem;
}
.audit-step-list li:last-child { border-bottom: none; }
.audit-step-list li .tick { color: #2a9d5c; font-weight: bold; flex-shrink: 0; }
.audit-step-list li .warn { color: #e09c2a; font-weight: bold; flex-shrink: 0; }

/* ── Download band ── */
.dl-band {
    background: linear-gradient(90deg, #0f2a5c, #1a4a8a);
    border-radius: 10px; padding: 0.9rem 1.6rem;
    margin-bottom: 1.6rem; display: flex;
    align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 0.8rem;
}
.dl-band-text { color: #c8dcf5; font-size: 0.85rem; }
.dl-band-text b { color: #fff; }

/* ── KPI Cards ── */
.kpi-row { display: flex; gap: 1rem; margin-bottom: 1.6rem; flex-wrap: wrap; }
.kpi-card {
    background: #fff; border-radius: 12px;
    padding: 1.1rem 1.5rem; flex: 1; min-width: 130px;
    box-shadow: 0 2px 12px rgba(11,26,54,0.07);
    border-top: 3px solid #1e6fd9;
}
.kpi-card .label {
    font-size: 0.7rem; font-weight: 600; color: #6b7a99;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.45rem;
}
.kpi-card .value { font-size: 1.9rem; font-weight: 600; color: #0b1a36; line-height: 1; }
.kpi-card .sub   { font-size: 0.76rem; color: #3d8b40; margin-top: 0.28rem; }
.kpi-card.green { border-top-color: #2a9d5c; }
.kpi-card.teal  { border-top-color: #1a8fa0; }
.kpi-card.amber { border-top-color: #e09c2a; }

/* ── Section titles ── */
.section-title {
    font-family: 'DM Serif Display', serif; font-size: 1.2rem;
    color: #0b1a36; margin: 1.5rem 0 0.75rem 0;
    padding-left: 0.75rem; border-left: 3px solid #1e6fd9;
}

/* ── Info banner ── */
.info-banner {
    background: #e8f1fb; border-left: 4px solid #1e6fd9;
    border-radius: 0 8px 8px 0; padding: 0.75rem 1.1rem;
    margin-bottom: 1.1rem; font-size: 0.83rem; color: #1a3260;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tab"] {
    font-weight: 500; font-size: 0.84rem; letter-spacing: 0.02em; color: #4a5a7a;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #1e6fd9; border-bottom-color: #1e6fd9 !important;
}

/* ── Tables ── */
[data-testid="stDataFrame"] {
    border-radius: 10px; overflow: hidden;
    box-shadow: 0 2px 10px rgba(11,26,54,0.06);
}

/* ── Download buttons ── */
[data-testid="stDownloadButton"] button {
    background: #0b1a36; color: white; border: none;
    border-radius: 8px; font-weight: 500;
    padding: 0.5rem 1.2rem; letter-spacing: 0.02em;
    transition: background 0.2s;
}
[data-testid="stDownloadButton"] button:hover { background: #1e3d7a; }

/* ── Empty states ── */
.no-data {
    background: #fff8e6; border: 1px dashed #e0b84a;
    border-radius: 10px; padding: 2rem; text-align: center;
    color: #7a5c10; font-size: 0.88rem;
}
.upload-prompt {
    background: linear-gradient(135deg, #eef4ff, #f4f6fb);
    border: 2px dashed #92b4e3; border-radius: 14px;
    padding: 3rem 2rem; text-align: center; margin-top: 2rem;
}
.upload-prompt h3 {
    font-family: 'DM Serif Display', serif; color: #14306b; font-size: 1.4rem;
}
.upload-prompt p { color: #5a6e8c; font-size: 0.86rem; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
SITE_MAPPING = {1: "WCM", 2: "UTHSA", 3: "Yale", 4: "UCLA", 5: "NW/LURIE"}

EMAILS_TO_REMOVE = [
    "NICUresearch@med.cornell.edu", "dvm4001@med.cornell.edu", "elb4016@med.cornell.edu",
    "sarah.n.taylor@yale.edu",       "tessa.kehoe@yale.edu",    "terri.motraghi@yale.edu",
    "blanco@uthscsa.edu",            "anzuetod@uthscsa.edu",    "winterc@uthscsa.edu",
    "dtrobinson@luriechildrens.org", "jsilverglade@luriechildrens.org",
    "esierra@luriechildrens.org",    "kcalkins@mednet.ucla.edu",
    "amdong@mednet.ucla.edu",        "alisonchu@mednet.ucla.edu",
]

NUMERIC_COLS = [
    'lastweek_anteligible','antscreen_number','antscreen_excluded','antscreen_eligible',
    'antscreen_approached','antscreen_no_approach','antapproach_declined','antapproach_yes',
    'antapproach_defer','antapproach_agedout','antconsent_eligible','antconsent_noteligible',
    'antconsent_random','antconsent_notrandom','lastweek_nicueligible','nicu_gascreen',
    'nicu_eligible1','nicu_excluded','nicu_approached','nicu_notapproach','nicu_decline',
    'nicu_toolate','nicu_consent','nicu_randomized',
]

SITE_COLORS = {
    "WCM":      "#1e6fd9",
    "UTHSA":    "#2a9d5c",
    "Yale":     "#e07b39",
    "UCLA":     "#9b59b6",
    "NW/LURIE": "#1a8fa0",
}

PLOTLY_BASE = dict(
    template="plotly_white",
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    font=dict(family="DM Sans, sans-serif", color="#0f1f3d", size=14),
    margin=dict(l=90, r=40, t=40, b=85),
    title=dict(text="", x=0.01, xanchor="left", font=dict(size=16, color="#0b1a36")),
    legend=dict(
        bgcolor="rgba(255,255,255,0.96)",
        bordercolor="#c7d3e6",
        borderwidth=1,
        font=dict(color="#0f1f3d", size=13),
        title=dict(text="", font=dict(color="#0f1f3d", size=13)),
    ),
    xaxis=dict(
        showgrid=True,
        gridcolor="#e2e9f4",
        linecolor="#9fb0c8",
        linewidth=1.3,
        tickfont=dict(color="#0f1f3d", size=13),
        title=dict(text="", font=dict(color="#0f1f3d", size=14)),
        automargin=True,
        showline=True,
        zeroline=False,
        ticks="outside",
        tickcolor="#9fb0c8",
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="#e2e9f4",
        linecolor="#9fb0c8",
        linewidth=1.3,
        tickfont=dict(color="#0f1f3d", size=13),
        title=dict(text="", font=dict(color="#0f1f3d", size=14)),
        automargin=True,
        showline=True,
        zeroline=False,
        ticks="outside",
        tickcolor="#9fb0c8",
    ),
)


# ─────────────────────────────────────────────
# CLEANING PIPELINE
# Mirrors the original R Markdown logic exactly:
#   1. Remove rows with staff/test email addresses
#   2. Fill NaN → 0 for all 24 numeric enrollment columns
#   3. Cast those columns to int
#   4. Derive helper columns used throughout the report
# Returns (cleaned_df, audit_dict)
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def clean_pipeline(file_bytes: bytes):
    raw      = pd.read_csv(BytesIO(file_bytes))
    raw_rows = len(raw)
    raw_cols = len(raw.columns)

    # Step 1 – remove test/staff email rows
    email_mask = raw.apply(
        lambda row: row.astype(str)
                       .str.contains('|'.join(EMAILS_TO_REMOVE), na=False, regex=True)
                       .any(),
        axis=1,
    )
    rows_removed = int(email_mask.sum())
    data = raw[~email_mask].copy()

    # Step 2 & 3 – fill nulls → 0, cast to int
    present_num = [c for c in NUMERIC_COLS if c in data.columns]
    missing_num = [c for c in NUMERIC_COLS if c not in data.columns]
    nulls_filled = int(data[present_num].isna().sum().sum())
    for col in present_num:
        data[col] = data[col].fillna(0).astype(int)

    # Step 4 – parse dates & map sites
    data['survey_date']    = pd.to_datetime(data['survey_date'], errors='coerce')
    data = data.dropna(subset=['survey_date']).copy()
    data['screening_site'] = data['screening_site'].map(SITE_MAPPING).fillna('Unknown')

    # Step 5 – derived columns
    data['Consented_Babies'] = data.get('nicu_randomized', 0) + data.get('antconsent_random', 0)
    data['Eligible_Babies']  = data.get('antconsent_eligible', 0) + data.get('nicu_eligible1', 0)
    data['year_month']       = data['survey_date'].dt.to_period('M')
    data['week']             = data['survey_date'].dt.isocalendar().week.astype(int)
    data['year']             = data['survey_date'].dt.year

    audit = {
        "raw_rows":     raw_rows,
        "raw_cols":     raw_cols,
        "rows_removed": rows_removed,
        "clean_rows":   len(data),
        "nulls_filled": nulls_filled,
        "cols_cast":    len(present_num),
        "cols_missing": missing_num,
        "date_range":   (data['survey_date'].min(), data['survey_date'].max()),
        "sites_found":  sorted(data['screening_site'].unique().tolist()),
    }
    return data, audit


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


# ─────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────
def render_kpis(cards: list):
    cols = st.columns(len(cards))
    for col, c in zip(cols, cards):
        sub = f'<div class="sub">{c["sub"]}</div>' if c.get("sub") else ""
        col.markdown(f"""
        <div class="kpi-card {c.get('cls','')}">
            <div class="label">{c['label']}</div>
            <div class="value">{c['value']}</div>
            {sub}
        </div>
        """, unsafe_allow_html=True)


def download_dataframe(label: str, df: pd.DataFrame, filename: str, key: str):
    st.download_button(
        label=label,
        data=to_csv_bytes(df.reset_index()),
        file_name=filename,
        mime="text/csv",
        key=key,
    )


def _deep_merge(base: dict, extra: dict) -> dict:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def plotly_layout(**extra):
    layout = deepcopy(PLOTLY_BASE)

    if 'title' in extra and isinstance(extra['title'], str):
        extra['title'] = dict(text=extra['title'], x=0.01, xanchor='left', font=layout['title']['font'])

    if 'legend_title' in extra:
        legend_title = extra.pop('legend_title')
        extra.setdefault('legend', {})
        extra['legend'].setdefault('title', {})
        extra['legend']['title']['text'] = legend_title

    if 'xaxis_title' in extra:
        xaxis_title = extra.pop('xaxis_title')
        extra.setdefault('xaxis', {})
        extra['xaxis'].setdefault('title', {})
        extra['xaxis']['title']['text'] = xaxis_title

    if 'yaxis_title' in extra:
        yaxis_title = extra.pop('yaxis_title')
        extra.setdefault('yaxis', {})
        extra['yaxis'].setdefault('title', {})
        extra['yaxis']['title']['text'] = yaxis_title

    return _deep_merge(layout, extra)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:1rem 0 0.4rem;'>
        <div style='font-size:2rem;'>🏥</div>
        <div style='font-family:DM Serif Display,serif; font-size:1.05rem;
                    color:#7eb8f7; letter-spacing:0.04em;'>FAIM Dashboard</div>
        <div style='font-size:0.7rem; color:#4a6a9a; margin-top:2px;'>
            NICU Enrollment Tracker
        </div>
    </div>
    <hr style='border-color:#1e3260; margin:0.6rem 0;'>
    """, unsafe_allow_html=True)

    st.markdown("## 📁 Data Upload")
    st.markdown("""
    <div style='font-size:0.75rem; color:#4a6a9a; margin-bottom:0.5rem; line-height:1.6;'>
        Upload the <b>raw REDCap export</b>.<br>
        The app cleans it automatically before analysis.
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Raw enrollment CSV",
        type=["csv"],
        help="FAIMEnrollmentWeekly_DATA_*.csv from REDCap",
        label_visibility="collapsed",
    )
    data_loaded = uploaded_file is not None

    if data_loaded:
        file_bytes      = uploaded_file.read()
        raw_data, audit = clean_pipeline(file_bytes)
        cleaned_filename = f"FAIM_cleaned_{datetime.now().strftime('%m-%d-%Y')}.csv"

        st.markdown("## 🔍 Filters")
        all_sites = sorted([s for s in raw_data['screening_site'].unique() if s != 'Unknown'])
        min_d = raw_data['survey_date'].min().date()
        max_d = raw_data['survey_date'].max().date()
        file_token = f"{uploaded_file.name}-{uploaded_file.size}"

        if st.session_state.get('faim_file_token') != file_token:
            st.session_state['faim_file_token'] = file_token
            st.session_state['site_filter'] = all_sites
            st.session_state['date_filter'] = (min_d, max_d)

        if 'site_filter' not in st.session_state:
            st.session_state['site_filter'] = all_sites
        if 'date_filter' not in st.session_state:
            st.session_state['date_filter'] = (min_d, max_d)

        if st.button('Reset Filters', use_container_width=True):
            st.session_state['site_filter'] = all_sites
            st.session_state['date_filter'] = (min_d, max_d)
            st.rerun()

        selected_sites = st.multiselect(
            "Screening Sites", options=all_sites, default=all_sites, key='site_filter'
        )
        date_range = st.date_input(
            "Date Range",
            value=st.session_state['date_filter'],
            min_value=min_d,
            max_value=max_d,
            key='date_filter',
        )

        st.markdown("## ℹ️ Definitions")
        st.markdown("""
        <div class="help-box">
            <b>Eligible</b><br>
            Babies counted as eligible for approach / consent based on the cleaned enrollment fields.<br><br>
            <b>Consented</b><br>
            Babies who were consented / randomized in the cleaned enrollment file.<br><br>
            <b>Consent Rate</b><br>
            Consented divided by eligible, expressed as a percent.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("## ⬇️ Export")
        st.download_button(
            label="⬇ Download Cleaned CSV",
            data=to_csv_bytes(raw_data),
            file_name=cleaned_filename,
            mime="text/csv",
            use_container_width=True,
        )
        filtered_sidebar = raw_data[
            raw_data['screening_site'].isin(selected_sites) &
            (raw_data['survey_date'] >= pd.Timestamp(date_range[0])) &
            (raw_data['survey_date'] <= pd.Timestamp(date_range[1]))
        ].copy() if len(date_range) == 2 else raw_data.copy()
        st.download_button(
            label="⬇ Download Filtered Data",
            data=to_csv_bytes(filtered_sidebar),
            file_name=f"FAIM_filtered_{datetime.now().strftime('%m-%d-%Y')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.markdown(f"""
        <div style='font-size:0.7rem; color:#3a5a8a; text-align:center;
                    margin-top:0.4rem; line-height:1.7;'>
            <b>{audit['clean_rows']:,}</b> records ·
            <b>{audit['rows_removed']}</b> test rows removed<br>
            <b>{audit['date_range'][0].strftime('%b %d, %Y')}</b> →
            <b>{audit['date_range'][1].strftime('%b %d, %Y')}</b>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='font-size:0.78rem; color:#4a6a9a; margin-top:1rem; line-height:1.8;'>
            ↑ Upload your REDCap CSV to begin.<br>
            <span style='color:#2e6faa;'>Raw data is cleaned automatically.</span>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h1>FAIM Enrollment Dashboard</h1>
    <p>Family Attitudes and Infant Management — Multi-Site NICU Enrollment Tracker</p>
    <span class="badge">WCM · UTHSA · Yale · UCLA · NW/LURIE</span>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GATE — require upload
# ─────────────────────────────────────────────
if not data_loaded:
    st.markdown("""
    <div class="pipeline-bar">
        <div class="step active">① Upload Raw CSV</div>
        <div class="step-arrow">→</div>
        <div class="step idle">② Auto-Clean</div>
        <div class="step-arrow">→</div>
        <div class="step idle">③ Download Cleaned</div>
        <div class="step-arrow">→</div>
        <div class="step idle">④ Explore Analysis</div>
    </div>
    <div class="upload-prompt">
        <h3>Upload Your Raw REDCap Export to Begin</h3>
        <p>Use the <b>Data Upload</b> panel in the sidebar.<br>
        The app removes test rows, fills missing values, and casts columns automatically.<br>
        No data leaves your browser session.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────
# PIPELINE STEPPER — complete state
# ─────────────────────────────────────────────
st.markdown("""
<div class="pipeline-bar">
    <div class="step done">✓ Raw CSV Uploaded</div>
    <div class="step-arrow">→</div>
    <div class="step done">✓ Data Cleaned</div>
    <div class="step-arrow">→</div>
    <div class="step done">✓ Ready to Download</div>
    <div class="step-arrow">→</div>
    <div class="step active">④ Explore Analysis ↓</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CLEANING AUDIT PANEL
# ─────────────────────────────────────────────
missing_warn = ""
if audit["cols_missing"]:
    cols_str = ', '.join(audit['cols_missing'][:6])
    if len(audit['cols_missing']) > 6:
        cols_str += ' …'
    missing_warn = f"""
    <li><span class="warn">⚠</span>
    {len(audit['cols_missing'])} expected numeric column(s) not found in this file:
    <code style='font-size:0.75rem;'>{cols_str}</code></li>"""

with st.expander("🧹 Data Cleaning Report — click to expand / collapse", expanded=True):
    st.markdown(f"""
    <div class="audit-card">
        <h3>🧹 Cleaning Summary</h3>
        <div class="audit-grid">
            <div class="audit-stat">
                <div class="av">{audit['raw_rows']:,}</div>
                <div class="al">Raw Rows In</div>
            </div>
            <div class="audit-stat red">
                <div class="av">−{audit['rows_removed']}</div>
                <div class="al">Test / Staff Rows Removed</div>
            </div>
            <div class="audit-stat green">
                <div class="av">{audit['clean_rows']:,}</div>
                <div class="al">Clean Rows Out</div>
            </div>
            <div class="audit-stat blue">
                <div class="av">{audit['nulls_filled']:,}</div>
                <div class="al">Null Values → 0</div>
            </div>
            <div class="audit-stat blue">
                <div class="av">{audit['cols_cast']}</div>
                <div class="al">Columns Cast to Int</div>
            </div>
            <div class="audit-stat">
                <div class="av">{len(audit['sites_found'])}</div>
                <div class="al">Sites Detected</div>
            </div>
        </div>
        <ul class="audit-step-list">
            <li><span class="tick">✓</span>
                Removed <b>{audit['rows_removed']}</b> row(s) matching
                {len(EMAILS_TO_REMOVE)} known staff / test email addresses.</li>
            <li><span class="tick">✓</span>
                Filled <b>{audit['nulls_filled']}</b> null value(s) with <code>0</code>
                across {audit['cols_cast']} numeric enrollment columns.</li>
            <li><span class="tick">✓</span>
                Cast all {audit['cols_cast']} enrollment columns to
                <code>integer</code> dtype.</li>
            <li><span class="tick">✓</span>
                Parsed <code>survey_date</code> to datetime. Range:
                <b>{audit['date_range'][0].strftime('%b %d, %Y')}</b> →
                <b>{audit['date_range'][1].strftime('%b %d, %Y')}</b>.</li>
            <li><span class="tick">✓</span>
                Mapped <code>screening_site</code> codes → names:
                {', '.join(audit['sites_found'])}.</li>
            <li><span class="tick">✓</span>
                Derived <code>Consented_Babies</code>
                (nicu_randomized + antconsent_random) and
                <code>Eligible_Babies</code>
                (antconsent_eligible + nicu_eligible1).</li>
            {missing_warn}
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Numeric column summary (cleaned data)**")
    num_cols_present = [c for c in NUMERIC_COLS if c in raw_data.columns]
    num_summary      = raw_data[num_cols_present].describe().T.round(2)
    st.dataframe(num_summary, use_container_width=True, height=260)


# ─────────────────────────────────────────────
# DOWNLOAD BAND  (prominent, above tabs)
# ─────────────────────────────────────────────
dl_col1, dl_col2 = st.columns([3.5, 1])
with dl_col1:
    st.markdown(f"""
    <div class="dl-band">
        <div class="dl-band-text">
            <b>Cleaned data ready.</b>&nbsp;&nbsp;
            {audit['clean_rows']:,} records &nbsp;·&nbsp;
            {audit['rows_removed']} test rows removed &nbsp;·&nbsp;
            {audit['nulls_filled']:,} nulls filled →
            <b>{cleaned_filename}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)
with dl_col2:
    st.download_button(
        label="⬇ Download Cleaned CSV",
        data=to_csv_bytes(raw_data),
        file_name=cleaned_filename,
        mime="text/csv",
        use_container_width=True,
    )


# ─────────────────────────────────────────────
# APPLY SIDEBAR FILTERS TO CLEANED DATA
# ─────────────────────────────────────────────
if len(date_range) == 2:
    start_dt = pd.Timestamp(date_range[0])
    end_dt   = pd.Timestamp(date_range[1])
else:
    start_dt = raw_data['survey_date'].min()
    end_dt   = raw_data['survey_date'].max()

df = raw_data[
    raw_data['screening_site'].isin(selected_sites) &
    (raw_data['survey_date'] >= start_dt) &
    (raw_data['survey_date'] <= end_dt)
].copy()

if df.empty:
    st.markdown(
        '<div class="no-data">⚠️ No data matches the current filters. '
        'Adjust site or date range in the sidebar.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

st.markdown(f"""
<div style='font-size:0.78rem; color:#6b7a99; margin-bottom:0.8rem;'>
    Showing <b>{len(df):,}</b> records &nbsp;·&nbsp;
    Sites: <b>{', '.join(selected_sites)}</b> &nbsp;·&nbsp;
    {start_dt.strftime('%b %d, %Y')} → {end_dt.strftime('%b %d, %Y')}
</div>
""", unsafe_allow_html=True)

download_dataframe('⬇ Download Current Filtered Dataset', df, 'filtered_dataset_current_view.csv', 'dl_filtered_dataset_top')


# ═══════════════════════════════════════════════════
# ANALYSIS TABS
# ═══════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "📊  Overview",
    "📅  Weekly Summary",
    "📆  Monthly Enrollment",
    "🗓  Biweekly Periods",
    "📈  Cumulative vs Expected",
    "🔻  Funnel Analysis",
    "🏢  Site Comparison",
    "📉  Time Trends",
    "🧮  Statistical Models",
    "🔍  Data Quality",
])


# ────────────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ────────────────────────────────────────────────────
with tab1:
    total_eligible  = int(df['Eligible_Babies'].sum())
    total_consented = int(df['Consented_Babies'].sum())
    consent_rate    = (total_consented / total_eligible * 100) if total_eligible else 0

    render_kpis([
        {"label": "Total Eligible Babies",  "value": f"{total_eligible:,}",  "cls": ""},
        {"label": "Total Consented Babies", "value": f"{total_consented:,}", "cls": "green"},
        {"label": "Overall Consent Rate",   "value": f"{consent_rate:.1f}%", "cls": "teal",
         "sub": "consented / eligible"},
        {"label": "Active Sites",     "value": str(df['screening_site'].nunique()), "cls": ""},
        {"label": "Reporting Weeks",  "value": str(df['week'].nunique()),           "cls": "amber"},
    ])

    st.markdown('<div class="section-title">Total Eligible vs. Consented by Site</div>',
                unsafe_allow_html=True)
    site_totals = df.groupby('screening_site').agg(
        Eligible=('Eligible_Babies','sum'),
        Consented=('Consented_Babies','sum')
    ).reset_index()
    site_totals['Rate'] = (
        site_totals['Consented'] / site_totals['Eligible'].replace(0, np.nan) * 100
    ).round(1).fillna(0)

    fig_ov = go.Figure()
    for _, row in site_totals.iterrows():
        c = SITE_COLORS.get(row['screening_site'], '#888')
        fig_ov.add_trace(go.Bar(
            x=[row['screening_site']], y=[row['Eligible']],
            name=f"{row['screening_site']} – Eligible",
            marker_color=c, opacity=0.38,
        ))
        fig_ov.add_trace(go.Bar(
            x=[row['screening_site']], y=[row['Consented']],
            name=f"{row['screening_site']} – Consented",
            marker_color=c, text=f"{row['Rate']}%", textposition='outside',
        ))
    fig_ov.update_layout(**plotly_layout(
        barmode='group',
        height=420,
        xaxis_title="Site",
        yaxis_title="Babies",
        legend_title="Site / Metric",
        xaxis=dict(title=dict(standoff=14)),
        yaxis=dict(title=dict(standoff=10)),
    ))
    fig_ov.update_traces(textfont_color="#0f1f3d", cliponaxis=False)
    st.plotly_chart(fig_ov, use_container_width=True, theme=None)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown('<div class="section-title">Consent Rate by Site</div>', unsafe_allow_html=True)
        fig_rate = px.bar(
            site_totals.sort_values('Rate'),
            x='Rate', y='screening_site', orientation='h',
            text='Rate', color='screening_site',
            color_discrete_map=SITE_COLORS,
        )
        fig_rate.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_rate.update_layout(**plotly_layout(
            height=320,
            showlegend=False,
            xaxis_title="Consent Rate (%)",
            yaxis_title="",
            xaxis=dict(range=[0, 115], title=dict(standoff=14)),
            yaxis=dict(tickfont=dict(size=13)),
        ))
        fig_rate.update_traces(textfont_color="#0f1f3d", cliponaxis=False)
        st.plotly_chart(fig_rate, use_container_width=True, theme=None)
    with col_r:
        st.markdown('<div class="section-title">Site Summary Table</div>', unsafe_allow_html=True)
        disp = site_totals.rename(columns={
            'screening_site':'Site', 'Rate':'Consent Rate (%)'
        }).set_index('Site')
        download_dataframe('⬇ Download Site Summary', disp, 'site_summary_filtered.csv', 'dl_site_summary')
        st.dataframe(disp, use_container_width=True, height=300)


# ────────────────────────────────────────────────────
# TAB 2 — WEEKLY SUMMARY
# ────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="info-banner">📌 Week-by-week eligible and consented babies by site. Week numbers are ISO calendar weeks.</div>', unsafe_allow_html=True)

    weekly = df.groupby(['year','week','screening_site']).agg(
        Eligible=('Eligible_Babies','sum'),
        Consented=('Consented_Babies','sum')
    ).reset_index()
    weekly['period'] = (weekly['year'].astype(str) + '-W' +
                        weekly['week'].astype(str).str.zfill(2))
    weekly = weekly.sort_values(['year','week'])

    c1, c2 = st.columns(2)
    with c1:
        metric = st.selectbox("Metric", ["Both","Eligible","Consented"], index=0)
    with c2:
        ctype  = st.selectbox("Chart style", ["Grouped Bars","Stacked Bars","Line"], index=0)

    fig_wk = go.Figure()
    bm = 'stack' if ctype == "Stacked Bars" else 'group'
    for site in selected_sites:
        sw = weekly[weekly['screening_site'] == site]
        c  = SITE_COLORS.get(site, '#888')
        if metric in ("Eligible","Both"):
            if ctype == "Line":
                fig_wk.add_trace(go.Scatter(
                    x=sw['period'], y=sw['Eligible'], name=f'{site} – Elig.',
                    mode='lines+markers', line=dict(color=c, dash='dot'), marker=dict(size=5)))
            else:
                fig_wk.add_trace(go.Bar(
                    x=sw['period'], y=sw['Eligible'],
                    name=f'{site} – Elig.', marker_color=c, opacity=0.4))
        if metric in ("Consented","Both"):
            if ctype == "Line":
                fig_wk.add_trace(go.Scatter(
                    x=sw['period'], y=sw['Consented'], name=f'{site} – Cons.',
                    mode='lines+markers', line=dict(color=c), marker=dict(size=7)))
            else:
                fig_wk.add_trace(go.Bar(
                    x=sw['period'], y=sw['Consented'],
                    name=f'{site} – Cons.', marker_color=c))
    fig_wk.update_layout(**plotly_layout(
        barmode=bm,
        height=470,
        xaxis_title="Week",
        yaxis_title="Babies",
        xaxis=dict(tickangle=-45, title=dict(standoff=14)),
        yaxis=dict(title=dict(standoff=10)),
        legend_title="Site / Metric",
    ))
    st.plotly_chart(fig_wk, use_container_width=True, theme=None)

    st.markdown('<div class="section-title">Weekly Pivot Table</div>', unsafe_allow_html=True)
    pvt_wk = weekly.pivot_table(
        index=['year','week'], columns='screening_site',
        values=['Eligible','Consented'], aggfunc='sum', fill_value=0
    )
    pvt_wk.columns = [f"{m} – {s}" for m, s in pvt_wk.columns]
    download_dataframe('⬇ Download Weekly Pivot', pvt_wk, 'weekly_summary_filtered.csv', 'dl_weekly_pivot')
    st.dataframe(pvt_wk, use_container_width=True)


# ────────────────────────────────────────────────────
# TAB 3 — MONTHLY ENROLLMENT
# ────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="info-banner">📌 Monthly NICU consents by site, consent heatmap, grouped eligibility / enrollment bars, and grand-total bar including all sites.</div>', unsafe_allow_html=True)

    # Monthly NICU consents — line chart
    st.markdown('<div class="section-title">Monthly NICU Consents by Site</div>', unsafe_allow_html=True)
    mo_con = df.groupby(
        ['screening_site', pd.Grouper(key='survey_date', freq='ME')]
    )['nicu_consent'].sum().reset_index()
    mo_con['mo'] = mo_con['survey_date'].dt.strftime('%Y-%m')

    fig_ml = go.Figure()
    for site in selected_sites:
        sd = mo_con[mo_con['screening_site'] == site]
        fig_ml.add_trace(go.Scatter(
            x=sd['mo'], y=sd['nicu_consent'], name=site,
            mode='lines+markers',
            line=dict(color=SITE_COLORS.get(site,'#888'), width=2.5),
            marker=dict(size=7),
        ))
    fig_ml.update_layout(**plotly_layout(
        height=390,
        xaxis_title="Month",
        yaxis_title="NICU Consents",
        xaxis=dict(tickangle=-45, title=dict(standoff=14)),
        yaxis=dict(title=dict(standoff=10)),
        legend_title="Site",
    ))
    st.plotly_chart(fig_ml, use_container_width=True, theme=None)

    # Pivot table + heatmap
    mo_tot = df.groupby(
        ['screening_site', pd.Grouper(key='survey_date', freq='ME')]
    )['Consented_Babies'].sum().reset_index()
    mo_tot['mo'] = mo_tot['survey_date'].dt.strftime('%Y-%m')
    pvt_mo = mo_tot.pivot_table(index='mo', columns='screening_site',
                                 values='Consented_Babies', fill_value=0)
    pvt_mo['Total'] = pvt_mo.sum(axis=1)

    cl, cr = st.columns([1.2, 1])
    with cl:
        st.markdown('<div class="section-title">Monthly Consented (Pivot)</div>', unsafe_allow_html=True)
        download_dataframe('⬇ Download Monthly Pivot', pvt_mo, 'monthly_consented_pivot_filtered.csv', 'dl_monthly_pivot')
        st.dataframe(pvt_mo, use_container_width=True, height=320)
    with cr:
        st.markdown('<div class="section-title">Consent Heatmap</div>', unsafe_allow_html=True)
        heat = pvt_mo.drop(columns='Total', errors='ignore')
        fig_h = px.imshow(
            heat.T,
            color_continuous_scale=[[0,'#eef4ff'],[0.5,'#5b9bd5'],[1,'#0b1a36']],
            aspect='auto', text_auto=True,
        )
        fig_h.update_layout(**plotly_layout(
            height=320,
            xaxis_title="Month",
            yaxis_title="Site",
            xaxis=dict(title=dict(standoff=12)),
            yaxis=dict(title=dict(standoff=10)),
            coloraxis_colorbar=dict(title=dict(text="Consented", font=dict(color='#0f1f3d', size=13)), tickfont=dict(color='#0f1f3d', size=12)),
        ))
        st.plotly_chart(fig_h, use_container_width=True, theme=None)

    # Monthly eligibility + enrollment grouped bar
    st.markdown('<div class="section-title">Monthly Eligibility & Enrollment by Site</div>', unsafe_allow_html=True)
    mo_both = df.groupby(
        ['screening_site', pd.Grouper(key='survey_date', freq='ME')]
    ).agg(Consented=('Consented_Babies','sum'),
          Eligible=('Eligible_Babies','sum')).reset_index()
    mo_both['mo'] = mo_both['survey_date'].dt.strftime('%Y-%m')

    fig_mb = go.Figure()
    for site in selected_sites:
        sd = mo_both[mo_both['screening_site'] == site]
        c  = SITE_COLORS.get(site, '#888')
        fig_mb.add_trace(go.Bar(x=sd['mo'], y=sd['Eligible'],
                                name=f'{site} – Elig.', marker_color=c, opacity=0.38))
        fig_mb.add_trace(go.Bar(x=sd['mo'], y=sd['Consented'],
                                name=f'{site} – Cons.', marker_color=c))
    fig_mb.update_layout(**plotly_layout(
        barmode='group',
        height=420,
        xaxis_title="Month",
        yaxis_title="Babies",
        xaxis=dict(tickangle=-45, title=dict(standoff=14)),
        yaxis=dict(title=dict(standoff=10)),
        legend_title="Site / Metric",
    ))
    st.plotly_chart(fig_mb, use_container_width=True, theme=None)

    # Total consented per site incl. grand total
    st.markdown('<div class="section-title">Total Consented Babies per Site (incl. Grand Total)</div>', unsafe_allow_html=True)
    tot_site = df.groupby('screening_site')['Consented_Babies'].sum().reset_index()
    grand    = tot_site['Consented_Babies'].sum()
    tot_site = pd.concat([
        tot_site,
        pd.DataFrame({'screening_site':['Grand Total'], 'Consented_Babies':[grand]})
    ], ignore_index=True)

    bar_colors = [SITE_COLORS.get(s, '#344a6e') for s in tot_site['screening_site']]
    fig_tot = go.Figure(go.Bar(
        x=tot_site['screening_site'], y=tot_site['Consented_Babies'],
        marker_color=bar_colors,
        text=tot_site['Consented_Babies'], textposition='outside',
    ))
    fig_tot.update_layout(**plotly_layout(
        height=380,
        xaxis_title="Screening Site",
        yaxis_title="Total Consented Babies",
        xaxis=dict(title=dict(standoff=14)),
        yaxis=dict(title=dict(standoff=10)),
    ))
    fig_tot.update_traces(textfont_color="#0f1f3d", cliponaxis=False)
    st.plotly_chart(fig_tot, use_container_width=True, theme=None)


# ────────────────────────────────────────────────────
# TAB 4 — BIWEEKLY PERIODS
# ────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="info-banner">📌 Data in 2-week blocks. Select a period — most recent first. Bars show eligible vs consented with consent % annotated on each bar.</div>', unsafe_allow_html=True)

    bw_origin   = datetime(2023, 3, 10)
    max_dt_data = df['survey_date'].max().to_pydatetime()
    bw_ranges   = []
    s = bw_origin
    while s <= max_dt_data:
        e = s + timedelta(days=13)
        bw_ranges.append((s, e))
        s = e + timedelta(days=1)
    bw_ranges = list(reversed(bw_ranges))

    labels     = [f"{s.strftime('%b %d')} – {e.strftime('%b %d, %Y')}" for s, e in bw_ranges]
    sel_label  = st.selectbox("Select 2-week period", labels, index=0)
    sel_idx    = labels.index(sel_label)
    bw_s, bw_e = bw_ranges[sel_idx]

    bw_df = df[(df['survey_date'] >= pd.Timestamp(bw_s)) &
               (df['survey_date'] <= pd.Timestamp(bw_e))]

    if bw_df.empty:
        st.markdown('<div class="no-data">No data for this period.</div>', unsafe_allow_html=True)
    else:
        bw_sum = bw_df.groupby('screening_site').agg(
            Eligible=('nicu_eligible1','sum'),
            Consented=('nicu_consent','sum')
        ).reset_index()
        bw_sum['Rate'] = bw_sum.apply(
            lambda r: round(r['Consented'] / r['Eligible'] * 100, 1)
            if r['Eligible'] > 0 else 0.0, axis=1
        )
        tot_e = int(bw_sum['Eligible'].sum())
        tot_c = int(bw_sum['Consented'].sum())
        tot_r = round(tot_c / max(tot_e, 1) * 100, 1)

        render_kpis([
            {"label": "Period Eligible",     "value": str(tot_e), "cls": ""},
            {"label": "Period Consented",    "value": str(tot_c), "cls": "green"},
            {"label": "Period Consent Rate", "value": f"{tot_r}%","cls": "teal"},
        ])

        fig_bw = go.Figure()
        first  = bw_sum.iloc[0]['screening_site'] if len(bw_sum) else None
        for _, row in bw_sum.iterrows():
            c = SITE_COLORS.get(row['screening_site'], '#888')
            is_first = row['screening_site'] == first
            fig_bw.add_trace(go.Bar(
                x=[row['screening_site']], y=[row['Eligible']],
                name='Eligible', marker_color=c, opacity=0.38,
                showlegend=is_first, legendgroup='E',
            ))
            fig_bw.add_trace(go.Bar(
                x=[row['screening_site']], y=[row['Consented']],
                name='Consented', marker_color=c,
                text=f"{row['Rate']:.1f}%", textposition='outside',
                showlegend=is_first, legendgroup='C',
            ))
        fig_bw.update_layout(**plotly_layout(
            barmode='group',
            height=420,
            title=f"NICU Babies: {sel_label}",
            xaxis_title="Screening Site",
            yaxis_title="Babies",
            xaxis=dict(title=dict(standoff=14)),
            yaxis=dict(title=dict(standoff=10)),
            legend=dict(yanchor='top', y=0.98, xanchor='left', x=1.02),
        ))
        fig_bw.update_traces(textfont_color="#0f1f3d", cliponaxis=False)
        st.plotly_chart(fig_bw, use_container_width=True, theme=None)

        st.markdown('<div class="section-title">Period Detail Table</div>', unsafe_allow_html=True)
        bw_detail = bw_sum.rename(columns={
                'screening_site':'Site', 'Rate':'Consent Rate (%)'
            }).set_index('Site')
        download_dataframe('⬇ Download Period Detail', bw_detail, 'biweekly_period_detail_filtered.csv', 'dl_biweekly_detail')
        st.dataframe(
            bw_detail,
            use_container_width=True,
        )

    # All-periods trend
    st.markdown('<div class="section-title">Consent Trend — All Biweekly Periods</div>', unsafe_allow_html=True)
    bw_rows = []
    for bws, bwe in reversed(bw_ranges):
        chunk = df[(df['survey_date'] >= pd.Timestamp(bws)) &
                   (df['survey_date'] <= pd.Timestamp(bwe))]
        if chunk.empty:
            continue
        bw_rows.append({
            'period':    bws.strftime('%Y-%m-%d'),
            'Consented': int(chunk['Consented_Babies'].sum()),
            'Eligible':  int(chunk['Eligible_Babies'].sum()),
        })
    if bw_rows:
        bw_trend = pd.DataFrame(bw_rows)
        fig_bwt  = go.Figure()
        fig_bwt.add_trace(go.Bar(x=bw_trend['period'], y=bw_trend['Eligible'],
                                  name='Eligible', marker_color='#92b4e3'))
        fig_bwt.add_trace(go.Bar(x=bw_trend['period'], y=bw_trend['Consented'],
                                  name='Consented', marker_color='#1e6fd9'))
        fig_bwt.update_layout(**plotly_layout(
            barmode='group',
            height=340,
            xaxis=dict(tickangle=-45, title=dict(standoff=14)),
            xaxis_title="Period Start",
            yaxis_title="Babies",
            yaxis=dict(title=dict(standoff=10)),
        ))
        st.plotly_chart(fig_bwt, use_container_width=True, theme=None)


# ────────────────────────────────────────────────────
# TAB 5 — CUMULATIVE vs EXPECTED
# ────────────────────────────────────────────────────
with tab5:
    st.markdown('<div class="info-banner">📌 Goal: 280 babies over 45 months (Mar 2023 – Dec 2026) at 8 consents/month. Red dashed line = expected pace. Green dotted line = goal.</div>', unsafe_allow_html=True)

    mo_all    = (df.copy().set_index('survey_date')
                   .resample('ME')['Consented_Babies'].sum())
    proj_s    = '2023-03-01'
    proj_e    = '2026-12-31'
    exp_dates = pd.date_range(start=proj_s, end=proj_e, freq='ME')
    exp_vals  = np.arange(8, 8 * len(exp_dates) + 1, 8)
    mo_all    = mo_all.loc[proj_s:proj_e]
    cum_actual = mo_all.cumsum()

    total_to_date    = int(mo_all.sum())
    goal             = 280
    pct_goal         = total_to_date / goal * 100
    months_elapsed   = len(mo_all)
    expected_to_date = min(8 * months_elapsed, goal)
    gap              = total_to_date - expected_to_date

    render_kpis([
        {"label": "Total Consented",      "value": f"{total_to_date:,}", "cls": "green"},
        {"label": "Enrollment Goal",      "value": str(goal),            "cls": ""},
        {"label": "% of Goal Reached",    "value": f"{pct_goal:.1f}%",  "cls": "teal"},
        {"label": "vs Expected Pace",
         "value": f"{gap:+d}",
         "cls": "green" if gap >= 0 else "amber",
         "sub": "ahead of pace" if gap >= 0 else "behind pace"},
    ])

    fig_cum = go.Figure()
    fig_cum.add_trace(go.Bar(
        x=mo_all.index, y=mo_all.values,
        name='Monthly Consented', marker_color='#5b9bd5', opacity=0.75,
    ))
    fig_cum.add_trace(go.Scatter(
        x=cum_actual.index, y=cum_actual.values,
        name='Cumulative Actual', mode='lines+markers',
        line=dict(color='#0b1a36', width=2.5), marker=dict(size=6),
    ))
    fig_cum.add_trace(go.Scatter(
        x=exp_dates, y=exp_vals,
        name='Expected (8/mo)', mode='lines',
        line=dict(color='#e03e3e', width=2, dash='dash'),
    ))
    fig_cum.add_hline(y=goal, line_dash='dot', line_color='#2a9d5c',
                      annotation_text=f"Goal: {goal}",
                      annotation_position="right")
    fig_cum.update_layout(**plotly_layout(
        height=500,
        title='Monthly Consented vs. Cumulative Actual vs. Expected Pace',
        xaxis_title='Month',
        yaxis_title='Babies',
        xaxis=dict(tickangle=-45, tickformat='%Y-%m', title=dict(standoff=14)),
        yaxis=dict(title=dict(standoff=10)),
        legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01),
    ))
    st.plotly_chart(fig_cum, use_container_width=True, theme=None)

    st.markdown('<div class="section-title">Cumulative Consents by Site</div>', unsafe_allow_html=True)
    fig_cs = go.Figure()
    for site in selected_sites:
        sd = (df[df['screening_site'] == site].copy()
              .set_index('survey_date')
              .resample('ME')['Consented_Babies'].sum()
              .loc[proj_s:proj_e]
              .cumsum())
        fig_cs.add_trace(go.Scatter(
            x=sd.index, y=sd.values, name=site,
            mode='lines+markers',
            line=dict(color=SITE_COLORS.get(site,'#888'), width=2.5),
            marker=dict(size=6),
        ))
    fig_cs.update_layout(**plotly_layout(
        height=380,
        xaxis_title='Month',
        yaxis_title='Cumulative Consented',
        xaxis=dict(tickangle=-45, tickformat='%Y-%m', title=dict(standoff=14)),
        yaxis=dict(title=dict(standoff=10)),
        legend_title='Site',
    ))
    st.plotly_chart(fig_cs, use_container_width=True, theme=None)

    st.markdown('<div class="section-title">Monthly Detail Table</div>', unsafe_allow_html=True)
    mo_sp = (df.groupby(['screening_site', pd.Grouper(key='survey_date', freq='ME')])
               ['Consented_Babies'].sum().reset_index())
    mo_sp['mo'] = mo_sp['survey_date'].dt.strftime('%Y-%m')
    pvt_final   = mo_sp.pivot_table(index='mo', columns='screening_site',
                                     values='Consented_Babies', fill_value=0)
    pvt_final['All Sites']  = pvt_final.sum(axis=1)
    pvt_final['Cumulative'] = pvt_final['All Sites'].cumsum()
    download_dataframe('⬇ Download Monthly Detail', pvt_final, 'cumulative_monthly_detail_filtered.csv', 'dl_monthly_detail')
    st.dataframe(pvt_final, use_container_width=True, height=340)


# ────────────────────────────────────────────────────
# TAB 6 — FUNNEL / CONVERSION ANALYSIS
# ────────────────────────────────────────────────────
with tab6:
    st.markdown('<div class="info-banner">📌 Antenatal and NICU screening funnels, where eligible subjects are lost at each stage, and a side-by-side consent-rate comparison between arms.</div>', unsafe_allow_html=True)

    ant_elig_total  = int(df['antscreen_eligible'].sum())
    ant_cons_total  = int(df['antconsent_random'].sum())
    nicu_elig_total = int(df['nicu_eligible1'].sum())
    nicu_cons_total = int(df['nicu_randomized'].sum())

    render_kpis([
        {"label": "Antenatal Eligible",  "value": f"{ant_elig_total:,}",  "cls": ""},
        {"label": "Antenatal Consented", "value": f"{ant_cons_total:,}",  "cls": "green",
         "sub": f"{(ant_cons_total/ant_elig_total*100 if ant_elig_total else 0):.1f}% of eligible"},
        {"label": "NICU Eligible",       "value": f"{nicu_elig_total:,}", "cls": ""},
        {"label": "NICU Consented",      "value": f"{nicu_cons_total:,}", "cls": "teal",
         "sub": f"{(nicu_cons_total/nicu_elig_total*100 if nicu_elig_total else 0):.1f}% of eligible"},
    ])

    # ---- Funnel charts ----
    st.markdown('<div class="section-title">Antenatal vs. NICU Screening Funnels</div>', unsafe_allow_html=True)
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        ant_stages = ['Screened', 'Screen-Eligible', 'Approached', 'Consented / Randomized']
        ant_vals = [
            int(df['antscreen_number'].sum()),
            ant_elig_total,
            int(df['antscreen_approached'].sum()),
            ant_cons_total,
        ]
        fig_fa = go.Figure(go.Funnel(
            y=ant_stages, x=ant_vals,
            marker=dict(color=['#c7dcf5', '#92b4e3', '#1e6fd9', '#0b1a36']),
            textinfo='value+percent initial',
            connector=dict(line=dict(color='#c7d3e6', width=1)),
        ))
        fig_fa.update_layout(**plotly_layout(height=380, title='Antenatal Funnel'))
        st.plotly_chart(fig_fa, use_container_width=True, theme=None)
    with fcol2:
        nicu_stages = ['GA-Screened', 'Eligible', 'Approached', 'Consented / Randomized']
        nicu_vals = [
            int(df['nicu_gascreen'].sum()),
            nicu_elig_total,
            int(df['nicu_approached'].sum()),
            nicu_cons_total,
        ]
        fig_fn = go.Figure(go.Funnel(
            y=nicu_stages, x=nicu_vals,
            marker=dict(color=['#c8ecd6', '#6fc48f', '#2a9d5c', '#0f3d24']),
            textinfo='value+percent initial',
            connector=dict(line=dict(color='#c7d3e6', width=1)),
        ))
        fig_fn.update_layout(**plotly_layout(height=380, title='NICU Funnel'))
        st.plotly_chart(fig_fn, use_container_width=True, theme=None)
    st.caption("Percentages are relative to the first stage of each funnel (100% initial). The two arms use different screening definitions upstream, so compare shape (drop-off between stages), not raw stage-to-stage totals across arms.")

    # ---- Drop-off analysis ----
    st.markdown('<div class="section-title">Drop-off Analysis — Where Eligible Subjects Are Lost</div>', unsafe_allow_html=True)
    dropoff = pd.DataFrame([
        {'Arm': 'Antenatal', 'Reason': 'Not Approached', 'Count': int(df['antscreen_no_approach'].sum())},
        {'Arm': 'Antenatal', 'Reason': 'Declined',        'Count': int(df['antapproach_declined'].sum())},
        {'Arm': 'Antenatal', 'Reason': 'Deferred',        'Count': int(df['antapproach_defer'].sum())},
        {'Arm': 'Antenatal', 'Reason': 'Aged Out',        'Count': int(df['antapproach_agedout'].sum())},
        {'Arm': 'NICU',      'Reason': 'Not Approached',  'Count': int(df['nicu_notapproach'].sum())},
        {'Arm': 'NICU',      'Reason': 'Declined',        'Count': int(df['nicu_decline'].sum())},
        {'Arm': 'NICU',      'Reason': 'Too Late',        'Count': int(df['nicu_toolate'].sum())},
    ])
    dropoff['Eligible Pool'] = dropoff['Arm'].map({'Antenatal': ant_elig_total, 'NICU': nicu_elig_total})
    dropoff['% of Eligible'] = (dropoff['Count'] / dropoff['Eligible Pool'].replace(0, np.nan) * 100).round(1)

    dcol1, dcol2 = st.columns([1.3, 1])
    with dcol1:
        fig_do = px.bar(dropoff, x='Reason', y='Count', color='Arm', barmode='group',
                         color_discrete_map={'Antenatal': '#1e6fd9', 'NICU': '#2a9d5c'}, text='Count')
        fig_do.update_traces(textposition='outside')
        fig_do.update_layout(**plotly_layout(height=380, xaxis_title='Drop-off Reason', yaxis_title='Subjects Lost'))
        fig_do.update_traces(textfont_color="#0f1f3d", cliponaxis=False)
        st.plotly_chart(fig_do, use_container_width=True, theme=None)
    with dcol2:
        disp_do = dropoff.set_index(['Arm', 'Reason'])
        download_dataframe('⬇ Download Drop-off Table', disp_do, 'dropoff_analysis_filtered.csv', 'dl_dropoff')
        st.dataframe(disp_do, use_container_width=True, height=320)

    # ---- Antenatal vs NICU consent-rate comparison ----
    st.markdown('<div class="section-title">Antenatal vs. NICU Consent Rate — Overall & by Site</div>', unsafe_allow_html=True)
    arm_site = df.groupby('screening_site').agg(
        ant_elig=('antscreen_eligible', 'sum'), ant_cons=('antconsent_random', 'sum'),
        nicu_elig=('nicu_eligible1', 'sum'),   nicu_cons=('nicu_randomized', 'sum'),
    ).reset_index()
    arm_site['Antenatal'] = (arm_site['ant_cons']  / arm_site['ant_elig'].replace(0, np.nan)  * 100).round(1)
    arm_site['NICU']      = (arm_site['nicu_cons'] / arm_site['nicu_elig'].replace(0, np.nan) * 100).round(1)
    arm_long = arm_site.melt(id_vars='screening_site', value_vars=['Antenatal', 'NICU'],
                              var_name='Arm', value_name='Rate')

    fig_arm = px.bar(arm_long, x='screening_site', y='Rate', color='Arm', barmode='group', text='Rate',
                      color_discrete_map={'Antenatal': '#1e6fd9', 'NICU': '#2a9d5c'})
    fig_arm.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_arm.update_layout(**plotly_layout(height=380, xaxis_title='Site', yaxis_title='Consent Rate (%)',
                                           legend_title='Arm'))
    fig_arm.update_traces(textfont_color="#0f1f3d", cliponaxis=False)
    st.plotly_chart(fig_arm, use_container_width=True, theme=None)
    st.caption("Blank bars indicate no eligible subjects recorded for that arm at that site in the current filter selection.")


# ────────────────────────────────────────────────────
# TAB 7 — SITE COMPARISON
# ────────────────────────────────────────────────────
with tab7:
    st.markdown('<div class="info-banner">📌 Formal between-site comparison: chi-square test of independence, a binomial GLM giving odds ratios vs. a chosen reference site, decline-reason breakdown, and normalized funnel shape by site.</div>', unsafe_allow_html=True)

    if not HAS_STATS:
        st.warning("This tab needs `statsmodels` and `scipy`. Install with `pip install statsmodels scipy` and restart the app.")
    else:
        site_stats = df.groupby('screening_site').agg(
            Eligible=('Eligible_Babies', 'sum'),
            Consented=('Consented_Babies', 'sum'),
            Screened=('antscreen_number', 'sum'),
            NICU_Declined=('nicu_decline', 'sum'),
            Ant_Declined=('antapproach_declined', 'sum'),
        ).reset_index()
        site_stats['Not Consented'] = (site_stats['Eligible'] - site_stats['Consented']).clip(lower=0)
        site_stats['Consent Rate (%)'] = (site_stats['Consented'] / site_stats['Eligible'].replace(0, np.nan) * 100).round(1)

        # ---- Chi-square test ----
        st.markdown('<div class="section-title">Chi-square Test — Is Consent Independent of Site?</div>', unsafe_allow_html=True)
        ct = site_stats.set_index('screening_site')[['Consented', 'Not Consented']]
        ct = ct[ct.sum(axis=1) > 0]
        if len(ct) < 2:
            st.markdown('<div class="no-data">Need at least 2 sites with eligible subjects in the current filter to run a chi-square test.</div>', unsafe_allow_html=True)
        else:
            try:
                chi2, pval, dof, _ = chi2_contingency(ct)
                render_kpis([
                    {"label": "Chi-square Statistic", "value": f"{chi2:.2f}", "cls": ""},
                    {"label": "Degrees of Freedom",    "value": str(dof),     "cls": ""},
                    {"label": "p-value",               "value": f"{pval:.4g}",
                     "cls": "green" if pval < 0.05 else "amber",
                     "sub": "sites differ significantly" if pval < 0.05 else "no significant difference"},
                ])
                st.caption("H₀: consent outcome (consented vs. not consented) is independent of screening site — tested on the site × outcome contingency table built from the current filter selection.")
            except ValueError as e:
                st.markdown(f'<div class="no-data">Chi-square test not computable on this filter selection (a site or outcome column has zero total): {e}</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1, 1])
        with cl:
            st.markdown('<div class="section-title">Consent Rate, Volume & Declines by Site</div>', unsafe_allow_html=True)
            disp = site_stats.rename(columns={'screening_site': 'Site'}).set_index('Site')
            download_dataframe('⬇ Download Site Comparison Table', disp, 'site_comparison_filtered.csv', 'dl_site_compare')
            st.dataframe(disp, use_container_width=True, height=300)
        with cr:
            st.markdown('<div class="section-title">NICU Decline-Related Losses by Site</div>', unsafe_allow_html=True)
            decl = df.groupby('screening_site').agg(
                Declined=('nicu_decline', 'sum'), Not_Approached=('nicu_notapproach', 'sum'), Too_Late=('nicu_toolate', 'sum')
            ).reset_index().melt(id_vars='screening_site', var_name='Reason', value_name='Count')
            fig_decl = px.bar(decl, x='screening_site', y='Count', color='Reason', barmode='stack')
            fig_decl.update_layout(**plotly_layout(height=300, xaxis_title='Site', yaxis_title='Count', legend_title='Reason'))
            st.plotly_chart(fig_decl, use_container_width=True, theme=None)

        # ---- Binomial GLM ----
        st.markdown('<div class="section-title">Binomial GLM — Odds of Consent by Site</div>', unsafe_allow_html=True)
        ref_site = st.selectbox("Reference site", sorted(selected_sites), index=0, key='glm_ref_site')
        model_df = df[df['Eligible_Babies'] > 0][['screening_site', 'Eligible_Babies', 'Consented_Babies']].copy()
        model_df['NotConsented'] = (model_df['Eligible_Babies'] - model_df['Consented_Babies']).clip(lower=0)
        try:
            glm = smf.glm(
                f'Consented_Babies + NotConsented ~ C(screening_site, Treatment(reference="{ref_site}"))',
                data=model_df, family=sm.families.Binomial()
            ).fit()
            or_table = pd.DataFrame({
                'Term': glm.params.index,
                'Odds Ratio': np.exp(glm.params.values),
                'CI Low': np.exp(glm.conf_int()[0].values),
                'CI High': np.exp(glm.conf_int()[1].values),
                'p-value': glm.pvalues.values,
            })
            or_table['Term'] = or_table['Term'].str.replace(
                r'C\(screening_site.*?\)\[T\.(.*?)\]', r'\1 vs ' + ref_site, regex=True)
            or_table = or_table[or_table['Term'] != 'Intercept'].reset_index(drop=True)

            st.dataframe(or_table.round(4).set_index('Term'), use_container_width=True)
            st.caption(f"Reference site: **{ref_site}**. Odds Ratio > 1 = higher odds of consent than {ref_site}; a 95% CI that excludes 1 is statistically significant at α = 0.05.")

            fig_or = go.Figure()
            fig_or.add_trace(go.Scatter(
                x=or_table['Odds Ratio'], y=or_table['Term'], mode='markers',
                error_x=dict(type='data', symmetric=False,
                              array=or_table['CI High'] - or_table['Odds Ratio'],
                              arrayminus=or_table['Odds Ratio'] - or_table['CI Low']),
                marker=dict(size=11, color='#1e6fd9'),
            ))
            fig_or.add_vline(x=1, line_dash='dash', line_color='#c0392b')
            fig_or.update_layout(**plotly_layout(
                height=320, xaxis_title='Odds Ratio (log scale)', yaxis_title='',
                xaxis=dict(type='log', title=dict(standoff=14)),
            ))
            st.plotly_chart(fig_or, use_container_width=True, theme=None)
        except Exception as e:
            st.warning(f"Model could not be fit on the current filtered data: {e}")

        # ---- Funnel shape comparison ----
        st.markdown('<div class="section-title">NICU Funnel Shape by Site (Normalized to Eligible = 100%)</div>', unsafe_allow_html=True)
        shape = df.groupby('screening_site').agg(
            Eligible=('nicu_eligible1', 'sum'), Approached=('nicu_approached', 'sum'), Consented=('nicu_randomized', 'sum')
        ).reset_index()
        for c in ['Approached', 'Consented']:
            shape[c] = (shape[c] / shape['Eligible'].replace(0, np.nan) * 100).round(1)
        shape['Eligible'] = 100.0
        stage_order = ['Eligible', 'Approached', 'Consented']

        fig_shape = go.Figure()
        for site in selected_sites:
            row = shape[shape['screening_site'] == site]
            if row.empty:
                continue
            ys = [row.iloc[0][s] for s in stage_order]
            fig_shape.add_trace(go.Scatter(
                x=stage_order, y=ys, name=site, mode='lines+markers',
                line=dict(color=SITE_COLORS.get(site, '#888'), width=2.5), marker=dict(size=8),
            ))
        fig_shape.update_layout(**plotly_layout(
            height=380, xaxis_title='NICU Funnel Stage', yaxis_title='% of Eligible Retained', legend_title='Site',
        ))
        st.plotly_chart(fig_shape, use_container_width=True, theme=None)
        st.caption("Uses the NICU funnel (larger, cleaner volumes) as the shape-comparison reference. A site that drops sharply between Eligible and Approached has an approach-capacity gap; a drop between Approached and Consented points to a decline/conversion problem instead.")


# ────────────────────────────────────────────────────
# TAB 8 — TIME TRENDS / FORECASTING
# ────────────────────────────────────────────────────
with tab8:
    st.markdown('<div class="info-banner">📌 Seasonality by ISO week and calendar month, a single-changepoint detector on the monthly trend, and a pace-based forecast to the 280-baby enrollment goal.</div>', unsafe_allow_html=True)

    # ---- Seasonality ----
    st.markdown('<div class="section-title">Seasonality</div>', unsafe_allow_html=True)
    scol1, scol2 = st.columns(2)
    with scol1:
        wk_season = df.groupby('week')['Consented_Babies'].sum().reset_index()
        fig_wks = px.bar(wk_season, x='week', y='Consented_Babies')
        fig_wks.update_traces(marker_color='#1e6fd9')
        fig_wks.update_layout(**plotly_layout(
            height=340, title='Consented by ISO Week-of-Year (All Years Combined)',
            xaxis_title='ISO Week', yaxis_title='Total Consented'))
        st.plotly_chart(fig_wks, use_container_width=True, theme=None)
    with scol2:
        mo_season = df.copy()
        mo_season['month_num']  = mo_season['survey_date'].dt.month
        mo_season['month_name'] = mo_season['survey_date'].dt.strftime('%b')
        mo_agg = (mo_season.groupby(['month_num', 'month_name'])['Consented_Babies']
                  .sum().reset_index().sort_values('month_num'))
        fig_mos = px.bar(mo_agg, x='month_name', y='Consented_Babies')
        fig_mos.update_traces(marker_color='#2a9d5c')
        fig_mos.update_layout(**plotly_layout(
            height=340, title='Consented by Calendar Month (All Years Combined)',
            xaxis_title='Month', yaxis_title='Total Consented'))
        st.plotly_chart(fig_mos, use_container_width=True, theme=None)
    st.caption("These pool every year in the filtered range onto one week/month axis — useful for spotting a recurring seasonal dip (e.g., holidays, summer) rather than a one-time event.")

    # ---- Changepoint detection ----
    st.markdown('<div class="section-title">Changepoint Detection — Monthly Consented Trend</div>', unsafe_allow_html=True)
    cp_scope = st.selectbox("Scope", ["All Sites Combined"] + sorted(selected_sites), index=0, key='cp_scope')
    if cp_scope == "All Sites Combined":
        cp_series = df.set_index('survey_date').resample('ME')['Consented_Babies'].sum()
    else:
        cp_series = (df[df['screening_site'] == cp_scope]
                     .set_index('survey_date').resample('ME')['Consented_Babies'].sum())

    def _single_changepoint(series):
        y = series.values.astype(float)
        n = len(y)
        if n < 8:
            return None, None
        total_ssr = np.sum((y - y.mean()) ** 2)
        best_ssr, best_idx = np.inf, None
        for i in range(3, n - 3):
            left, right = y[:i], y[i:]
            ssr = np.sum((left - left.mean()) ** 2) + np.sum((right - right.mean()) ** 2)
            if ssr < best_ssr:
                best_ssr, best_idx = ssr, i
        r2 = 1 - best_ssr / total_ssr if total_ssr > 0 else 0.0
        return best_idx, r2

    cp_idx, cp_r2 = _single_changepoint(cp_series)
    if cp_idx is None:
        st.markdown('<div class="no-data">Not enough monthly data points for changepoint detection (need 8+ months in the current filter).</div>', unsafe_allow_html=True)
    else:
        cp_y = cp_series.values.astype(float)
        cp_date = cp_series.index[cp_idx]
        mean_before, mean_after = cp_y[:cp_idx].mean(), cp_y[cp_idx:].mean()

        render_kpis([
            {"label": "Detected Changepoint", "value": cp_date.strftime('%b %Y'), "cls": ""},
            {"label": "Mean Before", "value": f"{mean_before:.1f}/mo", "cls": ""},
            {"label": "Mean After",  "value": f"{mean_after:.1f}/mo",
             "cls": "green" if mean_after >= mean_before else "amber"},
            {"label": "Variance Explained", "value": f"{cp_r2 * 100:.1f}%", "cls": "teal",
             "sub": "reasonable evidence" if cp_r2 > 0.3 else "weak evidence"},
        ])

        fig_cp = go.Figure()
        fig_cp.add_trace(go.Bar(x=cp_series.index, y=cp_series.values, name='Monthly Consented', marker_color='#92b4e3'))
        fig_cp.add_trace(go.Scatter(x=cp_series.index[:cp_idx], y=[mean_before] * cp_idx, mode='lines',
                                     name='Mean Before', line=dict(color='#1e6fd9', width=2.5)))
        fig_cp.add_trace(go.Scatter(x=cp_series.index[cp_idx:], y=[mean_after] * (len(cp_series) - cp_idx), mode='lines',
                                     name='Mean After', line=dict(color='#c0392b', width=2.5)))
        # NOTE: add_vline()/add_hline() with annotation_text on a datetime x-axis
        # triggers a known bug in some plotly versions (its auto-annotation-centering
        # code tries to average axis endpoints with plain arithmetic, which fails on
        # datetime values however they're passed in). Building the line + label
        # manually with add_shape()/add_annotation() avoids that code path entirely.
        cp_date_str = cp_date.strftime('%Y-%m-%d')
        fig_cp.add_shape(
            type='line', x0=cp_date_str, x1=cp_date_str, y0=0, y1=1, yref='paper',
            line=dict(color='#0b1a36', width=1.5, dash='dot'),
        )
        fig_cp.add_annotation(
            x=cp_date_str, y=1, yref='paper', yanchor='bottom',
            text='Changepoint', showarrow=False,
            font=dict(color='#0b1a36', size=11),
        )
        fig_cp.update_layout(**plotly_layout(height=380, xaxis_title='Month', yaxis_title='Consented'))
        st.plotly_chart(fig_cp, use_container_width=True, theme=None)
        st.caption("Single-changepoint least-squares method: finds the split point that minimizes combined within-segment variance (equivalent to a two-piece constant-mean model fit by OLS). 'Variance explained' is the % reduction in total sum-of-squares from splitting at that point — treat values under ~20% as weak evidence of a real shift rather than noise.")

    # ---- Forecast to goal ----
    st.markdown('<div class="section-title">Enrollment Pace Forecast to Goal</div>', unsafe_allow_html=True)
    goal_fc = 280
    weekly_all = df.set_index('survey_date').resample('W-MON')['Consented_Babies'].sum()
    total_so_far = int(df['Consented_Babies'].sum())
    remaining = max(goal_fc - total_so_far, 0)
    last_date = df['survey_date'].max()

    if remaining <= 0:
        st.success(f"Goal of {goal_fc} already reached ({total_so_far} consented in the current filter).")
    elif len(weekly_all) < 2:
        st.markdown('<div class="no-data">Not enough weekly data in the current filter to forecast a pace.</div>', unsafe_allow_html=True)
    else:
        pace_window = st.slider("Recent pace window (weeks)", min_value=4,
                                 max_value=min(52, len(weekly_all)), value=min(12, len(weekly_all)),
                                 step=4, key='pace_window')
        recent_pace  = weekly_all.tail(pace_window).mean()
        overall_pace = weekly_all.mean()

        def _project(pace):
            if pace <= 0:
                return None
            wk = remaining / pace
            return last_date + pd.Timedelta(weeks=wk), wk

        proj_recent, proj_overall = _project(recent_pace), _project(overall_pace)

        render_kpis([
            {"label": "Total Consented to Date", "value": f"{total_so_far:,}", "cls": "green"},
            {"label": "Remaining to Goal", "value": f"{remaining:,}", "cls": ""},
            {"label": f"Recent Pace ({pace_window}-wk avg)", "value": f"{recent_pace:.2f}/wk", "cls": "teal"},
            {"label": "Projected Completion (Recent Pace)",
             "value": proj_recent[0].strftime('%b %Y') if proj_recent else "pace ≤ 0",
             "cls": "amber"},
        ])

        if proj_recent and proj_overall:
            st.markdown(f"""
            <div style='font-size:0.85rem; color:#3a4a6a; margin-bottom:1rem; line-height:1.6;'>
            At the <b>recent {pace_window}-week pace</b> ({recent_pace:.2f} consents/week), the goal is projected
            around <b>{proj_recent[0].strftime('%B %Y')}</b> (~{proj_recent[1]:.0f} weeks from the last report).<br>
            At the <b>overall study-to-date pace</b> ({overall_pace:.2f} consents/week), projected around
            <b>{proj_overall[0].strftime('%B %Y')}</b> (~{proj_overall[1]:.0f} weeks from the last report).
            </div>
            """, unsafe_allow_html=True)

        # Linear trend projection on cumulative consents
        t_idx = np.arange(len(weekly_all))
        cum_vals = weekly_all.cumsum().values
        if len(t_idx) >= 4:
            slope, intercept = np.polyfit(t_idx, cum_vals, 1)
            n_future = 160
            future_t = np.arange(len(t_idx), len(t_idx) + n_future)
            future_cum = slope * future_t + intercept
            future_dates = [weekly_all.index[-1] + pd.Timedelta(weeks=int(i - len(t_idx) + 1)) for i in future_t]

            fig_fc = go.Figure()
            fig_fc.add_trace(go.Scatter(x=weekly_all.index, y=cum_vals, name='Actual Cumulative', mode='lines+markers',
                                         line=dict(color='#0b1a36', width=2.5)))
            fig_fc.add_trace(go.Scatter(x=future_dates, y=future_cum, name='Linear Trend Projection', mode='lines',
                                         line=dict(color='#e03e3e', width=2, dash='dash')))
            fig_fc.add_hline(y=goal_fc, line_dash='dot', line_color='#2a9d5c',
                              annotation_text=f'Goal: {goal_fc}', annotation_position='right')
            fig_fc.update_layout(**plotly_layout(
                height=420, title='Cumulative Enrollment — Linear Trend Projection',
                xaxis_title='Week', yaxis_title='Cumulative Consented'))
            st.plotly_chart(fig_fc, use_container_width=True, theme=None)

            if slope > 0:
                t_goal = (goal_fc - intercept) / slope
                weeks_from_last = max(t_goal - t_idx[-1], 0)
                proj_lin_date = weekly_all.index[-1] + pd.Timedelta(weeks=weeks_from_last)
                st.caption(f"Linear trend fit across the full filtered study period (slope ≈ {slope:.3f} consents/week): projected goal date ≈ **{proj_lin_date.strftime('%B %Y')}**. This smooths over the entire history rather than weighting recent pace, so compare it against the recent-pace estimate above — a large gap between the two suggests enrollment speed has been changing.")
            else:
                st.caption("The linear trend across the full filtered period is flat or declining, so a trend-based goal date isn't meaningful here — rely on the recent-pace estimates above instead.")


# ────────────────────────────────────────────────────
# TAB 9 — STATISTICAL MODELING
# ────────────────────────────────────────────────────
with tab9:
    st.markdown('<div class="info-banner">📌 Regression models fit on the current filter: a logistic model of consent probability, a Poisson/negative-binomial model of weekly consent counts, and a bootstrap time-to-goal projection.</div>', unsafe_allow_html=True)

    if not HAS_STATS:
        st.warning("This tab needs `statsmodels` and `scipy`. Install with `pip install statsmodels scipy` and restart the app.")
    else:
        t0 = df['survey_date'].min()
        df_t = df.copy()
        df_t['t_weeks'] = ((df_t['survey_date'] - t0).dt.days / 7).round().astype(int)
        # Reference site for the models below: first selected site alphabetically, so
        # the model still fits when the sidebar filter excludes WCM entirely.
        t9_ref_site = sorted(selected_sites)[0] if selected_sites else df_t['screening_site'].iloc[0]

        # ---- Logistic regression: site + time + arm + eligible count ----
        st.markdown('<div class="section-title">Logistic Regression — Probability of Consent</div>', unsafe_allow_html=True)
        ant_long = df_t[['screening_site', 't_weeks', 'antscreen_eligible', 'antconsent_random']].rename(
            columns={'antscreen_eligible': 'Eligible', 'antconsent_random': 'Consented'})
        ant_long['arm'] = 'Antenatal'
        nicu_long = df_t[['screening_site', 't_weeks', 'nicu_eligible1', 'nicu_randomized']].rename(
            columns={'nicu_eligible1': 'Eligible', 'nicu_randomized': 'Consented'})
        nicu_long['arm'] = 'NICU'
        long_df = pd.concat([ant_long, nicu_long], ignore_index=True)
        long_df = long_df[long_df['Eligible'] > 0].copy()
        long_df['NotConsented'] = (long_df['Eligible'] - long_df['Consented']).clip(lower=0)

        try:
            logit = smf.glm(
                'Consented + NotConsented ~ t_weeks + Eligible + '
                f'C(arm, Treatment(reference="NICU")) + C(screening_site, Treatment(reference="{t9_ref_site}"))',
                data=long_df, family=sm.families.Binomial()
            ).fit()
            lt = pd.DataFrame({
                'Term': logit.params.index,
                'Odds Ratio': np.exp(logit.params.values),
                'CI Low': np.exp(logit.conf_int()[0].values),
                'CI High': np.exp(logit.conf_int()[1].values),
                'p-value': logit.pvalues.values,
            })
            lt['Term'] = (lt['Term']
                          .str.replace(r'C\(arm.*?\)\[T\.(.*?)\]', r'\1 vs NICU', regex=True)
                          .str.replace(r'C\(screening_site.*?\)\[T\.(.*?)\]', r'\1 vs ' + t9_ref_site, regex=True)
                          .str.replace('t_weeks', 'Calendar time (+1 wk)', regex=False)
                          .str.replace('Eligible', 'Weekly eligible count (+1)', regex=False))
            lt = lt[lt['Term'] != 'Intercept'].reset_index(drop=True)
            st.dataframe(lt.round(4).set_index('Term'), use_container_width=True)
            st.caption(f"Binomial GLM (logit link), pooled across antenatal and NICU arms with an arm indicator, reference site {t9_ref_site}. OR > 1 = higher odds of consent; a 95% CI excluding 1 is significant at α = 0.05.")
        except Exception as e:
            st.warning(f"Logistic model could not be fit on the current filtered data: {e}")

        st.markdown("---")

        # ---- Poisson / Negative Binomial ----
        st.markdown('<div class="section-title">Weekly Consent Counts — Poisson vs. Negative Binomial</div>', unsafe_allow_html=True)
        count_df = df_t[['screening_site', 't_weeks', 'Consented_Babies']].copy()
        try:
            pois = smf.glm(f'Consented_Babies ~ t_weeks + C(screening_site, Treatment(reference="{t9_ref_site}"))',
                            data=count_df, family=sm.families.Poisson()).fit()
            disp_ratio = pois.deviance / pois.df_resid if pois.df_resid > 0 else np.nan

            render_kpis([
                {"label": "Poisson Deviance / df", "value": f"{disp_ratio:.2f}",
                 "cls": "amber" if disp_ratio > 1.5 else "green",
                 "sub": "overdispersed → switching to NB" if disp_ratio > 1.5 else "Poisson assumption OK (≈1)"},
            ])

            use_model, model_name = pois, "Poisson"
            if disp_ratio > 1.5:
                nb = smf.negativebinomial(
                    f'Consented_Babies ~ t_weeks + C(screening_site, Treatment(reference="{t9_ref_site}"))',
                    data=count_df).fit(disp=0)
                use_model, model_name = nb, "Negative Binomial (MLE-estimated dispersion α)"

            irr_t = pd.DataFrame({
                'Term': use_model.params.index,
                'IRR': np.exp(use_model.params.values),
                'CI Low': np.exp(use_model.conf_int()[0].values),
                'CI High': np.exp(use_model.conf_int()[1].values),
                'p-value': use_model.pvalues.values,
            })
            irr_t = irr_t[~irr_t['Term'].isin(['Intercept', 'alpha'])].copy()
            irr_t['Term'] = (irr_t['Term']
                             .str.replace(r'C\(screening_site.*?\)\[T\.(.*?)\]', r'\1 vs ' + t9_ref_site, regex=True)
                             .str.replace('t_weeks', 'Calendar time (+1 wk)', regex=False))
            st.markdown(f"**Model used: {model_name}** — incidence rate ratios (IRR) for weekly consented-baby counts.")
            st.dataframe(irr_t.round(4).set_index('Term'), use_container_width=True)
            st.caption(f"IRR > 1 = higher weekly consent rate than the reference ({t9_ref_site}). Poisson assumes mean = variance; a deviance/df ratio well above 1 signals overdispersion, in which case the model automatically switches to negative binomial, which estimates an extra dispersion parameter α.")
        except Exception as e:
            st.warning(f"Count model could not be fit on the current filtered data: {e}")

        st.markdown("---")

        # ---- Bootstrap time-to-goal ----
        st.markdown('<div class="section-title">Time-to-Goal Projection (Bootstrap)</div>', unsafe_allow_html=True)
        goal_tt = 280
        total_tt = int(df['Consented_Babies'].sum())
        remaining_tt = max(goal_tt - total_tt, 0)
        weekly_tt = df.set_index('survey_date').resample('W-MON')['Consented_Babies'].sum()

        if remaining_tt <= 0:
            st.success(f"Goal of {goal_tt} already reached ({total_tt} consented in the current filter).")
        elif len(weekly_tt) < 8:
            st.markdown('<div class="no-data">Not enough weekly data in the current filter for a bootstrap projection.</div>', unsafe_allow_html=True)
        else:
            boot_window = st.slider("Bootstrap pool: recent N weeks", min_value=8,
                                     max_value=min(104, len(weekly_tt)), value=min(26, len(weekly_tt)),
                                     step=2, key='boot_window')
            pool = weekly_tt.tail(boot_window).values

            if pool.sum() == 0:
                st.markdown('<div class="no-data">No consents in the selected recent window — cannot project a completion date from zero pace.</div>', unsafe_allow_html=True)
            else:
                rng = np.random.default_rng(42)
                n_boot, max_weeks = 2000, 500
                draws = rng.choice(pool, size=(n_boot, max_weeks), replace=True)
                cum_draws = np.cumsum(draws, axis=1)
                reached = cum_draws >= remaining_tt
                weeks_needed = np.where(reached.any(axis=1), reached.argmax(axis=1) + 1, max_weeks)

                med_wk = int(np.median(weeks_needed))
                lo_wk, hi_wk = np.percentile(weeks_needed, [5, 95])
                last_dt = df['survey_date'].max()
                med_date = last_dt + pd.Timedelta(weeks=med_wk)
                lo_date  = last_dt + pd.Timedelta(weeks=lo_wk)
                hi_date  = last_dt + pd.Timedelta(weeks=hi_wk)

                render_kpis([
                    {"label": "Remaining to Goal", "value": str(remaining_tt), "cls": ""},
                    {"label": "Median Projected Completion", "value": med_date.strftime('%b %Y'), "cls": "teal"},
                    {"label": "90% Interval", "value": f"{lo_date.strftime('%b %Y')} – {hi_date.strftime('%b %Y')}", "cls": "amber"},
                ])
                st.caption(f"Bootstrap resampling ({n_boot:,} draws) from the most recent {boot_window} weeks of consent counts, simulating cumulative enrollment forward until the goal is reached. Median and 90% interval reflect week-to-week variability in that recent pace — a nonparametric empirical projection, appropriate for small, discrete weekly counts where a normal approximation would be unreliable.")

                fig_boot = px.histogram(weeks_needed, nbins=40)
                fig_boot.update_traces(marker_color='#1a8fa0')
                fig_boot.update_layout(**plotly_layout(
                    height=320, xaxis_title='Weeks to Goal (bootstrap draws)', yaxis_title='Frequency', showlegend=False))
                st.plotly_chart(fig_boot, use_container_width=True, theme=None)


# ────────────────────────────────────────────────────
# TAB 10 — DATA QUALITY / OPERATIONAL
# ────────────────────────────────────────────────────
with tab10:
    st.markdown('<div class="info-banner">📌 Weekly reporting completeness by site (unfiltered — reflects the full uploaded file), duplicate-report checks, common themes in consent notes, and trends in timing-related losses (aged-out / too-late).</div>', unsafe_allow_html=True)

    # ---- Weekly reporting completeness ----
    st.markdown('<div class="section-title">Weekly Reporting Completeness by Site</div>', unsafe_allow_html=True)
    overall_min, overall_max = raw_data['survey_date'].min(), raw_data['survey_date'].max()
    full_grid = pd.date_range(overall_min, overall_max, freq='W-MON')
    rows = []
    for site in sorted(s for s in raw_data['screening_site'].unique() if s != 'Unknown'):
        sd = raw_data[raw_data['screening_site'] == site]
        present = set(sd['survey_date'].dt.normalize())
        n_missing = sum(1 for d in full_grid if d not in present)
        rows.append({
            'Site': site, 'Expected Weeks': len(full_grid), 'Reported Weeks': len(present),
            'Missing Weeks': n_missing, '% Complete': round(len(present) / len(full_grid) * 100, 1),
        })
    complete_df = pd.DataFrame(rows).set_index('Site')

    ccol1, ccol2 = st.columns([1, 1.2])
    with ccol1:
        download_dataframe('⬇ Download Completeness Table', complete_df, 'reporting_completeness.csv', 'dl_completeness')
        st.dataframe(complete_df, use_container_width=True, height=230)
    with ccol2:
        fig_comp = px.bar(complete_df.reset_index(), x='Site', y='% Complete', color='Site',
                           color_discrete_map=SITE_COLORS, text='% Complete')
        fig_comp.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_comp.add_hline(y=100, line_dash='dot', line_color='#2a9d5c')
        fig_comp.update_layout(**plotly_layout(
            height=280, showlegend=False, yaxis=dict(range=[0, 110]), xaxis_title='', yaxis_title='% of Expected Weeks Reported'))
        fig_comp.update_traces(textfont_color="#0f1f3d", cliponaxis=False)
        st.plotly_chart(fig_comp, use_container_width=True, theme=None)
    st.caption("Based on the full cleaned file (not the sidebar site/date filters) — this is a reporting-compliance check, and filtering the date range would create artificial 'missing weeks' at the edges.")

    # ---- Duplicate weekly reports ----
    dupe_check = raw_data.groupby(['screening_site', 'survey_date']).size().reset_index(name='n_reports')
    dupes = dupe_check[dupe_check['n_reports'] > 1]
    if len(dupes):
        st.markdown(f'<div class="no-data">⚠️ {len(dupes)} site-week combination(s) have more than one report on file — possible duplicate entry worth checking in REDCap:</div>', unsafe_allow_html=True)
        st.dataframe(
            dupes.rename(columns={'screening_site': 'Site', 'survey_date': 'Survey Date', 'n_reports': '# Reports'}).set_index('Site'),
            use_container_width=True)
    else:
        st.markdown("""
        <div class="audit-card" style="padding:0.9rem 1.3rem; margin-bottom:0;">
            <ul class="audit-step-list"><li><span class="tick">✓</span> No duplicate site-week reports detected.</li></ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ---- Consent notes — common themes ----
    st.markdown('<div class="section-title">Consent Notes — Common Themes</div>', unsafe_allow_html=True)
    notes = df['consent_notes'].dropna().astype(str)
    if notes.empty:
        st.markdown('<div class="no-data">No consent notes in the current filter selection.</div>', unsafe_allow_html=True)
    else:
        STOPWORDS = set("""the a an and or of to in on for with at by from as is was were be been being
        this that these those it its our their his her they he she we you your not no yes patient family
        mom mother dad father will did does do has have had all if than then so re per""".split())
        tokens = []
        for n in notes:
            words = re.findall(r"[a-zA-Z']+", n.lower())
            tokens.extend([w for w in words if w not in STOPWORDS and len(w) > 2])
        counts = Counter(tokens)
        top_words = pd.DataFrame(counts.most_common(20), columns=['Word', 'Count'])

        ncol1, ncol2 = st.columns([1, 1.3])
        with ncol1:
            fig_words = px.bar(top_words.sort_values('Count'), x='Count', y='Word', orientation='h')
            fig_words.update_traces(marker_color='#1e6fd9')
            fig_words.update_layout(**plotly_layout(height=460, xaxis_title='Occurrences', yaxis_title=''))
            st.plotly_chart(fig_words, use_container_width=True, theme=None)
        with ncol2:
            st.markdown(f"**{len(notes)} notes** in the current filter selection.")
            search_term = st.text_input("Search notes for a keyword", key='notes_search')
            note_disp = df.loc[df['consent_notes'].notna(), ['survey_date', 'screening_site', 'consent_notes']].rename(
                columns={'survey_date': 'Date', 'screening_site': 'Site', 'consent_notes': 'Note'})
            if search_term:
                note_disp = note_disp[note_disp['Note'].str.contains(search_term, case=False, na=False)]
            download_dataframe('⬇ Download Consent Notes', note_disp, 'consent_notes_filtered.csv', 'dl_notes')
            st.dataframe(note_disp.set_index('Date'), use_container_width=True, height=380)
        st.caption("Word list excludes common English stopwords and is built only from free-text notes — not a validated NLP classification, but useful for spotting recurring operational themes (e.g., 'discharged', 'window', 'declined').")

    st.markdown("---")

    # ---- Timing-related losses ----
    st.markdown('<div class="section-title">Timing-Related Losses — Aged Out (Antenatal) & Too Late (NICU)</div>', unsafe_allow_html=True)
    tl_by_site = df.groupby('screening_site')[['antapproach_agedout', 'nicu_toolate']].sum().reset_index()
    tl_by_site.columns = ['Site', 'Aged Out (Antenatal)', 'Too Late (NICU)']

    tcol1, tcol2 = st.columns([1, 1.3])
    with tcol1:
        download_dataframe('⬇ Download Timing-Loss Table', tl_by_site.set_index('Site'), 'timing_losses_by_site.csv', 'dl_timing')
        st.dataframe(tl_by_site.set_index('Site'), use_container_width=True, height=230)
    with tcol2:
        tl_long = tl_by_site.melt(id_vars='Site', var_name='Reason', value_name='Count')
        fig_tl = px.bar(tl_long, x='Site', y='Count', color='Reason', barmode='group',
                         color_discrete_map={'Aged Out (Antenatal)': '#e09c2a', 'Too Late (NICU)': '#c0392b'})
        fig_tl.update_layout(**plotly_layout(height=280, xaxis_title='', yaxis_title='Count', legend_title='Reason'))
        st.plotly_chart(fig_tl, use_container_width=True, theme=None)

    tl_trend = df.groupby(pd.Grouper(key='survey_date', freq='ME'))[['antapproach_agedout', 'nicu_toolate']].sum().reset_index()
    fig_tlt = go.Figure()
    fig_tlt.add_trace(go.Scatter(x=tl_trend['survey_date'], y=tl_trend['antapproach_agedout'], name='Aged Out (Antenatal)',
                                  mode='lines+markers', line=dict(color='#e09c2a', width=2.5)))
    fig_tlt.add_trace(go.Scatter(x=tl_trend['survey_date'], y=tl_trend['nicu_toolate'], name='Too Late (NICU)',
                                  mode='lines+markers', line=dict(color='#c0392b', width=2.5)))
    fig_tlt.update_layout(**plotly_layout(height=340, title='Monthly Trend', xaxis_title='Month', yaxis_title='Count'))
    st.plotly_chart(fig_tlt, use_container_width=True, theme=None)
    st.caption("Aged-out and too-late cases reflect timing/logistics gaps (missed enrollment windows) rather than family refusal — a persistently high or rising count at a site may point to staffing or workflow issues worth investigating operationally, rather than a consent/messaging problem.")
