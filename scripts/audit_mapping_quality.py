from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.metrics import add_beneish_style_features


DEFAULT_INPUT = "data/processed/financials_panel_2020_2024_full.csv"
DEFAULT_OUTPUT = "data/processed/account_mapping_quality_issues.csv"

NUMERIC_COLUMNS = [
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
]

ACCOUNT_TARGETS = [
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
]


def main() -> None:
    args = parse_args()
    panel = pd.read_csv(args.input, dtype={"stock_code": str})
    issues = audit_mapping_quality(panel)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    issues.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"Input rows: {len(panel):,}")
    print(f"Issues: {len(issues):,}")
    if not issues.empty:
        print(issues["severity"].value_counts().to_string())
        print("\nTop issue types")
        print(issues["issue_type"].value_counts().head(20).to_string())
        print(f"\nSaved: {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit DART account mapping quality across the panel.")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    return parser.parse_args()


def audit_mapping_quality(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    df["stock_code"] = df["stock_code"].astype(str).str.zfill(6)
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    parsed = parse_matched_accounts(df.get("matched_accounts", pd.Series("", index=df.index)))
    for target in ACCOUNT_TARGETS:
        df[f"{target}_matched_account"] = parsed[target]

    featured = add_beneish_style_features(df)
    issues: list[dict[str, object]] = []
    for row in featured.sort_values(["stock_code", "year"]).to_dict("records"):
        issues.extend(row_level_issues(row))

    issues.extend(temporal_issues(featured))
    result = pd.DataFrame(issues)
    if result.empty:
        return pd.DataFrame(columns=issue_columns())
    result["severity_rank"] = result["severity"].map({"High": 0, "Watch": 1, "Info": 2}).fillna(9)
    return result.sort_values(
        ["severity_rank", "company_name", "stock_code", "year", "issue_type"]
    )[issue_columns()]


def parse_matched_accounts(series: pd.Series) -> pd.DataFrame:
    rows = []
    for value in series.fillna("").astype(str):
        parsed = {target: "" for target in ACCOUNT_TARGETS}
        for part in value.split(";"):
            if ":" not in part:
                continue
            target, account_name = part.split(":", 1)
            target = target.strip()
            if target in parsed:
                parsed[target] = account_name.strip()
        rows.append(parsed)
    return pd.DataFrame(rows, index=series.index)


def row_level_issues(row: dict[str, object]) -> list[dict[str, object]]:
    issues = []
    base = {
        "stock_code": str(row.get("stock_code", "")).zfill(6),
        "company_name": row.get("company_name", ""),
        "year": row.get("year", ""),
        "industry": row.get("industry", ""),
    }

    def add(severity: str, issue_type: str, target: str, account: str, detail: str, value: object = "") -> None:
        issues.append(
            {
                **base,
                "severity": severity,
                "issue_type": issue_type,
                "target_account": target,
                "matched_account": account,
                "metric_value": value,
                "detail": detail,
            }
        )

    matched_accounts = [str(row.get(f"{target}_matched_account", "") or "") for target in ACCOUNT_TARGETS]
    if not any(matched_accounts):
        add("Info", "missing_match_trace", "all", "", "matched_accounts trace is empty")

    revenue = as_float(row.get("revenue"))
    gross_profit = as_float(row.get("gross_profit"))
    operating_income = as_float(row.get("operating_income"))
    receivables = as_float(row.get("receivables"))
    total_assets = as_float(row.get("total_assets"))
    current_assets = as_float(row.get("current_assets"))
    ppe = as_float(row.get("ppe"))
    operating_cash_flow = as_float(row.get("operating_cash_flow"))
    gross_margin = as_float(row.get("gross_margin"))

    gross_account = str(row.get("gross_profit_matched_account", "") or "")
    if gross_account and looks_like_revenue(gross_account) and not contains_any(gross_account, ["총이익", "총손익", "총손실"]):
        add(
            "High",
            "gross_profit_mapped_to_revenue",
            "gross_profit",
            gross_account,
            "gross_profit was matched to a revenue-like account name",
            gross_margin,
        )
    if gross_account and contains_any(gross_account, ["영업이익", "영업손익", "영업손실"]):
        add(
            "Watch",
            "gross_profit_uses_operating_income_proxy",
            "gross_profit",
            gross_account,
            "gross_profit is unavailable or mapped to operating income proxy; margin-based indicators need caution",
            gross_margin,
        )
    if np.isfinite(gross_margin) and gross_margin >= 0.98 and np.isfinite(operating_income):
        add(
            "High",
            "gross_margin_near_100_percent",
            "gross_profit",
            gross_account,
            "gross margin is near 100%; likely revenue was used as gross profit for a service/company without gross profit subtotal",
            gross_margin,
        )

    receivable_account = str(row.get("receivables_matched_account", "") or "")
    if receivable_account and contains_any(receivable_account, ["자산총계", "유동자산", "비유동자산"]):
        add(
            "High",
            "receivables_mapped_to_asset_total",
            "receivables",
            receivable_account,
            "receivables target matched to broad asset account",
            ratio(receivables, total_assets),
        )
    if np.isfinite(receivables) and np.isfinite(total_assets) and receivables > total_assets * 1.02:
        add(
            "High",
            "receivables_exceed_total_assets",
            "receivables",
            receivable_account,
            "receivables exceed total assets",
            ratio(receivables, total_assets),
        )

    ocf_account = str(row.get("operating_cash_flow_matched_account", "") or "")
    if ocf_account and contains_any(ocf_account, ["기초현금", "기말현금", "현금및현금성자산"]):
        add(
            "High",
            "operating_cash_flow_mapped_to_cash_balance",
            "operating_cash_flow",
            ocf_account,
            "operating cash flow target matched to a cash balance account",
            operating_cash_flow,
        )

    operating_account = str(row.get("operating_income_matched_account", "") or "")
    if operating_account and looks_like_revenue(operating_account):
        add(
            "High",
            "operating_income_mapped_to_revenue",
            "operating_income",
            operating_account,
            "operating income target matched to revenue-like account",
            ratio(operating_income, revenue),
        )

    if np.isfinite(current_assets) and np.isfinite(total_assets) and current_assets > total_assets * 1.02:
        add(
            "High",
            "current_assets_exceed_total_assets",
            "current_assets",
            str(row.get("current_assets_matched_account", "") or ""),
            "current assets exceed total assets",
            ratio(current_assets, total_assets),
        )
    if np.isfinite(ppe) and np.isfinite(total_assets) and ppe > total_assets * 1.02:
        add(
            "High",
            "ppe_exceeds_total_assets",
            "ppe",
            str(row.get("ppe_matched_account", "") or ""),
            "property, plant and equipment exceeds total assets",
            ratio(ppe, total_assets),
        )

    return issues


def temporal_issues(df: pd.DataFrame) -> list[dict[str, object]]:
    issues = []
    sorted_df = df.sort_values(["stock_code", "year"]).copy()
    for stock_code, company in sorted_df.groupby("stock_code", sort=False):
        previous = None
        for row in company.to_dict("records"):
            if previous is None:
                previous = row
                continue
            for target, metric in [
                ("gross_profit", "gmi"),
                ("receivables", "dsri"),
                ("total_liabilities", "lvgi"),
                ("current_assets", "aqi"),
            ]:
                current_account = str(row.get(f"{target}_matched_account", "") or "")
                previous_account = str(previous.get(f"{target}_matched_account", "") or "")
                metric_value = as_float(row.get(metric))
                if (
                    current_account
                    and previous_account
                    and current_account != previous_account
                    and np.isfinite(metric_value)
                    and (metric_value >= 3.0 or metric_value <= 0.33)
                ):
                    issues.append(
                        {
                            "stock_code": stock_code,
                            "company_name": row.get("company_name", ""),
                            "year": row.get("year", ""),
                            "industry": row.get("industry", ""),
                            "severity": "High",
                            "issue_type": "metric_jump_with_account_change",
                            "target_account": target,
                            "matched_account": current_account,
                            "metric_value": metric_value,
                            "detail": (
                                f"{metric.upper()} changed sharply while matched account changed "
                                f"from '{previous_account}' to '{current_account}'"
                            ),
                        }
                    )
            previous = row
    return issues


def issue_columns() -> list[str]:
    return [
        "severity",
        "issue_type",
        "stock_code",
        "company_name",
        "year",
        "industry",
        "target_account",
        "matched_account",
        "metric_value",
        "detail",
    ]


def contains_any(value: str, keywords: list[str]) -> bool:
    normalized = normalize(value)
    return any(normalize(keyword) in normalized for keyword in keywords)


def looks_like_revenue(value: str) -> bool:
    return contains_any(value, ["매출액", "영업수익", "수익", "매출"]) and not contains_any(
        value,
        ["법인세비용", "기타수익", "금융수익", "이자수익", "배당수익", "영업외수익"],
    )


def normalize(value: object) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]", "", str(value or "")).lower()


def as_float(value: object) -> float:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(numeric) if pd.notna(numeric) else float("nan")


def ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return float("nan")
    return float(numerator / denominator)


if __name__ == "__main__":
    main()
