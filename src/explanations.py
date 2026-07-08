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


def _dominant_focus_area(features: list[str]) -> str:
    if not features:
        return "재무비율 조합과 peer 대비 이례성"
    areas = [AUDIT_FOCUS[feature]["area"] for feature in features if feature in AUDIT_FOCUS]
    return ", ".join(dict.fromkeys(areas[:3])) if areas else "재무비율 조합과 peer 대비 이례성"


def _feature_direction(feature: str, value: object) -> str:
    if pd.isna(value):
        return "산출 불가"
    value = float(value)
    if feature == "tata":
        if value >= 0.08:
            return "강한 발생액 신호"
        if value >= 0.05:
            return "주의가 필요한 발생액 신호"
        return "낮은 발생액 신호"
    if value >= 1.25:
        return "뚜렷한 상승 신호"
    if value >= 1.10:
        return "관찰 필요한 상승 신호"
    if value <= 0.90:
        return "하락 방향의 변동"
    return "중립권"


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
        f"**요약:** Accounting Risk는 {_format_number(score)}점으로 `{_risk_band(score)}` 수준입니다. 이 점수는 회계비율 자체가 전통적인 재무제표 red flag와 얼마나 닮았는지를 보여줍니다.",
        f"**M-Score 관점:** M-Score는 {_format_number(row.get('m_score'))}입니다. 전통적으로 `-2.22`보다 높으면 주의 신호로 보지만, 여기서는 단독 판단이 아니라 매출채권, 수익성, 발생액, 레버리지 신호를 함께 읽기 위한 기준점입니다.",
    ]

    if features:
        lines.append("**핵심 기여 지표:**")
        for feature in features:
            detail = FEATURE_DETAIL[feature]
            lines.append(
                f"- **{detail['label']} {_feature_value(feature, row)} · {_feature_direction(feature, row.get(feature))}**: {detail['meaning']} {detail['risk']}"
            )
    else:
        lines.append(
            "**핵심 기여 지표:** 뚜렷하게 튀는 단일 지표는 없지만, 여러 비율의 조합이 종합 점수에 반영됐습니다."
        )

    lines.append(
        "**감사적 의미:** 이 점수가 높으면 매출 인식, 매출채권 회수가능성, 자산화/손상, 발생액 품질처럼 경영진 판단이 개입되는 계정 영역을 더 깊게 이해해야 합니다. 공시자료 단계에서는 결론보다 `어느 계정에 질문을 던질지`를 정하는 신호로 사용하는 것이 적절합니다."
    )
    return "\n".join(lines)


def explain_peer_layer(row: pd.Series) -> str:
    score = row.get("peer_risk_score")
    matched_size = int(row.get("matched_peer_group_size", 0) or 0)
    top_z = _top_peer_z_features(row)
    lines = [
        f"**요약:** Peer Risk는 {_format_number(score)}점으로 `{_risk_band(score)}` 수준입니다. 같은 Year/Industry뿐 아니라 규모, 수익성, 성장성이 비슷한 matched peer와 비교해 회사가 얼마나 다른 방향으로 움직였는지 봅니다.",
        f"**비교 근거:** Industry 기준 이례성 raw score는 {_format_number(row.get('industry_peer_risk_raw'))}, matched peer 기준 raw score는 {_format_number(row.get('matched_peer_risk_raw'))}입니다. 현재 matched peer group size는 {matched_size}개입니다. peer 분포가 지나치게 좁을 때 과대경고가 발생하지 않도록 개별 지표의 peer z-score는 일정 범위에서 cap 처리합니다.",
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
                f"- **{detail['label']} peer signal {z_value:.2f}**: 유사 회사 대비 {direction} 방향으로 벗어났습니다. {implication}"
            )
    else:
        lines.append(
            "**Peer 대비 크게 다른 지표:** peer z-score가 충분히 산출되지 않아 Industry/Year 분포 기반의 종합 이례성만 참고합니다."
        )

    lines.append(
        "**감사적 의미:** Peer Risk가 높으면 회사 자체의 전년 대비 변화만으로 설명을 끝내기 어렵습니다. 동종·유사 규모 회사와 다른 회계 추정, 수익구조, 운전자본 정책이 있는지 공시 설명과 함께 확인해야 합니다."
    )
    return "\n".join(lines)


def explain_ml_layer(row: pd.Series) -> str:
    score = row.get("ml_risk_score")
    imputed_count = int(row.get("feature_imputed_count", 0) or 0)
    imputed_features = row.get("imputed_features", "")
    lines = [
        f"**요약:** ML Risk는 {_format_number(score)}점으로 `{_risk_band(score)}` 수준입니다. 여러 재무비율을 한꺼번에 봤을 때, 이 회사가 과거/동종 기업의 일반적인 패턴과 얼마나 다르게 움직이는지를 보는 점수입니다.",
        f"**모델 신호:** Isolation Forest signal은 {_format_number(row.get('isolation_risk_raw'))}, PCA error는 {_format_number(row.get('pca_reconstruction_error'))}입니다. 쉽게 말해, 전자는 `주변 회사들과 다른 정도`, 후자는 `일반적인 재무비율 조합으로 설명하기 어려운 정도`를 나타냅니다.",
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
        "**감사적 의미:** ML Risk는 원인을 직접 단정하지 않습니다. 대신 재무비율 여러 개를 함께 볼 때 어색한 조합을 알려줍니다. 따라서 Accounting/Peer 설명과 겹치는 계정 영역을 우선 질문 후보로 삼는 것이 적절합니다. 모델 점수가 높지만 회계적 설명이 약하면, 먼저 데이터 품질과 peer 구성의 적정성을 확인해야 합니다."
    )
    return "\n".join(lines)


def detailed_risk_analysis(row: pd.Series) -> str:
    triggered = get_triggered_features(row)
    top_features = _top_accounting_features(row, limit=3)
    dominant_layer = _dominant_risk_layer(row)
    if pd.notna(row.get("risk_level")):
        risk_level = row.get("risk_level")
    elif row.get("final_risk_score", 0) >= 70:
        risk_level = "High"
    elif row.get("final_risk_score", 0) >= 40:
        risk_level = "Watch"
    else:
        risk_level = "Normal"

    focus_area = _dominant_focus_area(top_features)
    summary = [
        f"**한 줄 결론:** {row['company_name']}의 Final Risk는 {_format_number(row.get('final_risk_score'))}점이며, 현재 공시 재무제표 기준으로 `{risk_level}` 수준의 감사계획 분석 신호를 보입니다.",
        f"**가장 중요한 해석:** 가장 크게 기여한 리스크 축은 **{dominant_layer}**이고, 특히 이해해야 할 계정 영역은 **{focus_area}**입니다. 이 결과는 부정 판단이 아니라 `어디에 감사 질문을 집중할지`를 정하는 planning signal입니다.",
    ]

    if top_features:
        summary.append("**핵심 원인 3가지:**")
        for feature in top_features:
            detail = FEATURE_DETAIL[feature]
            value = _format_number(row.get(feature))
            peer_z = _format_number(row.get(f"{feature}_peer_z"))
            summary.append(
                f"- **{detail['label']} {value} · {_feature_direction(feature, row.get(feature))}**: {detail['meaning']} "
                f"동일 Year/Industry 기준 peer z-score는 {peer_z}입니다. {detail['risk']}"
            )
    else:
        summary.append(
            "**핵심 원인:** 단일 Beneish-style 지표가 크게 튀었다기보다는 여러 지표가 함께 움직인 복합 패턴이 ML/Peer 점수에 반영된 것으로 보입니다."
        )

    summary.extend(
        [
            "**읽는 순서:**",
            "- 먼저 Final Risk가 높은 이유를 Accounting, Peer, ML 중 어느 축이 끌어올렸는지 확인합니다.",
            "- 다음으로 핵심 지표가 전년 대비 변화인지, peer 대비 이례성인지, 또는 두 가지가 동시에 나타나는지 구분합니다.",
            "- 마지막으로 공시 주석과 사업보고서 설명이 해당 변화의 경제적 원인을 충분히 설명하는지 확인합니다.",
            "**감사계획 시사점:** 공시자료만으로 원장·전표 수준의 결론을 낼 수는 없습니다. 대신 이 분석은 매출채권, 수익 인식, 발생액, 자산 건전성, 레버리지 중 어느 영역을 먼저 질문할지 정리해주는 사전 검토 도구입니다.",
        ]
    )
    return "\n".join(summary)


def recommend_audit_steps(row: pd.Series) -> list[str]:
    triggered = get_triggered_features(row)
    if not triggered:
        return [
            "복수 지표가 함께 움직인 원인을 파악하기 위해 전년 대비 주요 재무비율 변동 원인을 경영진 설명과 대조합니다.",
            "동일 Industry 내 유사 기업과 비교하여 해당 변동이 산업 전반의 현상인지 개별 회사 고유 리스크인지 구분합니다.",
            "Final Risk가 높은 경우 주석 공시와 사업보고서 내 경영진 설명을 더 자세히 확인하고, 내부자료 접근이 가능한 감사 단계에서는 관련 계정 영역을 후속 확인 후보로 둡니다.",
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
