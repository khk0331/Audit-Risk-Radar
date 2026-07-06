from __future__ import annotations

from pathlib import Path

import pandas as pd


FOCUS_COLUMNS = [
    "issue_id",
    "year",
    "source_agency",
    "issue_name",
    "related_accounts",
    "description",
    "trigger_features",
    "company_applicability",
    "audit_implication",
    "reference_note",
]

DEFAULT_FOCUS_PATH = Path("data/reference/regulatory_focus_issues.csv")


def load_regulatory_focus_issues(path: str | Path = DEFAULT_FOCUS_PATH) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=FOCUS_COLUMNS)
    issues = pd.read_csv(path)
    for column in FOCUS_COLUMNS:
        if column not in issues.columns:
            issues[column] = ""
    issues["year"] = pd.to_numeric(issues["year"], errors="coerce").astype("Int64")
    return issues[FOCUS_COLUMNS]


def match_regulatory_focus_issues(
    row: pd.Series,
    issues: pd.DataFrame | None = None,
    min_strength: float = 0.35,
) -> pd.DataFrame:
    issues = load_regulatory_focus_issues() if issues is None else issues.copy()
    if issues.empty:
        return pd.DataFrame(columns=_result_columns())

    matches = []
    for issue in issues.itertuples(index=False):
        features = _parse_features(getattr(issue, "trigger_features", ""))
        strength, signals = _match_strength(row, features)
        if strength < min_strength:
            continue
        matches.append(
            {
                "issue_name": issue.issue_name,
                "source_year": int(issue.year) if pd.notna(issue.year) else "",
                "source_agency": issue.source_agency,
                "match_strength": round(strength * 100, 0),
                "matched_signal": "; ".join(signals),
                "related_accounts": issue.related_accounts,
                "description": issue.description,
                "audit_implication": issue.audit_implication,
                "reference_note": issue.reference_note,
            }
        )

    result = pd.DataFrame(matches, columns=_result_columns())
    if result.empty:
        return result
    return result.sort_values(["match_strength", "source_year"], ascending=[False, False])


def summarize_focus_matches(matches: pd.DataFrame) -> str:
    if matches.empty:
        return (
            "현재 선택 회사의 공시 재무제표 지표만으로는 등록된 감리 테마와 강하게 연결되는 항목이 없습니다. "
            "다만 실제 감사계획에서는 업종, 주석, 사업보고서, 내부통제 이해 결과에 따라 별도 고려가 필요합니다."
        )
    top = matches.iloc[0]
    return (
        f"등록된 감리 테마 중 `{top['issue_name']}`와 가장 강하게 연결됩니다. "
        f"주요 근거는 {top['matched_signal']}입니다."
    )


def _result_columns() -> list[str]:
    return [
        "issue_name",
        "source_year",
        "source_agency",
        "match_strength",
        "matched_signal",
        "related_accounts",
        "description",
        "audit_implication",
        "reference_note",
    ]


def _parse_features(value: object) -> list[str]:
    return [
        item.strip().lower()
        for item in str(value or "").split(",")
        if item.strip()
    ]


def _match_strength(row: pd.Series, features: list[str]) -> tuple[float, list[str]]:
    if not features:
        return 0.0, []

    scores = []
    signals = []
    for feature in features:
        value = row.get(feature)
        score, signal = _feature_score(feature, value)
        scores.append(score)
        if signal:
            signals.append(signal)

    if not scores:
        return 0.0, signals

    # Use the strongest signal as the anchor, with a small lift when multiple signals fire.
    strength = max(scores)
    if sum(score >= 0.35 for score in scores) >= 2:
        strength = min(1.0, strength + 0.12)
    return strength, signals


def _feature_score(feature: str, value: object) -> tuple[float, str]:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return 0.0, ""

    value = float(numeric)
    if feature == "tata":
        if value >= 0.08:
            return 0.95, f"TATA {value:.2f}: 순이익과 영업현금흐름 괴리 큼"
        if value >= 0.05:
            return 0.65, f"TATA {value:.2f}: 발생액 품질 관찰 필요"
        return 0.0, ""

    thresholds = {
        "dsri": (1.20, 1.35, "DSRI", "매출 대비 매출채권 증가"),
        "gmi": (1.10, 1.25, "GMI", "매출총이익률 악화"),
        "aqi": (1.10, 1.25, "AQI", "자산성 항목 비중 증가"),
        "sgi": (1.20, 1.50, "SGI", "매출 고성장"),
        "sgai": (1.10, 1.25, "SGAI", "매출 대비 비용 부담 증가"),
        "lvgi": (1.10, 1.25, "LVGI", "레버리지 부담 증가"),
    }
    if feature not in thresholds:
        return 0.0, ""
    watch, high, label, meaning = thresholds[feature]
    if value >= high:
        return 0.90, f"{label} {value:.2f}: {meaning} 강함"
    if value >= watch:
        return 0.58, f"{label} {value:.2f}: {meaning} 관찰"
    return 0.0, ""
