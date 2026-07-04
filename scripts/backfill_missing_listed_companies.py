from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dart_pipeline import (  # noqa: E402
    DartCompany,
    _collect_company_rows_with_diagnostics,
    _is_excluded_financial_company,
    fetch_company_profile,
    get_api_key,
    load_corp_codes,
    map_industry_code,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill listed DART companies missing from the financial panel."
    )
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--input", default="data/processed/financials_panel_2020_2024_full.csv")
    parser.add_argument("--output", default="data/processed/financials_panel_2020_2024_full.csv")
    parser.add_argument("--failure-log", default="data/processed/dart_backfill_failures.csv")
    parser.add_argument(
        "--universe",
        default=None,
        help="Optional current listed universe CSV with stock_code/company_name columns, such as data/raw/krx/current_listed_companies.csv.",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.08)
    parser.add_argument("--checkpoint-every", type=int, default=20)
    parser.add_argument("--include-financial", action="store_true")
    parser.add_argument("--include-alphanumeric-codes", action="store_true")
    parser.add_argument("--skip-existing-failures", action="store_true")
    parser.add_argument(
        "--retry-partials",
        action="store_true",
        help="Retry companies that previously produced partial year coverage.",
    )
    args = parser.parse_args()

    api_key = get_api_key(args.api_key)
    existing = load_existing_panel(args.input)
    completed_codes = completed_stock_codes(existing, args.start_year, args.end_year)

    corp_codes = load_corp_codes(api_key)
    listed = build_listed_candidates(corp_codes, args.universe)
    if not args.include_alphanumeric_codes:
        listed = listed[listed["stock_code"].str.fullmatch(r"\d{6}", na=False)]
    if not args.universe:
        listed = listed.sort_values("stock_code")
    missing = listed[~listed["stock_code"].isin(completed_codes)].copy()
    failures = load_existing_failures(args.failure_log)
    if args.skip_existing_failures and failures:
        failure_df = pd.DataFrame(failures)
        retry_statuses = {"added_partial"} if args.retry_partials else set()
        skip_codes = set(
            failure_df[~failure_df["status"].isin(retry_statuses)]["stock_code"]
            .astype(str)
            .str.zfill(6)
        )
        missing = missing[~missing["stock_code"].isin(skip_codes)]
    if args.limit:
        missing = missing.head(args.limit)

    rows = existing.to_dict("records") if not existing.empty else []

    print(
        f"Listed candidates: {len(listed):,}; completed {len(completed_codes):,}; "
        f"to scan {len(missing):,}.",
        flush=True,
    )

    scanned = 0
    added_companies = 0
    skipped_companies = 0
    failed_companies = 0

    try:
        for row in missing.itertuples(index=False):
            scanned += 1
            stock_code = str(row.stock_code).zfill(6)
            company_name = str(row.company_name)
            profile = fetch_company_profile(api_key, row.corp_code) or {}
            industry_code = str(profile.get("industry_code", "") or profile.get("induty_code", "") or "")
            industry = map_industry_code(industry_code)

            if not args.include_financial and _is_excluded_financial_company(industry_code, company_name):
                skipped_companies += 1
                failures.append(
                    failure_row(
                        stock_code,
                        company_name,
                        row.corp_code,
                        industry_code,
                        industry,
                        "excluded_industry_or_spac",
                        "Financial industry or SPAC/special purpose company excluded.",
                    )
                )
                print(
                    f"[{scanned}/{len(missing)}] {company_name}({stock_code}) skipped: financial/SPAC",
                    flush=True,
                )
                if args.checkpoint_every and scanned % args.checkpoint_every == 0:
                    save_panel(rows, args.output)
                    save_failures(failures, args.failure_log)
                    print(
                        f"Checkpoint: scanned={scanned:,}, added={added_companies:,}, "
                        f"failed={failed_companies:,}, skipped={skipped_companies:,}",
                        flush=True,
                    )
                continue

            company = DartCompany(
                corp_code=str(row.corp_code),
                stock_code=stock_code,
                company_name=company_name,
                industry_code=industry_code,
                industry=industry,
            )
            company_rows, diagnostics = _collect_company_rows_with_diagnostics(
                api_key,
                company,
                args.start_year,
                args.end_year,
                args.sleep,
            )
            rows.extend(company_rows)

            if len(company_rows) >= args.end_year - args.start_year + 1:
                added_companies += 1
                status = "added_complete"
            elif company_rows:
                added_companies += 1
                failed_companies += 1
                status = "added_partial"
            else:
                failed_companies += 1
                status = "failed"

            if status != "added_complete":
                failures.append(
                    failure_row(
                        stock_code,
                        company_name,
                        row.corp_code,
                        industry_code,
                        industry,
                        status,
                        "; ".join(diagnostics[:10]) if diagnostics else "No rows collected.",
                        collected_years=len(company_rows),
                    )
                )

            print(
                f"[{scanned}/{len(missing)}] {company_name}({stock_code}) "
                f"rows +{len(company_rows)}, status={status}",
                flush=True,
            )

            if args.checkpoint_every and scanned % args.checkpoint_every == 0:
                save_panel(rows, args.output)
                save_failures(failures, args.failure_log)
                print(
                    f"Checkpoint: scanned={scanned:,}, added={added_companies:,}, "
                    f"failed={failed_companies:,}, skipped={skipped_companies:,}",
                    flush=True,
                )
            time.sleep(args.sleep)
    except KeyboardInterrupt:
        print("Interrupted. Saving checkpoint before exit.", flush=True)
        save_panel(rows, args.output)
        save_failures(failures, args.failure_log)
        raise

    save_panel(rows, args.output)
    save_failures(failures, args.failure_log)
    print(
        f"Done. scanned={scanned:,}, added={added_companies:,}, "
        f"failed={failed_companies:,}, skipped={skipped_companies:,}",
        flush=True,
    )


def load_existing_panel(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"stock_code": str})


def build_listed_candidates(corp_codes: pd.DataFrame, universe_path: str | Path | None = None) -> pd.DataFrame:
    listed = corp_codes.dropna(subset=["stock_code"]).copy()
    listed["stock_code"] = listed["stock_code"].astype(str).str.zfill(6)
    listed["corp_code"] = listed["corp_code"].astype(str).str.zfill(8)

    if not universe_path:
        return listed

    universe_path = Path(universe_path)
    if not universe_path.exists():
        raise FileNotFoundError(f"Universe CSV not found: {universe_path}")

    universe = pd.read_csv(universe_path, dtype={"stock_code": str})
    if "stock_code" not in universe.columns:
        raise ValueError(f"Universe CSV must include stock_code: {universe_path}")
    universe["stock_code"] = universe["stock_code"].astype(str).str.zfill(6)
    keep_columns = ["stock_code"]
    for optional in ["company_name", "market", "market_cap"]:
        if optional in universe.columns:
            keep_columns.append(optional)

    merged = universe[keep_columns].merge(
        listed,
        on="stock_code",
        how="inner",
        suffixes=("_krx", ""),
    )
    if "company_name_krx" in merged.columns:
        merged["krx_company_name"] = merged["company_name_krx"]
        merged["company_name"] = merged["company_name"].fillna(merged["company_name_krx"])
    if "market" in merged.columns:
        market_order = {"KOSPI": 0, "KOSDAQ": 1, "KONEX": 2}
        merged["_market_order"] = merged["market"].map(market_order).fillna(9)
        merged = merged.sort_values(["_market_order", "stock_code"]).drop(columns=["_market_order"])
    return merged


def completed_stock_codes(panel: pd.DataFrame, start_year: int, end_year: int) -> set[str]:
    if panel.empty:
        return set()
    required_years = end_year - start_year + 1
    target = panel[(panel["year"] >= start_year) & (panel["year"] <= end_year)].copy()
    counts = target.groupby(target["stock_code"].astype(str).str.zfill(6))["year"].nunique()
    return set(counts[counts >= required_years].index)


def load_existing_failures(path: str | Path) -> list[dict[str, object]]:
    path = Path(path)
    if not path.exists():
        return []
    return pd.read_csv(path, dtype={"stock_code": str, "corp_code": str}).to_dict("records")


def failure_row(
    stock_code: str,
    company_name: str,
    corp_code: str,
    industry_code: str,
    industry: str,
    status: str,
    diagnostics: str,
    collected_years: int = 0,
) -> dict[str, object]:
    return {
        "stock_code": str(stock_code).zfill(6),
        "company_name": company_name,
        "corp_code": str(corp_code),
        "industry_code": industry_code,
        "industry": industry,
        "status": status,
        "collected_years": collected_years,
        "diagnostics": diagnostics,
    }


def save_panel(rows: list[dict[str, object]], path: str | Path) -> pd.DataFrame:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    panel = pd.DataFrame(rows)
    if not panel.empty:
        panel["stock_code"] = panel["stock_code"].astype(str).str.zfill(6)
        panel = panel.drop_duplicates(subset=["stock_code", "year"], keep="last")
        panel = panel.sort_values(["stock_code", "year"])
    panel.to_csv(path, index=False, encoding="utf-8-sig")
    return panel


def save_failures(rows: list[dict[str, object]], path: str | Path) -> pd.DataFrame:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    failures = pd.DataFrame(rows)
    if not failures.empty:
        failures["stock_code"] = failures["stock_code"].astype(str).str.zfill(6)
        failures = failures.drop_duplicates(subset=["stock_code", "status"], keep="last")
        failures = failures.sort_values(["status", "stock_code"])
    failures.to_csv(path, index=False, encoding="utf-8-sig")
    return failures


if __name__ == "__main__":
    main()
