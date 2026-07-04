# Project Brief

## Working Title

Audit Risk Radar: DART-based Financial Statement Risk Screening with Explainable Anomaly Detection

## Core Question

How can public financial statement data be used to support digital audit planning and early risk identification?

## Project Thesis

Public disclosures cannot prove fraud by themselves, but they can reveal accounting patterns that deserve closer audit attention. A digital audit workflow should therefore combine accounting theory, peer benchmarking, machine learning, and explainable visualization.

## Why Beneish-Style M-Score Is Still Useful

Beneish-style indicators are older than recent AI methods, but they remain useful as a baseline because they are:

- Calculable from public financial statements
- Grounded in accounting logic
- Easy to explain to non-technical stakeholders
- Suitable for first-pass red-flag screening

The project does not use M-Score as a final fraud detector. It uses M-Score as an interpretable starting point.

## Why Add Modern Techniques

Modern audit analytics increasingly focuses on full-population analysis, anomaly detection, and continuous risk monitoring. Public financial statements are limited compared with internal journal-entry data, but they can still support:

- Historical trend analysis
- Peer-group comparison
- Multivariate anomaly detection
- Explainable risk ranking

The machine learning layer is designed to identify patterns that a single formula may miss.

## Target Output

The final project should include:

- GitHub repository
- Reproducible sample data
- Python analysis pipeline
- Streamlit dashboard
- Clear README
- Backtesting case study
- Interview-ready methodology explanation

## First Expansion Scope

The first expansion should move beyond the original 350-statement experiment into panel data:

- 2019-2024 public financial statements
- Up to 500 KOSPI/KOSDAQ-listed companies
- Company-year level risk scoring
- Peer comparison across the same year and industry where industry metadata is available

This scale is large enough to make anomaly detection and peer benchmarking more meaningful, while still small enough to manage DART API limits, account mapping issues, and missing data.

## Interview Narrative

1. I started from a prior project that calculated Beneish-style M-Score from DART financial statements.
2. I recognized that a single formula is interpretable but limited.
3. I redesigned the project as a broader digital audit risk-screening workflow.
4. I added peer-group comparison to reflect industry context.
5. I added unsupervised anomaly detection because labeled fraud data is scarce.
6. I focused on explainability because audit conclusions require professional judgment and documentation.
7. The final insight is that AI should not replace auditors, but should help auditors ask better questions earlier.

## Audit Value

The project can help auditors:

- Prioritize risky companies before detailed testing
- Compare companies consistently across years and industries
- Detect unusual changes in accruals, receivables, margins, growth, and leverage
- Communicate risk signals through visual dashboards
- Convert raw public disclosures into audit planning insights
