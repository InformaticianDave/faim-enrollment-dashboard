# FAIM Enrollment Dashboard

**Author:** David Liu, M.S.
Family Attitudes and Infant Management (FAIM) — Multi-Site NICU Enrollment Tracker

A Streamlit dashboard that turns the weekly FAIM REDCap screening/consent export into a
cleaned dataset, 10 analysis tabs, and downloadable summary tables — for WCM, UTHSA, Yale,
UCLA, and NW/Lurie.

---

## 1. Getting the raw data out of REDCap

1. Log into **REDCap**
2. Open **FAIM Enrollment Weekly Survey**
3. **Applications → Data Exports, Reports, and Stats**
4. Select **All data**
5. **Export Data**
6. Choose **CSV / Microsoft Excel (raw data)**
7. **Export Data** — save the file (it will look like `FAIMEnrollmentWeekly_DATA_YYYY-MM-DD_HHMM.csv`)

This raw file is what you upload into the app. Do not pre-clean it — the app does that for you.

---

## 2. Install & run

```bash
pip install -r requirements.txt
streamlit run faim_app_readable.py
```

Requires Python 3.10+. See [`requirements.txt`](requirements.txt) for exact package versions.

No real data ships in this repo. [`sample_data/FAIMEnrollmentWeekly_SAMPLE.csv`](sample_data/FAIMEnrollmentWeekly_SAMPLE.csv)
is a fully synthetic file (fabricated numbers, same column schema as a real REDCap export) —
upload it to try the app with zero setup.

---

## 3. What happens when you upload a file

The app runs a five-step cleaning pipeline immediately on upload:

1. **Removes test/staff rows** — drops any row containing one of the known internal/staff email addresses
2. **Fills nulls → 0** across all enrollment count columns
3. **Casts those columns to integer**
4. **Parses `survey_date`** and maps numeric site codes → site names (WCM, UTHSA, Yale, UCLA, NW/Lurie)
5. **Derives** `Consented_Babies`, `Eligible_Babies`, `week`, `year`, `year_month`

A **Cleaning Audit Panel** shows exactly what happened: rows removed, nulls filled, columns cast,
sites detected — plus a warning (not a crash) if an expected column is missing from your export.

A **Download Cleaned CSV** button lets you save the cleaned output (named
`FAIM_cleaned_MM-DD-YYYY.csv`) for use elsewhere, e.g. in R or a parameterized report.

---

## 4. Sidebar controls

- **File uploader** — drag and drop the raw REDCap CSV
- **Screening Sites** — multi-select filter
- **Date Range** — restricts every tab to a window
- **Reset Filters** button
- **Definitions** — what "Eligible," "Consented," and "Consent Rate" mean
- **Download Filtered Data**

---

## 5. The 10 tabs

| Tab | What it shows |
|---|---|
| **📊 Overview** | KPI cards, eligible-vs-consented by site, consent rate by site, summary table |
| **📅 Weekly Summary** | Grouped/stacked/line view by week, year-week pivot table |
| **📆 Monthly Enrollment** | Monthly trend line, heatmap, enrollment+eligibility bars, pivot table |
| **🗓 Biweekly Periods** | Any 2-week block, per-site bars with consent % annotated, full trend sparkline |
| **📈 Cumulative vs Expected** | Actual vs. 8/month pace goal, ahead/behind KPI, per-site cumulative lines |
| **🔻 Funnel Analysis** | Antenatal & NICU screening funnels, drop-off by reason, antenatal-vs-NICU consent rate |
| **🏢 Site Comparison** | Chi-square test of consent-by-site, binomial GLM odds ratios, decline breakdown |
| **📉 Time Trends** | ISO-week/month seasonality, single-changepoint detector, pace-based goal forecast |
| **🧮 Statistical Models** | Pooled logistic regression, Poisson/negative-binomial weekly count model, bootstrap time-to-goal |
| **🔍 Data Quality** | Weekly reporting completeness by site, duplicate-report detection, consent-note themes, timing-loss trends |

The **Site Comparison** and **Statistical Models** tabs need `statsmodels` and `scipy`
(both in `requirements.txt`). If either package is missing, those two tabs show a plain
warning instead of crashing the app — everything else keeps working.

### Definitions

- **Eligible** — subjects who met screening criteria for either the antenatal or NICU arm
- **Consented** — subjects (or guardians) who agreed to enrollment and were randomized
- **Consent Rate** — Consented ÷ Eligible, expressed as a percentage

---

## 6. Data handling / privacy

- The app reads the uploaded file **in memory only** for the life of the session — nothing is
  written to disk or sent anywhere outside your machine.
- The first cleaning step strips rows tied to known internal/staff test email addresses.
- **No real participant data is committed to this repository.** `.gitignore` excludes every
  `*.csv` except the synthetic file under `sample_data/`.
- If you fork or share this repo, do not commit a real REDCap export or a cleaned output file.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `SyntaxError: expected 'except' or 'finally' block` | The file's indentation was altered by copy/paste into an editor. Re-download the file from source control instead of hand-editing it. |
| Blank tabs / "no data" after upload | Check the Cleaning Audit Panel for a missing-column warning — your export may be missing an expected REDCap field. |
| `TypeError` from a Plotly chart mentioning `add_vline`/`_mean` | Known Plotly/pandas version incompatibility on some installs; this repo's `faim_app_readable.py` already works around it. If you still see it, update plotly (`pip install -U plotly`). |
| `pip install` itself fails with a `pip._vendor` error | Your local `pip` install is corrupted, unrelated to this app. Run `python -m ensurepip --upgrade` then `python -m pip install --upgrade pip setuptools wheel`, and retry. |

---

## 8. Project layout

```
faim-enrollment-dashboard/
├── faim_app_readable.py        # the Streamlit app
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── .gitignore
└── sample_data/
    └── FAIMEnrollmentWeekly_SAMPLE.csv   # synthetic test data, no real PHI
```

## 9. Maintenance notes

- Site-code → site-name mapping and the staff/test email list live near the top of
  `faim_app_readable.py` in `SITE_MAPPING` and the cleaning pipeline's email list — update
  those if a site is added or an internal test account changes.
- The 280-baby / 8-per-month enrollment goal used in the forecasting tabs is hardcoded;
  update it in the **Cumulative vs Expected**, **Time Trends**, and **Statistical Models**
  tabs if the study's target changes.
