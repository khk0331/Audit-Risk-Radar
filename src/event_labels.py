from __future__ import annotations

from pathlib import Path

import pandas as pd


EVENT_LABEL_COLUMNS = [
    "stock_code",
    "company_name",
    "year",
    "event_type",
    "event_date",
    "source",
    "source_url",
    "notes",
]


def empty_event_labels() -> pd.DataFrame:
    return pd.DataFrame(columns=EVENT_LABEL_COLUMNS)


def load_event_labels(path: str | Path = "data/labels/external_events_template.csv") -> pd.DataFrame:
    label_path = Path(path)
    if not label_path.exists():
        return empty_event_labels()

    labels = pd.read_csv(label_path, dtype={"stock_code": "string"})
    missing_columns = [col for col in EVENT_LABEL_COLUMNS if col not in labels.columns]
    if missing_columns:
        raise ValueError(f"Event label file is missing columns: {', '.join(missing_columns)}")

    labels = labels[EVENT_LABEL_COLUMNS].copy()
    labels["stock_code"] = labels["stock_code"].astype("string").str.zfill(6)
    labels["year"] = pd.to_numeric(labels["year"], errors="coerce").astype("Int64")
    labels["event_date"] = pd.to_datetime(labels["event_date"], errors="coerce")
    labels = labels.dropna(subset=["stock_code", "year", "event_type"])
    return labels


def attach_event_labels(scored: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    result = scored.copy()
    if labels.empty:
        result["event_flag"] = False
        result["event_types"] = ""
        result["event_sources"] = ""
        return result

    labels = labels.copy()
    labels["stock_code"] = labels["stock_code"].astype("string").str.zfill(6)
    labels["year"] = pd.to_numeric(labels["year"], errors="coerce").astype("Int64")

    event_summary = (
        labels.groupby(["stock_code", "year"], dropna=False)
        .agg(
            event_types=("event_type", lambda values: ", ".join(sorted(set(values.dropna())))),
            event_sources=("source", lambda values: ", ".join(sorted(set(values.dropna())))),
        )
        .reset_index()
    )
    event_summary["event_flag"] = True
    result = result.merge(event_summary, on=["stock_code", "year"], how="left")
    result["event_flag"] = result["event_flag"].fillna(False).astype(bool)
    result["event_types"] = result["event_types"].fillna("")
    result["event_sources"] = result["event_sources"].fillna("")
    return result
