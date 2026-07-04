from __future__ import annotations

import argparse
import io
import re
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dart_pipeline import DART_BASE_URL, get_api_key, load_corp_codes
from src.report_risks import REPORT_COVERAGE_COLUMNS, REPORT_RISK_COLUMNS


RISK_KEYWORDS = {
    "계속기업": ["계속기업", "존속능력", "going concern"],
    "감사의견/강조사항": ["한정의견", "부적정의견", "의견거절", "강조사항", "핵심감사사항"],
    "수익인식": ["수익인식", "매출인식", "기간귀속", "cut-off", "고객과의 계약"],
    "채권/회수가능성": ["매출채권", "대손충당금", "손상", "회수가능"],
    "재고/평가": ["재고자산", "평가손실", "진부화", "순실현가능가치"],
    "손상/추정": ["손상검사", "회수가능액", "공정가치", "사용가치", "추정"],
    "부채/유동성": ["유동성", "차입금", "재무약정", "기한이익", "부채비율"],
    "우발/소송": ["우발부채", "소송", "충당부채", "지급보증"],
    "내부통제": ["내부회계관리제도", "중요한 취약점", "미비점"],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect prior-year DART report text risk snippets.")
    parser.add_argument("--api-key", default=None, help="OpenDART API key. Defaults to DART_API_KEY env var.")
    parser.add_argument("--stock-code", default=None, help="Six-digit listed company stock code.")
    parser.add_argument("--stock-codes", default=None, help="Comma-separated stock codes.")
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Collect the top N companies by Final Risk for the analysis year.",
    )
    parser.add_argument(
        "--scored-data",
        default="data/processed/scored_financials_v11.csv",
        help="Scored panel used when --top-n is provided.",
    )
    parser.add_argument("--analysis-year", type=int, required=True, help="Audit/planning year. Prior-year reports are collected.")
    parser.add_argument("--output", default="data/processed/report_risks.csv")
    parser.add_argument("--coverage-output", default="data/processed/report_risk_coverage.csv")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--checkpoint-every", type=int, default=5)
    args = parser.parse_args()

    api_key = get_api_key(args.api_key)
    prior_year = args.analysis_year - 1
    corp_codes = load_corp_codes(api_key)
    stock_codes = resolve_stock_codes(args)
    if not stock_codes:
        raise ValueError("Provide --stock-code, --stock-codes, or --top-n.")

    rows = []
    coverage_rows = []
    for idx, stock_code in enumerate(stock_codes, start=1):
        stock_code = str(stock_code).zfill(6)
        company = corp_codes[corp_codes["stock_code"].astype(str).str.zfill(6) == stock_code]
        if company.empty:
            coverage_rows.append(
                build_coverage_row(
                    stock_code=stock_code,
                    company_name="",
                    prior_year=prior_year,
                    reports_found=0,
                    snippets_found=0,
                    status="corp_code_not_found",
                    message="DART corp code cache에서 종목코드를 찾지 못했습니다.",
                )
            )
            print(f"[{idx}/{len(stock_codes)}] skip {stock_code}: not found in DART corp codes.")
            continue

        row = company.iloc[0]
        company_rows, reports_found = collect_company_report_risks(
            api_key=api_key,
            stock_code=stock_code,
            company_name=row["company_name"],
            corp_code=row["corp_code"],
            prior_year=prior_year,
            sleep=args.sleep,
        )
        rows.extend(company_rows)
        coverage_rows.append(
            build_coverage_row(
                stock_code=stock_code,
                company_name=row["company_name"],
                prior_year=prior_year,
                reports_found=reports_found,
                snippets_found=len(company_rows),
                status=coverage_status(reports_found, len(company_rows)),
                message=coverage_message(reports_found, len(company_rows)),
            )
        )
        print(
            f"[{idx}/{len(stock_codes)}] {row['company_name']}({stock_code}) "
            f"reports: {reports_found:,}, risk snippets: {len(company_rows):,}"
        )
        if args.checkpoint_every and idx % args.checkpoint_every == 0:
            save_rows(rows, args.output)
            save_coverage_rows(coverage_rows, args.coverage_output)
            print(f"Checkpoint saved after {idx:,} companies.")

    save_rows(rows, args.output)
    save_coverage_rows(coverage_rows, args.coverage_output)
    print(f"Saved {len(rows):,} extracted risk snippets to {args.output}")
    print(f"Saved {len(coverage_rows):,} coverage rows to {args.coverage_output}")


def resolve_stock_codes(args: argparse.Namespace) -> list[str]:
    codes = []
    if args.stock_code:
        codes.append(args.stock_code)
    if args.stock_codes:
        codes.extend(code.strip() for code in args.stock_codes.split(",") if code.strip())
    if args.top_n:
        scored = pd.read_csv(args.scored_data, dtype={"stock_code": str})
        year_df = scored[scored["year"] == args.analysis_year].copy()
        top_codes = (
            year_df.sort_values("final_risk_score", ascending=False)["stock_code"]
            .dropna()
            .astype(str)
            .str.zfill(6)
            .drop_duplicates()
            .head(args.top_n)
            .tolist()
        )
        codes.extend(top_codes)
    return list(dict.fromkeys(str(code).zfill(6) for code in codes))


def collect_company_report_risks(
    api_key: str,
    stock_code: str,
    company_name: str,
    corp_code: str,
    prior_year: int,
    sleep: float,
) -> tuple[list[dict[str, str | int]], int]:
    reports = fetch_annual_report_list(api_key, corp_code, prior_year)
    rows = []
    for report in reports:
        text = fetch_document_text(api_key, report["rcept_no"])
        rows.extend(extract_risk_rows(stock_code, company_name, prior_year, report, text))
        time.sleep(sleep)
    return rows, len(reports)


def build_coverage_row(
    stock_code: str,
    company_name: str,
    prior_year: int,
    reports_found: int,
    snippets_found: int,
    status: str,
    message: str,
) -> dict[str, str | int]:
    return {
        "stock_code": str(stock_code).zfill(6),
        "company_name": company_name,
        "year": prior_year + 1,
        "report_year": prior_year,
        "reports_found": reports_found,
        "snippets_found": snippets_found,
        "status": status,
        "message": message,
    }


def coverage_status(reports_found: int, snippets_found: int) -> str:
    if reports_found <= 0:
        return "no_report_found"
    if snippets_found <= 0:
        return "collected_no_keyword_hit"
    return "collected_with_hits"


def coverage_message(reports_found: int, snippets_found: int) -> str:
    if reports_found <= 0:
        return "보고서 목록 조회 결과 대상 사업보고서/감사보고서를 찾지 못했습니다."
    if snippets_found <= 0:
        return "보고서 원문은 수집했지만 사전 정의한 텍스트 리스크 키워드는 탐지되지 않았습니다."
    return "보고서 원문에서 텍스트 리스크 키워드 주변 문구를 추출했습니다."


def save_rows(rows: list[dict[str, str | int]], output: str) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_df = pd.DataFrame(rows, columns=REPORT_RISK_COLUMNS)
    if output_path.exists():
        existing = pd.read_csv(output_path, dtype={"stock_code": str, "rcept_no": str})
        new_df = pd.concat([existing, new_df], ignore_index=True)
    for column in REPORT_RISK_COLUMNS:
        if column not in new_df.columns:
            new_df[column] = ""
    if not new_df.empty:
        new_df = new_df.drop_duplicates(
            subset=["stock_code", "report_year", "rcept_no", "risk_type", "keyword", "excerpt"]
        )
    new_df[REPORT_RISK_COLUMNS].to_csv(output_path, index=False, encoding="utf-8-sig")


def save_coverage_rows(rows: list[dict[str, str | int]], output: str) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_df = pd.DataFrame(rows, columns=REPORT_COVERAGE_COLUMNS)
    if output_path.exists():
        existing = pd.read_csv(output_path, dtype={"stock_code": str})
        new_df = pd.concat([existing, new_df], ignore_index=True)
    for column in REPORT_COVERAGE_COLUMNS:
        if column not in new_df.columns:
            new_df[column] = ""
    if not new_df.empty:
        new_df = new_df.drop_duplicates(
            subset=["stock_code", "report_year"],
            keep="last",
        )
    new_df[REPORT_COVERAGE_COLUMNS].to_csv(output_path, index=False, encoding="utf-8-sig")


def fetch_annual_report_list(api_key: str, corp_code: str, year: int) -> list[dict[str, str]]:
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": f"{year + 1}0101",
        "end_de": f"{year + 1}1231",
        "pblntf_ty": "A",
        "pblntf_detail_ty": "A001",
        "page_count": 100,
    }
    reports = fetch_report_list(api_key, params)
    if reports:
        return reports

    fallback_params = params.copy()
    fallback_params.pop("pblntf_detail_ty", None)
    reports = fetch_report_list(api_key, fallback_params)
    return [
        report
        for report in reports
        if "사업보고서" in str(report.get("report_nm", ""))
        or "annual" in str(report.get("report_nm", "")).lower()
    ]


def fetch_report_list(api_key: str, params: dict[str, str | int]) -> list[dict[str, str]]:
    del api_key
    response = requests.get(f"{DART_BASE_URL}/list.json", params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "000":
        return []
    return payload.get("list", [])


def fetch_document_text(api_key: str, rcept_no: str) -> str:
    response = requests.get(
        f"{DART_BASE_URL}/document.xml",
        params={"crtfc_key": api_key, "rcept_no": rcept_no},
        timeout=60,
    )
    response.raise_for_status()
    content = response.content
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            raw = "\n".join(
                archive.read(name).decode("utf-8", errors="ignore")
                for name in archive.namelist()
                if name.lower().endswith((".xml", ".html", ".htm", ".txt"))
            )
    else:
        raw = content.decode("utf-8", errors="ignore")
    return normalize_text(raw)


def normalize_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_risk_rows(
    stock_code: str,
    company_name: str,
    report_year: int,
    report: dict[str, str],
    text: str,
) -> list[dict[str, str | int]]:
    rows = []
    lowered = text.lower()
    for risk_type, keywords in RISK_KEYWORDS.items():
        for keyword in keywords:
            search = keyword.lower()
            for match in re.finditer(re.escape(search), lowered):
                start = max(match.start() - 130, 0)
                end = min(match.end() + 170, len(text))
                excerpt = text[start:end].strip()
                rows.append(
                    {
                        "stock_code": stock_code,
                        "company_name": company_name,
                        "year": report_year + 1,
                        "report_year": report_year,
                        "report_name": report.get("report_nm", ""),
                        "source": "DART",
                        "risk_type": risk_type,
                        "keyword": keyword,
                        "excerpt": excerpt,
                        "rcept_no": report.get("rcept_no", ""),
                        "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={report.get('rcept_no', '')}",
                    }
                )
                if len([row for row in rows if row["risk_type"] == risk_type and row["keyword"] == keyword]) >= 3:
                    break
    return rows


if __name__ == "__main__":
    main()
