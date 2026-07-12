from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


# The dashboard is designed to run without a DART API key during review.
# It therefore tries the committed processed DART panel first, then falls
# back to a smaller sample dataset only when processed data is missing.
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

    # Fail fast when a required analytical account is missing. A silent
    # missing column here would later distort M-Score, peer risk, and ML risk.
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    return df


def generate_sample_financials(output_path: str | Path, random_state: int = 42) -> pd.DataFrame:
    """Generate a reproducible public-financial-statement style demo dataset."""
    rng = np.random.default_rng(random_state)
    industries = ["Manufacturing", "Retail", "Technology", "Construction", "Bio"]
    companies = [
        (f"{i:06d}", f"Company {i:03d}", industries[i % len(industries)])
        for i in range(1, 81)
    ]

    rows = []
    for stock_code, company_name, industry in companies:
        revenue = rng.normal(300_000, 80_000)
        assets = revenue * rng.uniform(0.9, 1.8)
        liabilities_ratio = rng.uniform(0.25, 0.75)
        receivable_ratio = rng.uniform(0.08, 0.25)
        margin = rng.uniform(0.12, 0.42)

        for year in range(2019, 2024):
            growth = rng.normal(1.06, 0.13)
            revenue = max(revenue * growth, 20_000)
            assets = max(assets * rng.normal(1.04, 0.1), revenue * 0.5)
            receivables = revenue * max(receivable_ratio + rng.normal(0, 0.025), 0.02)
            gross_profit = revenue * max(margin + rng.normal(0, 0.03), 0.02)
            operating_income = gross_profit * rng.uniform(0.25, 0.75)
            current_assets = assets * rng.uniform(0.35, 0.72)
            ppe = assets * rng.uniform(0.12, 0.45)
            total_liabilities = assets * max(liabilities_ratio + rng.normal(0, 0.05), 0.05)
            net_income = operating_income * rng.uniform(0.45, 0.95)
            operating_cash_flow = net_income * rng.normal(0.95, 0.35)

            rows.append(
                {
                    "year": year,
                    "stock_code": stock_code,
                    "company_name": company_name,
                    "industry": industry,
                    "revenue": revenue,
                    "receivables": receivables,
                    "gross_profit": gross_profit,
                    "operating_income": operating_income,
                    "total_assets": assets,
                    "current_assets": current_assets,
                    "ppe": ppe,
                    "total_liabilities": total_liabilities,
                    "net_income": net_income,
                    "operating_cash_flow": operating_cash_flow,
                }
            )

    df = pd.DataFrame(rows)

    # Inject a few artificial red-flag patterns so the sample dashboard still
    # demonstrates the risk logic when the real DART panel is unavailable.
    flagged_codes = ["000007", "000019", "000043", "000061"]
    mask = (df["stock_code"].isin(flagged_codes)) & (df["year"] == 2023)
    df.loc[mask, "receivables"] *= 2.3
    df.loc[mask, "operating_cash_flow"] *= -0.25
    df.loc[mask, "gross_profit"] *= 0.72
    df.loc[mask, "total_liabilities"] *= 1.35

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df
