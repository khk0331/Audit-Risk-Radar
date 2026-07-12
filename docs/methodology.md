# Methodology

## Data Scope

The target production data source is DART/OpenDART financial statement data. The initial repository uses generated sample data so that the project is reproducible without API keys.

The first expansion target is 2019-2024 financial statements for up to 500 listed companies. This creates a panel dataset at the company-year level and allows both trend analysis and cross-sectional comparison.

Minimum fields:

- year
- stock_code
- company_name
- industry
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

## Accounting Indicators

The main accounting indicators are:

- DSRI: Days Sales in Receivables Index
- GMI: Gross Margin Index
- AQI: Asset Quality Index
- SGI: Sales Growth Index
- SGAI: SG&A proxy index
- LVGI: Leverage Index
- TATA: Total Accruals to Total Assets

If depreciation data becomes available, DEPI can be added to move closer to the full Beneish 8-variable model.

## Risk Layers

## Data Quality And Scaling

The DART-derived panel can contain missing values because public filings do not always expose every account in a perfectly standardized form. The scoring pipeline therefore applies a conservative preprocessing flow before peer and ML scoring:

- Replace infinite values with missing values.
- Impute missing indicators by industry-year median first.
- Fall back to year median, then global median, then zero only if no other benchmark exists.
- Store imputation flags so reviewers can see when a company-year relied on filled values.
- Winsorize model inputs at the 1st and 99th percentiles to reduce single-outlier distortion.
- Use `RobustScaler` for ML features so median and interquartile range drive scaling instead of mean and standard deviation.

This keeps the score suitable for company-level audit planning analysis while making data quality limitations visible.

### Accounting Risk

Uses Beneish-style score and rule-based red flags.

### Peer Risk

Uses industry-year robust z-scores and percentile ranks.

The peer layer is designed to answer a simple planning question:

> Is this company moving differently from similar companies in the same year?

During review, one important calibration issue was found. If peer companies are tightly clustered around a ratio, a company can receive an extremely large robust z-score even when the absolute ratio is not unreasonable. For example, a GMI of 1.37 may be a meaningful deterioration versus peers, but it should not automatically behave like a maximum-risk signal just because the peer distribution is narrow.

To reduce over-warning, the model caps each peer z-score before aggregating Peer Risk. This keeps the direction of the signal - "different from peers" - while preventing one narrow-distribution feature from dominating the entire score.

Interview framing:

- Before improvement: Peer Risk correctly detected relative difference, but could overstate intensity.
- Improvement: Apply z-score cap and explain Peer Risk as relative difference, not a fraud conclusion.
- Audit implication: High Peer Risk means "ask why this company differs from comparable companies," not "the company is misstated."

### ML Risk

Uses unsupervised anomaly detection because confirmed financial statement fraud labels are scarce.

Initial models:

- Isolation Forest
- PCA reconstruction error

The ML layer uses robust-scaled, winsorized accounting indicators rather than raw financial statement amounts. This helps the model focus on abnormal financial statement patterns instead of company size.

Future extension:

- Autoencoder

## Composite Score

The final risk score should be an ensemble:

```text
final_risk_score =
  accounting_weight * accounting_risk
  + peer_weight * peer_risk
  + ml_weight * ml_risk
```

Current implementation:

```text
final_risk_score =
  0.45 * accounting_risk_score
  + 0.30 * peer_risk_score
  + 0.25 * ml_risk_score
```

This weighting is a documented prototype assumption, not a coefficient estimated from confirmed fraud labels or an official audit standard. It is kept transparent so reviewers can challenge or revise it. The current design logic is:

- **Accounting Risk 45%**: Beneish-style indicators are explainable accounting signals and provide the anchor for the planning score.
- **Peer Risk 30%**: ISA-style analytical procedures compare relationships and fluctuations across prior periods and comparable entities, so peer context is a second major signal.
- **ML Risk 25%**: unsupervised anomaly models are useful for pattern discovery, but they are less directly explainable; therefore, they are used as a supporting signal rather than the dominant component.

The score is used to structure planning-stage company analysis, not final judgment or a fraud probability. In the dashboard, the detailed component explanations and public-disclosure check points are more important than the composite score itself. A production version should run sensitivity analysis on the weights and validate the calibration against external weak labels such as restatements, modified opinions, enforcement actions, and going-concern emphasis.

## Validation Strategy

Because confirmed fraud labels are scarce, the first validation layer is a time-based hold-out sanity check:

- Use historical years as the train/reference period.
- Treat the latest year as the validation year.
- Compare the latest-year risk distribution against the historical distribution.
- Apply the historical 90th percentile threshold to the validation year.
- Review companies whose risk score increases sharply year over year.

This is not a supervised fraud validation. It tests whether the model creates stable and explainable company-level risk signals when applied to a later reporting period. A later extension can add weak labels such as restatement filings, modified audit opinions, going-concern uncertainty, exchange warnings, or enforcement events.

The repository also includes an external event label template. When event labels are added, the dashboard compares event-labeled company-years against the high-risk group:

- Event capture rate within the validation-year top-risk threshold.
- Average risk score for event-labeled vs non-event company-years.
- Flagged companies that also have external event evidence.

These labels are weak validation signals. They help assess directional alignment with audit-relevant public events, but they do not prove fraud or misstatement.

## Explainability

Each flagged company receives a short narrative:

- Main risk driver
- Peer comparison
- Trend direction
- Suggested audit question

Example:

> Revenue increased sharply while receivables grew faster than sales and operating cash flow weakened. This pattern may warrant additional procedures around revenue recognition and collectability.

## Public Data Boundary

This project uses public disclosure data only. It should not claim to identify specific journal entries, ledgers, contracts, or evidence items. Those procedures require internal audit data. The correct output is a risk signal, a review area, and a standards-based follow-up question.
