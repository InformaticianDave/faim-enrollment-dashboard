# Changelog

All notable changes to the FAIM Enrollment Dashboard, newest first.

## [Unreleased]
- Repository created from the project's development history: code, docs, `.gitignore`,
  and synthetic sample data.

## 2026-10-07
### Fixed
- Collapsed the optional `statsmodels`/`scipy` import into a single indented line inside
  its `try:` block, to be more resilient to copy/paste-induced indentation loss in editors
  that don't preserve leading whitespace.

## 2026-09-23
### Added
- Five new analysis tabs on top of the original five:
  - **Funnel Analysis** — antenatal & NICU screening funnels, drop-off-by-reason breakdown,
    antenatal-vs-NICU consent rate comparison
  - **Site Comparison** — chi-square test of consent independence by site, binomial GLM
    odds ratios vs. a selectable reference site, decline-reason breakdown, normalized
    funnel shape by site
  - **Time Trends** — ISO-week/calendar-month seasonality, single-changepoint detector,
    pace-based forecast to the enrollment goal
  - **Statistical Models** — pooled logistic regression (site + time + arm + eligible count),
    Poisson/negative-binomial model for weekly counts with automatic overdispersion handling,
    bootstrap-based time-to-goal projection with a 90% interval
  - **Data Quality** — weekly reporting completeness by site, duplicate-report detection,
    consent-note keyword themes, aged-out/too-late timing-loss trends
- `statsmodels` and `scipy` as new dependencies for the statistical tabs; both tabs degrade
  to a plain warning (not a crash) if either package is missing.

### Fixed
- Extended the enrollment goal projection window from March 2026 to December 2026
  (`proj_e`), and the banner text that stated the goal timeline, to match the study's
  revised 45-month enrollment window.
- Fixed a `TypeError` in the Time Trends tab's changepoint marker: `add_vline()` with
  `annotation_text` on a datetime x-axis hits a broken auto-annotation-centering code path
  in some Plotly versions. Replaced it with a manual `add_shape()` + `add_annotation()`
  call, which bypasses that code path entirely.
- Fixed a latent bug where the Statistical Models tab's regressions hardcoded `"WCM"` as
  the reference site, silently failing whenever a sidebar filter excluded WCM. The
  reference site is now chosen dynamically from whatever sites are currently selected.
- Hardened the Site Comparison tab's chi-square test against a `ValueError` that occurs
  when a filtered subset has a site or outcome column that sums to zero.

## Earlier (pre-2026-09-23)
### Added
- Initial Streamlit app: sidebar (file uploader, site filter, date range picker), and five
  tabs — Overview, Weekly Summary, Monthly Enrollment, Biweekly Periods, Cumulative vs
  Expected.
- Explicit data-cleaning pipeline ported from the original R Markdown / `reticulate`
  workflow: removes known staff/test email rows, fills and casts the 24 enrollment count
  columns, parses dates, maps site codes to names, derives `Consented_Babies`,
  `Eligible_Babies`, `week`, `year`, `year_month`.
- Cleaning Audit Panel showing rows removed, nulls filled, columns cast, and sites
  detected, plus a non-fatal warning for any missing expected column.
- Downloadable cleaned CSV (`FAIM_cleaned_MM-DD-YYYY.csv`), in the sidebar and above the
  tabs.

### Fixed
- A `TypeError: update_layout() got multiple values for keyword argument 'xaxis'` crash
  across every tab, caused by passing `xaxis=` directly into `update_layout()` while a
  shared layout helper was already supplying `xaxis` settings.
- Washed-out, unreadable chart axis labels, tick labels, and legends across all five tabs —
  rebuilt the shared Plotly layout helper with explicit high-contrast theme, tick font,
  legend font, margins, and line colors, and disabled Streamlit's own chart theming
  override so it couldn't wash the colors back out.

### Added
- "FAIM Enrollment Dashboard — Author: David Liu, M.S." page header.
- Reset Filters button, a Definitions help box (Eligible / Consented / Consent Rate), and
  download buttons for each tab's filtered summary table (Site Summary, Weekly Pivot,
  Monthly Pivot, Biweekly Period Detail, Monthly Detail).
