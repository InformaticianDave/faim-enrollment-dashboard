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
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊  Overview",
    "📅  Weekly Summary",
    "📆  Monthly Enrollment",
    "🗓  Biweekly Periods",
    "📈  Cumulative vs Expected",
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
