# Audit Risk Radar Implementation Report

## 1. Project Name

Audit Risk Radar

## 2. One-Line Summary

Audit Risk Radar is a DART-based financial statement risk screening dashboard that helps auditors identify companies with unusual accounting, peer, and machine-learning anomaly signals.

## 3. Problem The Project Solves

Auditors must identify high-risk areas before detailed audit procedures begin. In practice, internal data such as ledgers, journal entries, invoices, and contracts is not always available at the earliest planning stage. However, public financial statements are available for listed companies.

This project explores how much useful risk insight can be extracted from public disclosures alone. It does not attempt to conclude fraud. Instead, it identifies risk signals that may guide audit planning, peer comparison, and follow-up questions.

The key practical question is:

> Given only public financial statement data, can an auditor prioritize companies that deserve closer attention?

## 4. Data Scope

The project uses three data layers:

1. Sample data for reproducible demos.
2. OpenDART financial statement data for real public filings.
3. KRX current listed-company data to define a cleaner current listed-company universe.

The latest local run expanded the panel to:

- Raw panel: 2,050 companies and 9,760 company-year rows
- Five-year complete raw companies: 1,864
- Scored dashboard data: 1,995 companies and 7,675 company-year rows
- Main period: 2020-2024 raw collection
- Scored period: generally 2021-2024 because index-style ratios require prior-year values

Generated data files under `data/raw/` and `data/processed/` are ignored by git because they are large and reproducible.

## 5. Overall Workflow

```text
KRX listed-company universe
        |
        v
DART corp_code matching
        |
        v
Financial/SPAC/REIT exclusion
        |
        v
OpenDART financial statement collection
        |
        v
Account-name normalization
        |
        v
Beneish-style ratio calculation
        |
        v
Accounting Risk + Peer Risk + ML Risk
        |
        v
Korean dashboard explanations and audit questions
```

## 6. Why KRX Universe Was Added

At first, the project used DART corp codes as the source of listed companies. During testing, this produced many stale or irrelevant companies because DART corp-code data can include old, delisted, merged, or otherwise inactive entities.

The pipeline was therefore changed to:

1. Fetch current listed companies from KRX.
2. Match them to DART corp codes using stock code.
3. Collect only companies that are relevant to the current listed-company universe.

This solved the issue where important companies such as Maeil Dairies could be missing from the dashboard even though DART had collectible financial statement data.

## 7. Financial And Special-Purpose Exclusion Logic

The project currently focuses on non-financial operating companies. Financial companies are excluded because banks, insurers, securities firms, REITs, and investment vehicles have different financial statement structures and risk indicators.

The exclusion logic considers:

- Industry codes
- Company-name keywords
- SPAC and special-purpose naming patterns
- REIT and infrastructure-fund style naming patterns

During development, the filter was adjusted because a simple industry-code prefix rule incorrectly excluded non-financial holding companies such as SK, BGF, and LG. It was also adjusted because overly broad name keywords could incorrectly exclude companies such as JW Life Science or Mirae Life Resources. This is a good example of why data cleaning in financial analytics must be iterative.

## 8. Account Mapping Challenge

The hardest technical issue is account-name normalization.

Financial statement line items are not perfectly standardized across companies. Even when the economic meaning is similar, companies may use different Korean account names, different IFRS account IDs, different statement sections, or different disclosure formatting.

The target analytical schema requires fields such as:

- revenue
- receivables
- gross_profit
- operating_income
- total_assets
- current_assets
- ppe
- total_liabilities
- net_income
- operating_cash_flow

The account resolver uses:

- DART/IFRS account IDs
- Korean synonym keywords
- Exclusion keywords
- Statement preference, such as BS, IS, and CF
- Consolidated financial statement preference
- Fuzzy matching
- Failure diagnostics with actual account-name samples

This matters because a single wrong mapping can distort the risk score. For example, in service or game companies, gross profit may not be presented like a manufacturing company. The code now avoids matching operating income as gross profit by fuzzy similarity alone and handles zero-index situations more conservatively.

## 9. Core Accounting Indicators

The project uses Beneish-style indicators as the interpretable accounting baseline.

Key indicators include:

- DSRI: receivables-to-sales pressure
- GMI: gross margin deterioration
- AQI: asset quality movement
- SGI: sales growth
- SGAI: SG&A proxy movement
- LVGI: leverage change
- TATA: accruals relative to total assets

These indicators are useful because they are calculable from public financial statements and understandable to auditors. They are not used as fraud proof.

## 10. Risk Score Layers

### Accounting Risk

Accounting Risk is based on Beneish-style signals and rule-based red flags. It answers:

- Are receivables growing faster than revenue?
- Is gross margin deteriorating?
- Is the company generating weak operating cash flow relative to earnings?
- Are accruals unusually high?

### Peer Risk

Peer Risk answers:

- Is this company unusual compared with similar companies?
- Is the signal abnormal for this industry and year?
- Is the company outside a normal peer range?

The project originally compared companies mainly by industry. It was later expanded conceptually and structurally to support richer peer logic, because deal and valuation practice usually considers not only industry but also size, market, and business comparability.

### ML Risk

ML Risk uses unsupervised anomaly detection because reliable public fraud labels are scarce. The ML layer is designed to detect multivariate patterns that may not be obvious from one ratio.

The pipeline applies:

- Missing-value tracking
- Industry-year median imputation
- Year and global fallback imputation
- Winsorization
- Robust scaling
- Isolation Forest style anomaly scoring
- PCA-style reconstruction error

The model is not an auditor. It is a prioritization tool.

## 11. Dashboard Design

The dashboard was redesigned around company search because practical audit work usually starts with a target company, not with a generic top-risk list.

The current interface emphasizes:

- Company search and selection
- Summary risk scores
- Historical trend chart
- Detailed explanation of why the company is risky
- Accounting Risk, Peer Risk, and ML Risk decomposition
- Peer comparison
- Year-by-year calculation details
- Audit workplan suggestions
- Data quality and validation expanders

The UI uses Korean explanations where interpretation matters, while simple fields such as `Industry` and `year` remain in English for readability.

## 12. Why Text Risk Was Removed

The project briefly explored using prior-year annual report or audit report text to identify risk phrases. This was removed from the main dashboard because text risk may be absent, inconsistent, or difficult to validate reliably from public filings within the current project scope.

The decision was to keep the app focused on financial statement risk signals, peer comparison, and explainable scoring. This made the workflow cleaner and more defensible for a portfolio project.

## 13. Validation Logic

The project includes an external event label template for future validation. Potential weak labels include:

- Restatement disclosures
- Modified audit opinions
- Going-concern uncertainty
- Exchange warnings
- Enforcement or disclosure sanctions

The current validation philosophy is conservative:

- High-risk scores are not treated as proof.
- External labels are weak signals, not perfect ground truth.
- The goal is directional alignment with audit-relevant events.

## 14. Practical Audit Interpretation

Because the project uses public disclosure data only, it should not say:

- Review this exact journal entry.
- Inspect this exact ledger.
- Confirm this exact invoice.

Those require internal client data.

The app should instead say:

- Revenue recognition deserves attention.
- Receivables collectability may need follow-up.
- Cash conversion appears weak.
- Margin movement is unusual versus peers.
- Accrual pressure is elevated.
- The auditor should consider focused procedures in this area.

This keeps the project aligned with realistic audit evidence boundaries.

## 15. Main Code Files

`audit_risk_radar/app.py`

Runs the Streamlit dashboard.

`src/dart_pipeline.py`

Handles OpenDART collection, corp-code matching, industry mapping, account-name normalization, and diagnostics.

`scripts/fetch_krx_universe.py`

Fetches current KRX listed-company universe.

`scripts/backfill_missing_listed_companies.py`

Backfills missing DART financial statements from the KRX-DART matched universe with checkpoints and failure logs.

`src/metrics.py`

Calculates Beneish-style financial indicators.

`src/risk_scoring.py`

Creates Accounting Risk, Peer Risk, ML Risk, and final composite scores.

`src/explanations.py`

Creates Korean explanations, risk drivers, audit focus, and follow-up questions.

`src/peer_selection.py`

Supports peer group logic.

`tests/test_metrics.py`

Checks core feature calculation, scoring, event labels, and account matching behavior.

## 16. How To Reproduce

1. Install dependencies.

```bash
python3 -m pip install -r requirements.txt
```

2. Run the dashboard with sample data.

```bash
streamlit run audit_risk_radar/app.py
```

3. Fetch KRX universe.

```bash
python3 scripts/fetch_krx_universe.py --market KRX --output data/raw/krx/current_listed_companies.csv
```

4. Collect DART financial statements.

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

5. Run tests.

```bash
python3 -m unittest discover tests
```

## 17. What Was Implemented By The Author

The project implementation includes:

- DART API collection pipeline
- KRX listed-company universe integration
- Account-name matching and diagnostics
- Financial statement feature engineering
- Risk scoring model
- Peer comparison logic
- Streamlit dashboard
- Korean explanations and audit-oriented narrative
- Data quality and imputation tracking
- Checkpoint-based large-scale data collection
- Unit tests
- Project documentation

## 18. Key Difficulties

The most important difficulties were:

- DART corp-code data is not the same as a clean current listed-company universe.
- Companies use inconsistent account names.
- Financial companies need different indicators and should not be mixed casually with operating companies.
- Some companies have partial history because of new listings, mergers, spin-offs, or disclosure changes.
- Public data cannot support journal-entry-level conclusions.
- ML anomaly scores need explanation to be audit-useful.

## 19. Connection To Audit, Digital, And AI

This project connects to digital audit in three ways.

First, it uses full-population public data instead of manual one-company review.

Second, it combines accounting logic with machine learning rather than using AI as a black box.

Third, it emphasizes explainability. In audit, a risk score is only useful if the auditor can explain why it matters and what to do next.

The project shows that AI in audit should not replace professional judgment. It should help auditors focus that judgment earlier, more consistently, and with better evidence of why a company was selected for review.

## 20. Next Steps

Recommended next improvements:

- Finish the remaining KRX current-listed backfill.
- Review failure logs and improve account-name candidate lists.
- Add a data coverage dashboard.
- Add stronger external weak labels.
- Add downloadable audit planning memo.
- Add peer-group tuning controls.
- Add GitHub Actions test workflow.
- Add screenshots to the README after final UI polish.
