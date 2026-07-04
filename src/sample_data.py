from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


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

    # Inject a few explainable red-flag patterns for the demo dashboard.
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


if __name__ == "__main__":
    generate_sample_financials("data/sample/sample_financials.csv")

