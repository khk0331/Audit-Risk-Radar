from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.sample_data import generate_sample_financials


REQUIRED_COLUMNS = {
    "year",
    "stock_code",
    "company_name",
    "industry",
    "revenue",
    "receivables",
    "gross_profit",
    "operating_income",
    "total_assets",
    "current_assets",
    "ppe",
    "total_liabilities",
    "net_income",
    "operating_cash_flow",
}


def load_financials(path: str | Path | None = None) -> pd.DataFrame:
    if path is None:
        processed_candidates = [
            Path("data/processed/financials_panel_2020_2024_full.csv"),
            Path("data/processed/financials_panel.csv"),
        ]
        path = next(
            (candidate for candidate in processed_candidates if candidate.exists()),
            Path("data/sample/sample_financials.csv"),
        )

    path = Path(path)
    if not path.exists():
        return generate_sample_financials(path)

    df = pd.read_csv(path, dtype={"stock_code": str})
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    return df
