from __future__ import annotations

import pandas as pd


DRIVER_LABELS = {
    "dsri": "매출 대비 매출채권 증가 속도가 높습니다",
    "gmi": "매출총이익률이 악화되었습니다",
    "aqi": "자산의 질이 약화되는 흐름이 있습니다",
    "sgi": "매출 성장률이 이례적으로 높습니다",
    "sgai": "영업비용 부담이 증가했습니다",
    "lvgi": "레버리지 부담이 커졌습니다",
    "tata": "총자산 대비 발생액 비중이 높습니다",
}

FEATURE_DETAIL = {
    "dsri": {
        "label": "DSRI",
        "meaning": "매출 대비 매출채권이 전년보다 빠르게 증가했다는 신호입니다.",
        "risk": "매출은 인식됐지만 현금 회수가 뒤따르지 않거나, 기말 매출 인식 시점에 판단이 많이 개입됐을 가능성을 우선 살펴봅니다.",
    },
    "gmi": {
        "label": "GMI",
        "meaning": "매출총이익률이 전년보다 악화됐다는 신호입니다.",
        "risk": "수익성이 악화된 회사는 목표 이익을 맞추기 위한 매출 인식, 원가 배분, 재고평가 판단 압력이 커질 수 있습니다.",
    },
    "aqi": {
        "label": "AQI",
        "meaning": "총자산 중 유동자산과 유형자산으로 설명되지 않는 자산 비중이 커졌다는 신호입니다.",
        "risk": "비용의 자산화, 무형자산/기타자산 증가, 손상검토 가정의 적정성을 공시자료와 함께 확인할 필요가 있습니다.",
    },
    "sgi": {
        "label": "SGI",
        "meaning": "매출 성장률이 전년 대비 높다는 신호입니다.",
        "risk": "고성장은 그 자체로 오류가 아니지만, 매출채권과 현금흐름이 함께 뒷받침되는지 확인해야 합니다.",
    },
    "sgai": {
        "label": "SGAI",
        "meaning": "매출 대비 판매관리비성 비용 부담이 커졌다는 신호입니다.",
        "risk": "영업효율 악화, 비용의 기간 귀속, 비용 자본화 판단이 수익성 설명과 일관되는지 살펴봅니다.",
    },
    "lvgi": {
        "label": "LVGI",
        "meaning": "총자산 대비 부채 부담이 전년보다 커졌다는 신호입니다.",
        "risk": "차입약정, 유동성, 계속기업 불확실성, 재무비율 관리 압력이 재무제표 판단에 영향을 줄 수 있습니다.",
    },
    "tata": {
        "label": "TATA",
        "meaning": "순이익과 영업현금흐름 사이의 괴리가 커졌다는 신호입니다.",
        "risk": "이익이 현금흐름으로 뒷받침되지 않는 경우 발생액, 충당부채, 운전자본 계정의 품질을 확인해야 합니다.",
    },
}

AUDIT_FOCUS = {
    "dsri": {
        "area": "매출채권 및 수익 인식",
        "question": "매출 성장보다 매출채권이 더 빠르게 증가한 이유가 무엇인가?",
        "procedure": "공시자료상 매출채권 증가율, 현금흐름, 대손충당금 추이를 우선 비교합니다. 내부자료 접근이 가능한 감사 단계에서는 기말 전후 매출 cut-off와 주요 채권 회수 여부를 후속 확인 후보로 둘 수 있습니다.",
        "basis": "ISA 315/330/500/520, IFRS 15",
    },
    "gmi": {
        "area": "매출총이익률 및 원가 구조",
        "question": "매출총이익률 악화가 정상적인 원가 상승 때문인지, 매출/원가 인식 오류 때문인지 확인했는가?",
        "procedure": "공시자료상 매출총이익률, 재고자산, 매출원가 변동을 전년 및 Industry와 비교합니다. 내부자료 접근이 가능한 감사 단계에서는 제품군별 원가 구조와 재고평가 관련 근거를 후속 확인 후보로 둘 수 있습니다.",
        "basis": "ISA 315/330/500/520, IAS 2",
    },
    "aqi": {
        "area": "자산 건전성",
        "question": "비유동/기타자산 증가가 미래 효익이 있는 자산인지, 비용의 자산화 가능성은 없는가?",
        "procedure": "공시자료상 무형자산·유형자산·기타비유동자산 증가와 손상 관련 주석을 우선 확인합니다. 내부자료 접근이 가능한 감사 단계에서는 자본적 지출 판단 근거와 손상검토 가정을 후속 확인 후보로 둘 수 있습니다.",
        "basis": "ISA 315/330/500, IAS 16/36/38",
    },
    "sgi": {
        "area": "고성장 매출",
        "question": "이례적인 매출 성장이 실제 영업활동에 의해 뒷받침되는가?",
        "procedure": "공시자료상 매출 성장률, 영업현금흐름, 매출채권 증가율이 함께 설명되는지 확인합니다. 내부자료 접근이 가능한 감사 단계에서는 신규 거래, 특수관계자 거래, 계약조건 변경 여부를 후속 확인 후보로 둘 수 있습니다.",
        "basis": "ISA 240/315/330/500/520, IFRS 15",
    },
    "sgai": {
        "area": "판관비 및 영업비용",
        "question": "영업비용 부담 증가가 일시적 요인인지, 수익성 악화 신호인지 확인했는가?",
        "procedure": "공시자료상 판관비율, 영업이익률, 일회성 비용 설명을 전년 및 Industry와 비교합니다. 내부자료 접근이 가능한 감사 단계에서는 비용의 기간 귀속과 비용 자본화 판단 근거를 후속 확인 후보로 둘 수 있습니다.",
        "basis": "ISA 315/330/500/520, IAS 1",
    },
    "lvgi": {
        "area": "레버리지 및 유동성",
        "question": "부채 부담 증가가 계속기업, 차입약정, 유동성 리스크에 영향을 주는가?",
        "procedure": "공시자료상 부채비율, 유동성, 차입금 만기, 이자비용 및 계속기업 관련 주석을 우선 확인합니다. 내부자료 접근이 가능한 감사 단계에서는 차환 계획과 재무약정 준수 여부를 후속 확인 후보로 둘 수 있습니다.",
        "basis": "ISA 315/330/500/570, IAS 1/IFRS 7",
    },
    "tata": {
        "area": "발생액 품질",
        "question": "순이익과 영업현금흐름의 괴리가 정상적인 운전자본 변화로 설명되는가?",
        "procedure": "공시자료상 순이익, 영업현금흐름, 운전자본 변동의 괴리를 우선 분석합니다. 내부자료 접근이 가능한 감사 단계에서는 비현금성 발생액, 충당부채, 미수·미지급 계정 관련 근거를 후속 확인 후보로 둘 수 있습니다.",
        "basis": "ISA 315/330/500/520/540, IAS 37",
    },
}


def get_triggered_features(row: pd.Series) -> list[str]:
    triggered = []
    for feature in DRIVER_LABELS:
        value = row.get(feature)
        if pd.notna(value) and value > 1.25:
            triggered.append(feature)
    if pd.notna(row.get("tata")) and row.get("tata") > 0.08 and "tata" not in triggered:
        triggered.append("tata")
    return triggered


def explain_row(row: pd.Series) -> str:
    drivers = [DRIVER_LABELS[feature] for feature in get_triggered_features(row)]

    if not drivers:
        drivers.append("단일 지표보다 여러 재무비율의 조합에서 비정상성이 관찰됩니다")

    driver_text = ", ".join(drivers[:3])
    return (
        f"{row['company_name']}은(는) {driver_text}. "
        "이는 분식 판단이 아니라 감사 계획 단계에서 추가 검토가 필요한 위험 신호로 해석해야 합니다."
    )


def _format_number(value: object) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.2f}"


def _dominant_risk_layer(row: pd.Series) -> str:
    layers = {
        "Accounting Risk": row.get("accounting_risk_score"),
        "Peer Risk": row.get("peer_risk_score"),
        "ML Risk": row.get("ml_risk_score"),
    }
    valid_layers = {key: value for key, value in layers.items() if pd.notna(value)}
    if not valid_layers:
        return "복합 리스크"
    return max(valid_layers, key=valid_layers.get)


def _risk_band(score: object) -> str:
    if pd.isna(score):
        return "산출 불가"
    score = float(score)
    if score >= 70:
        return "높음"
    if score >= 40:
        return "관찰 필요"
    return "상대적으로 낮음"


def _feature_value(feature: str, row: pd.Series) -> str:
    value = row.get(feature)
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.2f}"


def _top_accounting_features(row: pd.Series, limit: int = 4) -> list[str]:
    triggered = get_triggered_features(row)
    if triggered:
        return triggered[:limit]

    candidates = []
    for feature in DRIVER_LABELS:
        value = row.get(feature)
        if pd.isna(value):
            continue
        if feature == "tata":
            severity = abs(float(value)) / 0.08
        else:
            severity = abs(float(value) - 1.0)
        candidates.append((severity, feature))
    return [feature for _, feature in sorted(candidates, reverse=True)[:limit]]


def _top_peer_z_features(row: pd.Series, limit: int = 4) -> list[tuple[str, float]]:
    values = []
    for feature in DRIVER_LABELS:
        z_value = row.get(f"{feature}_peer_z")
        if pd.notna(z_value):
            values.append((feature, float(z_value)))
    return sorted(values, key=lambda item: abs(item[1]), reverse=True)[:limit]


def explain_accounting_layer(row: pd.Series) -> str:
    score = row.get("accounting_risk_score")
    features = _top_accounting_features(row)
    lines = [
        f"**점수 의미:** Accounting Risk는 {_format_number(score)}점으로 `{_risk_band(score)}` 수준입니다. Beneish-style 지표와 M-Score를 이용해 전통적인 재무제표 이상징후와 유사한 패턴이 있는지 봅니다.",
        f"**핵심 원인:** M-Score는 {_format_number(row.get('m_score'))}입니다. 전통적으로 -2.22보다 높으면 조작 가능성 신호로 참고하지만, 이 프로젝트에서는 단독 결론이 아니라 다른 지표와 함께 우선순위를 정하는 입력값으로 사용합니다.",
    ]

    if features:
        lines.append("**주요 기여 지표:**")
        for feature in features:
            detail = FEATURE_DETAIL[feature]
            lines.append(
                f"- **{detail['label']} {_feature_value(feature, row)}**: {detail['meaning']} {detail['risk']}"
            )
    else:
        lines.append(
            "**주요 기여 지표:** 뚜렷하게 튀는 단일 지표는 없지만, 여러 비율의 조합이 종합 점수에 반영됐습니다."
        )

    lines.append(
        "**감사적 의미:** 이 점수가 높으면 매출 인식, 매출채권 회수가능성, 자산화/손상, 발생액 품질처럼 경영진 판단이 개입되는 계정 영역을 우선 검토 대상으로 둡니다."
    )
    return "\n".join(lines)


def explain_peer_layer(row: pd.Series) -> str:
    score = row.get("peer_risk_score")
    matched_size = int(row.get("matched_peer_group_size", 0) or 0)
    top_z = _top_peer_z_features(row)
    lines = [
        f"**점수 의미:** Peer Risk는 {_format_number(score)}점으로 `{_risk_band(score)}` 수준입니다. 같은 Year/Industry 비교와 규모·수익성·성장성이 유사한 matched peer 비교에서 얼마나 이례적인지를 봅니다.",
        f"**계산 관점:** Industry 기준 이례성 raw score는 {_format_number(row.get('industry_peer_risk_raw'))}, matched peer 기준 raw score는 {_format_number(row.get('matched_peer_risk_raw'))}입니다. 현재 matched peer group size는 {matched_size}개입니다.",
    ]

    if top_z:
        lines.append("**Peer 대비 크게 다른 지표:**")
        for feature, z_value in top_z:
            detail = FEATURE_DETAIL[feature]
            direction = "높은" if z_value > 0 else "낮은"
            implication = (
                detail["meaning"]
                if z_value > 0
                else "낮은 값이 반드시 위험을 의미하지는 않지만, peer와 다른 방향으로 움직였다는 점에서 원인 설명이 필요합니다."
            )
            lines.append(
                f"- **{detail['label']} z-score {z_value:.2f}**: peer 중앙값 대비 {direction} 방향으로 벗어났습니다. {implication}"
            )
    else:
        lines.append(
            "**Peer 대비 크게 다른 지표:** peer z-score가 충분히 산출되지 않아 Industry/Year 분포 기반의 종합 이례성만 참고합니다."
        )

    lines.append(
        "**감사적 의미:** Peer Risk가 높으면 회사 자체의 변화뿐 아니라 동종·유사 규모 회사와 다른 회계 추정, 수익구조, 운전자본 정책이 있는지 설명이 필요합니다."
    )
    return "\n".join(lines)


def explain_ml_layer(row: pd.Series) -> str:
    score = row.get("ml_risk_score")
    imputed_count = int(row.get("feature_imputed_count", 0) or 0)
    imputed_features = row.get("imputed_features", "")
    lines = [
        f"**점수 의미:** ML Risk는 {_format_number(score)}점으로 `{_risk_band(score)}` 수준입니다. Isolation Forest와 PCA reconstruction error를 함께 사용해 여러 재무비율이 동시에 움직이는 비지도 이상 패턴을 포착합니다.",
        f"**핵심 원인:** Isolation Forest raw signal은 {_format_number(row.get('isolation_risk_raw'))}, PCA reconstruction error는 {_format_number(row.get('pca_reconstruction_error'))}입니다. 두 값이 높을수록 학습된 일반 패턴에서 벗어난 조합이라는 의미입니다.",
    ]

    if imputed_count:
        lines.append(
            f"**데이터 주의:** ML 입력 지표 중 {imputed_count}개가 결측 대체되었습니다. 대체된 지표는 `{imputed_features}`입니다. 이 경우 점수 해석 시 원천 공시 수집 한계를 함께 고려합니다."
        )
    else:
        lines.append(
            "**데이터 주의:** 선택 회사의 ML 입력 지표에서는 결측 대체가 발생하지 않았습니다. 따라서 현재 ML 점수는 결측 보정보다 실제 지표 조합의 이례성을 더 많이 반영합니다."
        )

    lines.append(
        "**감사적 의미:** ML Risk는 원인을 직접 단정하지 않습니다. 대신 사람이 놓치기 쉬운 복합 패턴을 알려주므로, Accounting/Peer 설명과 겹치는 계정 영역을 우선 질문 후보로 삼는 것이 적절합니다."
    )
    return "\n".join(lines)


def detailed_risk_analysis(row: pd.Series) -> str:
    triggered = get_triggered_features(row)
    dominant_layer = _dominant_risk_layer(row)
    if pd.notna(row.get("risk_level")):
        risk_level = row.get("risk_level")
    elif row.get("final_risk_score", 0) >= 70:
        risk_level = "High"
    elif row.get("final_risk_score", 0) >= 40:
        risk_level = "Watch"
    else:
        risk_level = "Normal"

    summary = [
        f"**종합 판단:** {row['company_name']}의 Final Risk는 {_format_number(row.get('final_risk_score'))}점이며, 현재 선택 표본에서 `{risk_level}` 수준의 우선 검토 대상으로 분류됩니다.",
        f"가장 크게 기여한 리스크 축은 **{dominant_layer}**입니다. 이 점수는 부정 판단이 아니라, 감사계획 단계에서 어느 회사와 계정 영역을 먼저 볼지 정하기 위한 신호입니다.",
    ]

    if triggered:
        summary.append("**주요 원인 지표:**")
        for feature in triggered[:5]:
            detail = FEATURE_DETAIL[feature]
            value = _format_number(row.get(feature))
            peer_z = _format_number(row.get(f"{feature}_peer_z"))
            summary.append(
                f"- **{detail['label']} {value}**: {detail['meaning']} "
                f"동일 Year/Industry 기준 peer z-score는 {peer_z}입니다. {detail['risk']}"
            )
    else:
        summary.append(
            "**주요 원인 지표:** 단일 Beneish-style 지표가 크게 튀었다기보다는 여러 지표가 함께 움직인 복합 패턴이 ML/Peer 점수에 반영된 것으로 보입니다."
        )

    summary.extend(
        [
            "**감사인이 읽어야 하는 방향:**",
            "- 매출 성장, 매출채권, 영업현금흐름이 같은 방향으로 설명되는지 먼저 확인합니다.",
            "- 발생액 품질이 낮거나 현금흐름이 약하면 순이익의 지속가능성과 회수가능성을 함께 봅니다.",
            "- Industry 전반 현상인지 회사 고유 이슈인지 구분하기 위해 peer 비교 결과를 함께 해석합니다.",
            "- 내부자료 접근 전 단계에서는 공시 주석, 사업보고서 MD&A, 감사보고서 강조사항/핵심감사사항을 우선 확인하는 것이 적절합니다.",
        ]
    )
    return "\n".join(summary)


def recommend_audit_steps(row: pd.Series) -> list[str]:
    triggered = get_triggered_features(row)
    if not triggered:
        return [
            "복수 지표가 함께 움직인 원인을 파악하기 위해 전년 대비 주요 재무비율 변동 원인을 경영진 설명과 대조합니다.",
            "동일 Industry 내 유사 기업과 비교하여 해당 변동이 산업 전반의 현상인지 개별 회사 고유 리스크인지 구분합니다.",
            "Final Risk가 높은 경우 주석 공시와 사업보고서 내 경영진 설명을 우선 확인하고, 내부자료 접근이 가능한 감사 단계에서는 관련 계정 영역을 후속 확인 후보로 둡니다.",
        ]

    steps = []
    for feature in triggered[:4]:
        focus = AUDIT_FOCUS[feature]
        steps.append(
            f"[{focus['area']}] {focus['question']} {focus['procedure']} "
            f"(근거: {focus['basis']})"
        )
    return steps


def format_audit_steps(row: pd.Series) -> str:
    return "\n".join(f"{idx}. {step}" for idx, step in enumerate(recommend_audit_steps(row), start=1))


def add_explanations(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["risk_explanation"] = result.apply(explain_row, axis=1)
    result["detailed_risk_analysis"] = result.apply(detailed_risk_analysis, axis=1)
    result["accounting_risk_analysis"] = result.apply(explain_accounting_layer, axis=1)
    result["peer_risk_analysis"] = result.apply(explain_peer_layer, axis=1)
    result["ml_risk_analysis"] = result.apply(explain_ml_layer, axis=1)
    result["recommended_audit_steps"] = result.apply(format_audit_steps, axis=1)
    return result
