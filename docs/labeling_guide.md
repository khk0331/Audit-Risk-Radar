# External Event Labeling Guide

This project uses public financial statement data, so confirmed fraud labels are usually unavailable. External event labels are designed as weak validation signals rather than final proof.

## Label File

Use:

```text
data/labels/external_events_template.csv
```

Required columns:

- `stock_code`: six-digit listed company code
- `company_name`: company name used for reviewer readability
- `year`: fiscal/reporting year linked to the event
- `event_type`: event category
- `event_date`: event disclosure or announcement date
- `source`: source name such as DART, KRX, audit report, enforcement release
- `source_url`: public source URL
- `notes`: short reviewer note

## Suggested Event Types

- `restatement`: financial statement correction or restatement disclosure
- `modified_opinion`: qualified, adverse, disclaimer, or other modified audit opinion
- `going_concern`: going-concern uncertainty or emphasis in audit report
- `exchange_warning`: administrative issue, delisting risk, or exchange warning
- `disclosure_sanction`: late filing, unfaithful disclosure, or regulatory disclosure sanction
- `misappropriation`: embezzlement, breach of trust, or similar public disclosure

## Validation Use

The dashboard compares event-labeled company-years against the model's risk ranking:

- How many validation-year event companies are captured by the historical top-risk threshold?
- Is the average risk score higher for event-labeled companies?
- Which flagged companies also have event labels?

This does not convert the model into a supervised fraud classifier. It provides a practical audit analytics check that the risk score is directionally aligned with observable external risk events.
