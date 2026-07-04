from __future__ import annotations

from pathlib import Path

import pandas as pd


REPORT_RISK_COLUMNS = [
    "stock_code",
    "company_name",
    "year",
    "report_year",
    "report_name",
    "source",
    "risk_type",
    "keyword",
    "excerpt",
    "rcept_no",
    "url",
]

REPORT_COVERAGE_COLUMNS = [
    "stock_code",
    "company_name",
    "year",
    "report_year",
    "reports_found",
    "snippets_found",
    "status",
    "message",
]


def load_report_risks(
    path: str | Path = "data/processed/report_risks.csv",
    report_mtime: float = 0.0,
) -> pd.DataFrame:
    del report_mtime
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=REPORT_RISK_COLUMNS)

    risks = pd.read_csv(path, dtype={"stock_code": str, "rcept_no": str})
    for column in REPORT_RISK_COLUMNS:
        if column not in risks.columns:
            risks[column] = ""
    risks["stock_code"] = risks["stock_code"].astype(str).str.zfill(6)
    risks["year"] = pd.to_numeric(risks["year"], errors="coerce").astype("Int64")
    risks["report_year"] = pd.to_numeric(risks["report_year"], errors="coerce").astype("Int64")
    return risks[REPORT_RISK_COLUMNS]


def load_report_coverage(
    path: str | Path = "data/processed/report_risk_coverage.csv",
    report_mtime: float = 0.0,
) -> pd.DataFrame:
    del report_mtime
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=REPORT_COVERAGE_COLUMNS)

    coverage = pd.read_csv(path, dtype={"stock_code": str})
    for column in REPORT_COVERAGE_COLUMNS:
        if column not in coverage.columns:
            coverage[column] = ""
    coverage["stock_code"] = coverage["stock_code"].astype(str).str.zfill(6)
    coverage["year"] = pd.to_numeric(coverage["year"], errors="coerce").astype("Int64")
    coverage["report_year"] = pd.to_numeric(coverage["report_year"], errors="coerce").astype("Int64")
    coverage["reports_found"] = pd.to_numeric(
        coverage["reports_found"], errors="coerce"
    ).fillna(0).astype(int)
    coverage["snippets_found"] = pd.to_numeric(
        coverage["snippets_found"], errors="coerce"
    ).fillna(0).astype(int)
    return coverage[REPORT_COVERAGE_COLUMNS]


def summarize_report_risks(
    report_risks: pd.DataFrame,
    stock_code: str,
    analysis_year: int,
    report_coverage: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, str]:
    prior_year = int(analysis_year) - 1
    coverage_message = _coverage_message(report_coverage, stock_code, prior_year)
    if report_risks.empty:
        return report_risks.copy(), coverage_message or _missing_report_message(analysis_year)

    selected = report_risks[
        (report_risks["stock_code"].astype(str).str.zfill(6) == str(stock_code).zfill(6))
        & (report_risks["report_year"].astype("Int64") == prior_year)
    ].copy()
    if selected.empty:
        return selected, coverage_message or _missing_company_message(prior_year)

    risk_counts = selected["risk_type"].fillna("기타").value_counts()
    top_types = ", ".join(f"{risk_type} {count}건" for risk_type, count in risk_counts.head(3).items())
    message = (
        f"전기({prior_year}년) 공시 텍스트에서 {len(selected):,}개의 리스크 문구를 찾았습니다. "
        f"주요 유형은 {top_types}입니다. 당해년도 감사계획에서는 재무제표 지표로 포착된 영역과 "
        "전기 공시에서 반복적으로 언급된 위험 문구가 연결되는지 우선 확인합니다."
    )
    return selected.sort_values(["risk_type", "keyword"]), message


def _coverage_message(
    report_coverage: pd.DataFrame | None,
    stock_code: str,
    prior_year: int,
) -> str:
    if report_coverage is None or report_coverage.empty:
        return ""
    selected = report_coverage[
        (report_coverage["stock_code"].astype(str).str.zfill(6) == str(stock_code).zfill(6))
        & (report_coverage["report_year"].astype("Int64") == prior_year)
    ].copy()
    if selected.empty:
        return ""

    row = selected.sort_values("snippets_found", ascending=False).iloc[0]
    reports_found = int(row.get("reports_found", 0) or 0)
    snippets_found = int(row.get("snippets_found", 0) or 0)
    if snippets_found > 0:
        return ""
    if reports_found > 0:
        return (
            f"전기({prior_year}년) 사업보고서/감사보고서 원문 {reports_found}건을 수집했지만, "
            "현재 키워드 기준으로는 리스크 문구가 탐지되지 않았습니다. 이는 위험이 없다는 결론이 아니라, "
            "공시 텍스트에서 사전에 정의한 위험 키워드가 뚜렷하게 반복되지 않았다는 의미입니다."
        )
    return (
        f"전기({prior_year}년) 사업보고서/감사보고서 목록을 조회했지만 대상 보고서를 찾지 못했습니다. "
        "상장폐지, 합병, 종목코드 변경, 보고서 제출 시점 차이 또는 DART 조회 조건의 영향일 수 있습니다."
    )


def _missing_report_message(analysis_year: int) -> str:
    prior_year = int(analysis_year) - 1
    return (
        f"아직 전기({prior_year}년) 사업보고서/감사보고서 텍스트 리스크 데이터가 없습니다. "
        "`scripts/collect_dart_report_risks.py`로 DART 원문을 수집하면 이 영역에 전기 리스크 문구가 자동 표시됩니다."
    )


def _missing_company_message(prior_year: int) -> str:
    return (
        f"수집된 텍스트 데이터 안에서 전기({prior_year}년) 해당 회사의 리스크 문구를 찾지 못했습니다. "
        "공시 원문이 없거나 키워드 기반 탐지에 걸리지 않은 경우입니다."
    )
