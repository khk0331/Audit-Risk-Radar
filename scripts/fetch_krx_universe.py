from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch the current KRX listed company universe.")
    parser.add_argument("--market", default="KRX", choices=["KRX", "KOSPI", "KOSDAQ", "KONEX"])
    parser.add_argument("--output", default="data/raw/krx/current_listed_companies.csv")
    args = parser.parse_args()

    try:
        import FinanceDataReader as fdr
    except ImportError as exc:
        raise SystemExit(
            "FinanceDataReader is required. Install it with: python3 -m pip install finance-datareader"
        ) from exc

    listing = fdr.StockListing(args.market).copy()
    required = {"Code", "Name", "Market"}
    missing = required.difference(listing.columns)
    if missing:
        raise SystemExit(f"KRX listing response is missing columns: {sorted(missing)}")

    result = listing.rename(
        columns={
            "Code": "stock_code",
            "Name": "company_name",
            "Market": "market",
            "Marcap": "market_cap",
            "Stocks": "shares_outstanding",
        }
    )
    result["stock_code"] = result["stock_code"].astype(str).str.zfill(6)
    result = result[
        [
            col
            for col in [
                "stock_code",
                "company_name",
                "market",
                "market_cap",
                "shares_outstanding",
                "Close",
                "Dept",
                "MarketId",
            ]
            if col in result.columns
        ]
    ].sort_values(["market", "stock_code"])

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved {len(result):,} {args.market} listed companies to {output_path}")


if __name__ == "__main__":
    main()
