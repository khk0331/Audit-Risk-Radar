from __future__ import annotations

import numpy as np
import pandas as pd


PEER_DISPLAY_COLUMNS = [
    "company_name",
    "stock_code",
    "industry",
    "peer_similarity",
    "revenue",
    "total_assets",
    "operating_margin",
    "gross_margin",
    "sgi",
    "final_risk_score",
]


def select_representative_peers(
    scored: pd.DataFrame,
    target_row: pd.Series,
    max_peers: int = 8,
) -> pd.DataFrame:
    # These peers are displayed to the user, so the goal is interpretability:
    # choose a small set of close comparables, then show why they were selected.
    candidates = rank_peer_candidates(scored, target_row)
    if candidates.empty:
        return pd.DataFrame(columns=PEER_DISPLAY_COLUMNS + ["peer_reason"])

    peers = candidates.sort_values(["peer_distance", "final_risk_score"], ascending=[True, False]).head(max_peers)
    for column in PEER_DISPLAY_COLUMNS:
        if column not in peers.columns:
            peers[column] = np.nan
    return peers[PEER_DISPLAY_COLUMNS + ["peer_reason"]].copy()


def matched_peer_indices(scored: pd.DataFrame, target_row: pd.Series, max_peers: int = 12) -> list:
    candidates = rank_peer_candidates(scored, target_row, include_reasons=False)
    if candidates.empty:
        return []
    return candidates.sort_values("peer_distance").head(max_peers).index.tolist()


def rank_peer_candidates(
    scored: pd.DataFrame,
    target_row: pd.Series,
    include_reasons: bool = True,
) -> pd.DataFrame:
    # Peer selection starts from the same year. This keeps macro conditions and
    # reporting periods aligned before comparing industry, scale, profitability,
    # and growth.
    year = int(target_row["year"])
    candidates = scored[
        (scored["year"].astype(int) == year)
        & (scored["stock_code"].astype(str) != str(target_row["stock_code"]))
    ].copy()
    if candidates.empty:
        return candidates

    target = target_row.copy()
    candidates["operating_margin"] = _safe_divide(
        pd.to_numeric(candidates.get("operating_income"), errors="coerce"),
        pd.to_numeric(candidates.get("revenue"), errors="coerce"),
    )
    target_operating_margin = _safe_scalar_divide(target.get("operating_income"), target.get("revenue"))
    gross_margin = _numeric_column(candidates, "gross_margin", default=0.0)
    target_gross_margin = _safe_numeric(target.get("gross_margin"), default=0.0)
    sgi = _numeric_column(candidates, "sgi", default=1.0)
    target_sgi = _safe_numeric(target.get("sgi"), default=1.0)

    candidates["industry_match"] = (candidates["industry"] == target["industry"]).astype(float)
    candidates["industry_code_match"] = _industry_prefix_match(candidates, target)
    candidates["size_distance"] = _ranked_distance(
        _log_distance(candidates["revenue"], target.get("revenue"))
        + _log_distance(candidates["total_assets"], target.get("total_assets"))
    )
    candidates["profit_distance"] = _ranked_distance(
        (gross_margin - target_gross_margin).abs()
        + (candidates["operating_margin"] - target_operating_margin).abs()
    )
    candidates["growth_distance"] = _ranked_distance((sgi - target_sgi).abs())

    # Weighting reflects practical comparability logic used in planning and
    # valuation-style peer selection: industry fit first, then size and operating
    # profile. The weights are transparent heuristics, not trained coefficients.
    candidates["peer_distance"] = (
        0.36 * (1 - candidates["industry_match"])
        + 0.14 * (1 - candidates["industry_code_match"])
        + 0.28 * candidates["size_distance"]
        + 0.14 * candidates["profit_distance"]
        + 0.08 * candidates["growth_distance"]
    )
    candidates["peer_similarity"] = ((1 - candidates["peer_distance"]).clip(0, 1) * 100).round(1)
    if include_reasons:
        candidates["peer_reason"] = candidates.apply(_peer_reason, axis=1)
    return candidates


def peer_methodology_note(target_row: pd.Series, peers: pd.DataFrame) -> str:
    if peers.empty:
        return (
            "현재 패널에서 같은 Year 기준 비교 가능한 peer 후보가 부족합니다. "
            "해당 회사 분석의 신뢰도를 높이려면 DART에서 동종/유사 규모 회사를 추가 수집해야 합니다."
        )

    same_industry = int((peers["industry"] == target_row["industry"]).sum())
    return (
        f"대표 peer는 {int(target_row['year'])}년 기준으로 업종 유사성, 매출/총자산 규모, "
        f"수익성, 성장성을 함께 고려해 산정했습니다. 표시된 {len(peers)}개 peer 중 "
        f"{same_industry}개가 동일 Industry입니다. 현재 데이터에는 시장구분/시가총액이 없으므로 "
        "시장 변수는 향후 KRX 또는 DART 기업개황 데이터가 확장되면 가중치에 반영하는 구조가 적절합니다."
    )


def _industry_prefix_match(candidates: pd.DataFrame, target: pd.Series) -> pd.Series:
    if "industry_code" not in candidates.columns or "industry_code" not in target.index:
        return pd.Series(0.0, index=candidates.index)
    target_prefix = str(target.get("industry_code", "") or "")[:2]
    if not target_prefix:
        return pd.Series(0.0, index=candidates.index)
    return candidates["industry_code"].fillna("").astype(str).str[:2].eq(target_prefix).astype(float)


def _log_distance(series: pd.Series, target_value: object) -> pd.Series:
    target = pd.to_numeric(pd.Series([target_value]), errors="coerce").iloc[0]
    values = pd.to_numeric(series, errors="coerce")
    if pd.isna(target) or target <= 0:
        return pd.Series(0.0, index=series.index)
    return (np.log1p(values.clip(lower=0)) - np.log1p(target)).abs().fillna(0.0)


def _ranked_distance(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    fill_value = values.median()
    if pd.isna(fill_value):
        fill_value = 0.0
    values = values.fillna(fill_value)
    if values.nunique(dropna=True) <= 1:
        return pd.Series(0.0, index=series.index)
    return values.rank(pct=True).clip(0, 1)


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    return numerator / denominator


def _safe_scalar_divide(numerator: object, denominator: object) -> float:
    numerator_value = pd.to_numeric(pd.Series([numerator]), errors="coerce").iloc[0]
    denominator_value = pd.to_numeric(pd.Series([denominator]), errors="coerce").iloc[0]
    if pd.isna(numerator_value) or pd.isna(denominator_value) or denominator_value == 0:
        return 0.0
    return float(numerator_value / denominator_value)


def _numeric_column(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in df.columns:
        return pd.Series(default, index=df.index)
    return pd.to_numeric(df[column], errors="coerce").fillna(default)


def _safe_numeric(value: object, default: float = 0.0) -> float:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return default
    return float(numeric)


def _peer_reason(row: pd.Series) -> str:
    reasons = []
    if row.get("industry_match", 0) == 1:
        reasons.append("동일 Industry")
    elif row.get("industry_code_match", 0) == 1:
        reasons.append("유사 산업코드")
    else:
        reasons.append("규모/수익성 유사")
    if row.get("size_distance", 1) <= 0.35:
        reasons.append("규모 유사")
    if row.get("profit_distance", 1) <= 0.35:
        reasons.append("수익성 유사")
    if row.get("growth_distance", 1) <= 0.35:
        reasons.append("성장성 유사")
    return ", ".join(reasons)
