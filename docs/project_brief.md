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
- Methodology explanation and limitation notes

## First Expansion Scope

The first expansion should move beyond the original 350-statement experiment into panel data:

- 2019-2024 public financial statements
- Up to 500 KOSPI/KOSDAQ-listed companies
- Company-year level risk scoring
- Peer comparison across the same year and industry where industry metadata is available

This scale is large enough to make anomaly detection and peer benchmarking more meaningful, while still small enough to manage DART API limits, account mapping issues, and missing data.

## Project Rationale

1. Beneish-style M-Score provides an interpretable accounting-based starting point.
2. A single formula is limited, so the workflow adds peer-group comparison and unsupervised anomaly detection.
3. Peer-group comparison reflects industry and market context.
4. Unsupervised anomaly detection is used because confirmed public fraud labels are scarce.
5. Explainability is emphasized because audit planning requires professional judgment and documentation.
6. The dashboard is designed as a planning analytics aid, not as an audit conclusion engine.

## Audit Value

The project can help auditors:

- Prioritize risky companies before detailed testing
- Compare companies consistently across years and industries
- Detect unusual changes in accruals, receivables, margins, growth, and leverage
- Communicate risk signals through visual dashboards
- Convert raw public disclosures into audit planning insights
