# Audit Risk Radar

Audit Risk Radar is a Streamlit dashboard and Python pipeline for screening audit risk signals from Korean public disclosure data. The project uses OpenDART financial statements, KRX listed-company universe data, Beneish-style accounting indicators, peer benchmarking, and unsupervised anomaly detection to help an auditor decide which companies deserve deeper planning-stage attention.

The project does not claim to prove fraud or identify specific journal entries. It is designed as a digital audit planning tool: it turns public financial statements into explainable risk signals, peer context, and follow-up audit questions.

## Current Status

As of the latest local run:

- Raw DART panel: 2,050 companies and 9,760 company-year rows
- Companies with complete five-year raw coverage: 1,864
- Scored dashboard dataset: 1,995 companies and 7,675 company-year rows
- Period: 2020-2024 raw collection, with scored rows generally starting from 2021 because ratio indices require a prior year
- Universe: KRX current listed companies matched to DART corp codes, excluding financial companies, SPACs, REIT-like vehicles, and special-purpose entities where appropriate

Large generated datasets are intentionally ignored by git. They can be regenerated with the scripts in this repository using a valid OpenDART API key.

## Why This Project Exists

Digital audit work increasingly depends on full-population analytics, automated data processing, explainable scoring, and risk-based prioritization. Public disclosure data is weaker than internal ERP, journal-entry, and contract-level evidence, but it is still useful for planning-stage screening.

This project asks:

> If an auditor only has public financial statements, can we still identify companies whose accounting patterns deserve closer review?

The answer is yes, with important limits. Public data cannot replace audit evidence, but it can support a disciplined first-pass risk assessment.

## Main Features

- Company-centered search and analysis dashboard
- KRX current listed-company universe fetch
- DART/OpenDART financial statement collection
- Account-name normalization from heterogeneous Korean/IFRS account names
- Beneish-style indicators as an interpretable accounting baseline
- Peer risk scoring by industry, year, size, and market-aware comparison logic
- ML anomaly risk using robust preprocessing and unsupervised models
- Korean risk explanations for Accounting Risk, Peer Risk, and ML Risk
- Audit briefing section that explains why a company is risky and what to ask next
- Detailed annual calculation table with comma-formatted raw amounts
- Data quality diagnostics, imputation flags, and failure logs
- External event label template for later weak validation

## Risk Layers

### Accounting Risk

The accounting layer uses Beneish-style indicators such as:

- DSRI: receivables growth relative to sales
- GMI: gross margin deterioration
- AQI: asset quality movement
- SGI: sales growth
- SGAI: SG&A proxy movement
- LVGI: leverage movement
- TATA: accruals relative to assets

M-Score is used as an explainable red-flag baseline, not as a fraud conclusion.

### Peer Risk

The peer layer compares the selected company with similar companies rather than reading its ratios in isolation. The comparison uses industry-year distributions and matched peer ideas so the app can explain whether a ratio is unusual relative to comparable companies.

### ML Risk

The ML layer uses unsupervised anomaly detection because reliable fraud labels are scarce. The current pipeline uses robust preprocessing, imputation tracking, scaling, Isolation Forest style anomaly scoring, and PCA-style reconstruction logic.

The purpose of ML is not to make the conclusion. It highlights multivariate patterns that may be missed by one formula.

## Data Collection Flow

1. Fetch current listed-company universe from KRX.
2. Match KRX stock codes to DART corp codes.
3. Exclude finance, SPAC, REIT, and special-purpose companies unless deliberately included.
4. Collect five years of DART financial statements.
5. Normalize account names into a common schema.
6. Save checkpoints and failure logs.
7. Recalculate risk scores and explanations.
8. Launch the Streamlit dashboard.

## Account Mapping Challenge

The hardest technical problem is not just downloading more companies. It is mapping inconsistent public account names into a standard analytical schema.

Different companies may use different labels for similar concepts, for example:

- 매출액
- 영업수익
- 수익
- 용역매출
- 게임매출
- 콘텐츠매출

The pipeline therefore combines:

- DART/IFRS `account_id` matching
- Korean account-name synonym candidates
- Exclusion keywords to avoid false matches
- Statement preference such as BS, IS, and CF
- Consolidated statement preference
- Fuzzy text matching
- Failure diagnostics with actual account-name samples

The current code also handles cases where service or game companies do not present gross profit in the same way as manufacturers. When an index would become `0 / 0`, the metrics layer treats it as a neutral index value rather than dropping the company-year.

## How To Run

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run the app with the sample data or existing processed data:

```bash
streamlit run audit_risk_radar/app.py
```

Fetch current KRX listed-company universe:

```bash
python3 scripts/fetch_krx_universe.py \
  --market KRX \
  --output data/raw/krx/current_listed_companies.csv
```

Backfill missing listed companies from DART:

```bash
export DART_API_KEY="your_open_dart_api_key"

python3 scripts/backfill_missing_listed_companies.py \
  --start-year 2020 \
  --end-year 2024 \
  --sleep 0.03 \
  --checkpoint-every 25 \
  --skip-existing-failures \
  --universe data/raw/krx/current_listed_companies.csv \
  --input data/processed/financials_panel_2020_2024_full.csv \
  --output data/processed/financials_panel_2020_2024_full.csv \
  --failure-log data/processed/dart_backfill_failures.csv
```

Run tests:

```bash
python3 -m unittest discover tests
```

## Repository Structure

```text
audit_risk_radar/
  app.py                         # Streamlit dashboard
src/
  dart_pipeline.py               # DART collection and account matching
  data_loader.py                 # Sample/DART panel loader
  metrics.py                     # Beneish-style feature engineering
  risk_scoring.py                # Accounting, peer, and ML risk scores
  peer_selection.py              # Peer-group matching logic
  explanations.py                # Korean risk narratives and audit questions
  event_labels.py                # External weak-label support
scripts/
  fetch_krx_universe.py          # Current KRX universe fetch
  backfill_missing_listed_companies.py
  collect_dart_panel.py
  collect_dart_report_risks.py
docs/
  implementation_report.md       # Detailed project explanation
  methodology.md
  project_brief.md
  labeling_guide.md
data/sample/
  sample_financials.csv
data/labels/
  external_events_template.csv
tests/
  test_metrics.py
```

## Interview Positioning

I built Audit Risk Radar to show how digital audit can turn public financial statement data into planning-stage risk insight. I started with an interpretable Beneish-style baseline, then expanded it with peer benchmarking, unsupervised anomaly detection, account mapping diagnostics, and a Korean dashboard that explains why each company was flagged. The goal is not to replace auditor judgment, but to help auditors ask better questions earlier.

## Limitations

- Public financial statements do not contain journal-entry, contract, invoice, or ERP-level evidence.
- The model identifies risk signals, not fraud or misstatement conclusions.
- Account mapping quality affects downstream scores.
- Peer comparison depends on industry classification and available public data.
- New listings, mergers, spin-offs, and disclosure format changes can create partial-year coverage.
- Any red flag requires professional judgment and corroborating audit evidence.

## More Detail

See [docs/implementation_report.md](docs/implementation_report.md) for the full project explanation.

한국어 상세 설명은 [docs/implementation_report_ko.md](docs/implementation_report_ko.md)를 참고하세요.
