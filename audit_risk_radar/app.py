from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_financials
from src.event_labels import EVENT_LABEL_COLUMNS, attach_event_labels, load_event_labels
from src.explanations import (
    AUDIT_FOCUS,
    add_explanations,
    detailed_risk_analysis,
    explain_accounting_layer,
    explain_ml_layer,
    explain_peer_layer,
    get_triggered_features,
)
from src.metrics import add_beneish_style_features
from src.peer_selection import peer_methodology_note, select_representative_peers
from src.risk_scoring import score_financials


st.set_page_config(page_title="Audit Risk Radar", layout="wide")

COLORWAY = ["#D8FF64", "#78C6A3", "#E6B86A", "#F2EFE4", "#A7B86B", "#BFA6FF"]
LAYER_LABELS = {
    "accounting_risk_score": "Accounting Risk",
    "peer_risk_score": "Peer Risk",
    "ml_risk_score": "ML Risk",
}
LAYER_HELP = {
    "Final Risk": "Accounting, Peer, ML 점수를 가중 평균한 최종 우선순위 점수입니다. 감사인이 먼저 볼 회사를 정렬하기 위한 지표입니다.",
    "Accounting Risk": "Beneish-style 재무비율을 기반으로 산출한 회계적 Red Flag 점수입니다. 높을수록 전통적 재무제표 조작 징후와 유사한 패턴입니다.",
    "Peer Risk": "동일 Year/Industry 비교와 규모·수익성·성장성이 유사한 matched peer 비교를 함께 반영한 이례성 점수입니다.",
    "ML Risk": "Isolation Forest와 PCA reconstruction error로 계산한 비지도 이상탐지 점수입니다. 여러 지표가 함께 움직이는 복합 패턴을 포착합니다.",
}
DISPLAY_COLUMNS = {
    "stock_code": "종목코드",
    "company_name": "회사명",
    "industry": "Industry",
    "risk_level": "검토 등급",
    "final_risk_score": "Final Risk",
    "accounting_risk_score": "Accounting Risk",
    "peer_risk_score": "Peer Risk",
    "ml_risk_score": "ML Risk",
    "m_score": "M-Score",
    "risk_explanation": "위험 신호 해석",
    "recommended_audit_steps": "추천 감사 질문/절차",
}
FEATURE_LABELS = {
    "dsri": "DSRI",
    "gmi": "GMI",
    "aqi": "AQI",
    "sgi": "SGI",
    "sgai": "SGAI",
    "lvgi": "LVGI",
    "tata": "TATA",
}
RAW_QUALITY_COLUMNS = [
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
RAW_QUALITY_LABELS = {
    "revenue": "매출",
    "receivables": "매출채권",
    "gross_profit": "매출총이익",
    "operating_income": "영업이익",
    "total_assets": "총자산",
    "current_assets": "유동자산",
    "ppe": "유형자산",
    "total_liabilities": "총부채",
    "net_income": "순이익",
    "operating_cash_flow": "영업현금흐름",
}
RISK_LEVEL_HELP = {
    "High": "감사계획 단계에서 우선 검토가 필요한 상위 위험 신호입니다.",
    "Watch": "단일 결론은 어렵지만 추세와 주요 계정 변동을 함께 확인할 필요가 있습니다.",
    "Normal": "현재 표본 내에서는 상대적으로 낮은 우선순위입니다.",
}

px.defaults.color_discrete_sequence = COLORWAY
px.defaults.template = "plotly_dark"

st.markdown(
    """
    <style>
    :root {
        --moss-bg: #070907;
        --moss-panel: #10140F;
        --moss-panel-2: #171D15;
        --moss-forest: #1F3B2C;
        --moss-forest-soft: #223429;
        --moss-lime: #D8FF64;
        --moss-cream: #F2EFE4;
        --moss-paper: #ECE7D8;
        --moss-muted: #B8BAAB;
        --moss-subtle: #858B7D;
        --moss-border: #2D352B;
        --moss-border-2: #3A4536;
        --moss-rust: #E6B86A;
    }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background:
            radial-gradient(circle at 78% 0%, rgba(216, 255, 100, 0.08), transparent 28rem),
            linear-gradient(180deg, #080A08 0%, #070907 62%, #050705 100%);
        color: var(--moss-cream);
    }
    [data-testid="stSidebar"], [data-testid="stToolbar"] {
        background: var(--moss-bg);
    }
    .main .block-container { padding-top: 2rem; max-width: 1280px; }
    h1, h2, h3, h4, h5, h6, p, li, label, span {
        color: var(--moss-cream);
    }
    h1 {
        font-weight: 760;
        letter-spacing: 0;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(23, 29, 21, 0.98), rgba(13, 17, 12, 0.98));
        border: 1px solid var(--moss-border);
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: inset 0 1px 0 rgba(242, 239, 228, 0.04);
    }
    div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--moss-cream);
    }
    .small-note {
        color: var(--moss-muted);
        font-size: 0.86rem;
        line-height: 1.55;
        margin-top: -0.35rem;
    }
    .score-guide {
        border-left: 4px solid var(--moss-lime);
        background: var(--moss-panel);
        border: 1px solid var(--moss-border);
        padding: 0.85rem 1rem;
        border-radius: 6px;
        margin-bottom: 0.6rem;
        min-height: 124px;
    }
    .intro-band {
        background:
            linear-gradient(135deg, rgba(23, 29, 21, 0.98) 0%, rgba(15, 20, 14, 0.98) 54%, rgba(31, 59, 44, 0.92) 100%);
        border: 1px solid var(--moss-border-2);
        border-radius: 8px;
        padding: 1.2rem;
        margin: 0.7rem 0 1.0rem 0;
        box-shadow: 0 22px 60px rgba(0, 0, 0, 0.22), inset 0 1px 0 rgba(242, 239, 228, 0.04);
    }
    .hero-grid {
        display: grid;
        grid-template-columns: minmax(0, 1.15fr) minmax(280px, 0.85fr);
        gap: 1.2rem;
        align-items: stretch;
    }
    .intro-title {
        color: var(--moss-cream);
        font-size: 1.04rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }
    .system-kicker {
        color: var(--moss-lime);
        font-size: 0.78rem;
        font-weight: 760;
        letter-spacing: 0;
        margin-bottom: 0.45rem;
        text-transform: uppercase;
    }
    .hero-title {
        color: var(--moss-cream);
        font-size: 2.15rem;
        line-height: 1.08;
        font-weight: 780;
        margin-bottom: 0.65rem;
    }
    .reference-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.85rem;
    }
    .reference-chip {
        border: 1px solid rgba(242, 239, 228, 0.18);
        border-radius: 999px;
        color: var(--moss-cream);
        background: rgba(7, 9, 7, 0.42);
        padding: 0.33rem 0.62rem;
        font-size: 0.78rem;
        line-height: 1;
    }
    .preview-panel {
        background: var(--moss-paper);
        border: 1px solid rgba(242, 239, 228, 0.32);
        border-radius: 8px;
        color: #182116;
        padding: 1rem;
        min-height: 186px;
        display: grid;
        grid-template-rows: auto 1fr auto;
        box-shadow: inset 0 0 0 1px rgba(24, 33, 22, 0.08);
    }
    .preview-panel * {
        color: #182116;
    }
    .preview-topline {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.72rem;
        font-weight: 760;
        text-transform: uppercase;
        border-bottom: 1px solid rgba(24, 33, 22, 0.12);
        padding-bottom: 0.55rem;
    }
    .preview-number {
        font-size: 2.05rem;
        font-weight: 800;
        margin: 0.75rem 0 0.25rem 0;
        color: #203A2B;
    }
    .preview-bars {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        align-items: end;
        gap: 0.32rem;
        height: 58px;
        margin-top: 0.45rem;
    }
    .preview-bars span {
        display: block;
        background: #203A2B;
        border-radius: 3px 3px 0 0;
    }
    .preview-bars span:nth-child(2n) { background: var(--moss-lime); }
    .preview-foot {
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
        margin-top: 0.8rem;
        font-size: 0.75rem;
        color: #56624C;
    }
    .workflow-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.8rem 0 1.0rem 0;
    }
    .briefing-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.65rem 0 0.95rem 0;
    }
    .briefing-card {
        background: var(--moss-panel);
        border: 1px solid var(--moss-border);
        border-radius: 8px;
        padding: 0.9rem 1rem;
        min-height: 128px;
    }
    .briefing-kicker {
        color: var(--moss-lime);
        font-size: 0.76rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }
    .briefing-value {
        color: var(--moss-cream);
        font-size: 1.02rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }
    .workflow-step {
        background: var(--moss-panel);
        border: 1px solid var(--moss-border);
        border-top: 3px solid var(--moss-lime);
        border-radius: 8px;
        padding: 0.85rem 0.9rem;
        min-height: 112px;
    }
    .step-label {
        color: var(--moss-lime);
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    .step-title {
        color: var(--moss-cream);
        font-size: 0.98rem;
        font-weight: 700;
        margin-bottom: 0.28rem;
    }
    .section-note {
        color: var(--moss-muted);
        font-size: 0.9rem;
        line-height: 1.6;
        margin: -0.35rem 0 0.65rem 0;
    }
    .audit-callout {
        border-left: 4px solid var(--moss-rust);
        background: var(--moss-panel-2);
        border: 1px solid var(--moss-border-2);
        border-radius: 6px;
        padding: 0.8rem 1rem;
        color: var(--moss-cream);
        line-height: 1.55;
        margin: 0.4rem 0 0.9rem 0;
    }
    .risk-analysis {
        background: linear-gradient(180deg, rgba(23, 29, 21, 0.98), rgba(12, 16, 11, 0.98));
        border: 1px solid var(--moss-border-2);
        border-left: 4px solid var(--moss-rust);
        border-radius: 8px;
        padding: 1rem 1.1rem;
        line-height: 1.65;
        color: var(--moss-cream);
        margin: 0.4rem 0 1rem 0;
    }
    .risk-analysis strong {
        color: var(--moss-cream);
    }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        border: 1px solid var(--moss-border);
        border-radius: 8px;
    }
    div[data-baseweb="select"] > div, div[data-baseweb="tag"], div[data-baseweb="slider"] {
        background: var(--moss-panel);
        border-color: var(--moss-border) !important;
        color: var(--moss-cream);
    }
    div[data-baseweb="select"] input,
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {
        color: var(--moss-cream) !important;
    }
    div[data-baseweb="popover"] div,
    div[role="listbox"] div,
    div[role="option"] {
        background: var(--moss-panel) !important;
        color: var(--moss-cream) !important;
    }
    div[role="option"]:hover {
        background: var(--moss-forest-soft) !important;
    }
    input, textarea {
        color: var(--moss-cream) !important;
        background: var(--moss-panel) !important;
    }
    input::placeholder, textarea::placeholder {
        color: var(--moss-subtle) !important;
    }
    .stAlert {
        background: var(--moss-panel);
        color: var(--moss-cream);
    }
    .stButton > button, .stDownloadButton > button {
        background: var(--moss-paper);
        color: #11180F;
        border: 1px solid rgba(216, 255, 100, 0.34);
        border-radius: 8px;
        font-weight: 700;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background: var(--moss-lime);
        color: #11180F;
        border-color: var(--moss-lime);
    }
    @media (max-width: 900px) {
        .hero-grid { grid-template-columns: 1fr; }
        .workflow-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .briefing-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
        .workflow-grid { grid-template-columns: 1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_scored_data(model_version: int = 11, data_mtime: float = 0.0):
    cache_path = Path(f"data/processed/scored_financials_v{model_version}.csv")
    if cache_path.exists() and cache_path.stat().st_mtime >= data_mtime:
        return pd.read_csv(cache_path, dtype={"stock_code": str})

    financials = load_financials()
    features = add_beneish_style_features(financials)
    scored = score_financials(features.dropna(subset=["m_score"]))
    scored = add_explanations(scored)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(cache_path, index=False)
    return scored


@st.cache_data
def load_labels(label_mtime: float = 0.0):
    return load_event_labels()


def classify_risk_level(score: float) -> str:
    if score >= 70:
        return "High"
    if score >= 40:
        return "Watch"
    return "Normal"


def style_chart(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="#070907",
        plot_bgcolor="#070907",
        font=dict(color="#F2EFE4"),
        legend=dict(font=dict(color="#F2EFE4")),
        xaxis=dict(gridcolor="#20271E", zerolinecolor="#3A4536"),
        yaxis=dict(gridcolor="#20271E", zerolinecolor="#3A4536"),
    )
    return fig


def analysis_to_html(text: str) -> str:
    lines = []
    in_list = False
    for raw_line in text.splitlines():
        line = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", raw_line)
        if line.startswith("- "):
            if not in_list:
                lines.append("<ul>")
                in_list = True
            lines.append(f"<li>{line[2:]}</li>")
        else:
            if in_list:
                lines.append("</ul>")
                in_list = False
            lines.append(f"<p>{line}</p>")
    if in_list:
        lines.append("</ul>")
    return "".join(lines)


def top_indicator_summary(row: pd.Series, limit: int = 3) -> str:
    candidates = []
    for feature, label in FEATURE_LABELS.items():
        value = row.get(feature)
        if pd.isna(value):
            continue
        if feature == "tata":
            severity = abs(float(value)) / 0.08
        else:
            severity = abs(float(value) - 1.0)
        candidates.append((severity, label, float(value)))
    if not candidates:
        return "주요 지표 산출 불가"
    top_items = sorted(candidates, reverse=True)[:limit]
    return ", ".join(f"{label} {value:.2f}" for _, label, value in top_items)


def first_audit_question(row: pd.Series) -> str:
    steps = str(row.get("recommended_audit_steps", "")).splitlines()
    if not steps:
        return "재무비율 변동 원인을 전년 및 peer와 비교해 설명합니다."
    first = re.sub(r"^\d+\.\s*", "", steps[0]).strip()
    return first[:210] + ("..." if len(first) > 210 else "")


def build_audit_workplan(row: pd.Series) -> pd.DataFrame:
    triggered = get_triggered_features(row)
    if not triggered:
        triggered = ["dsri", "tata", "lvgi"]

    rows = []
    for idx, feature in enumerate(triggered[:5], start=1):
        focus = AUDIT_FOCUS.get(feature)
        if not focus:
            continue
        value = row.get(feature)
        peer_z = row.get(f"{feature}_peer_z")
        priority = "High" if idx <= 2 and row.get("final_risk_score", 0) >= 70 else "Watch"
        rows.append(
            {
                "Priority": priority,
                "Audit Area": focus["area"],
                "Risk Signal": f"{FEATURE_LABELS.get(feature, feature.upper())} {value:.2f}"
                if pd.notna(value)
                else FEATURE_LABELS.get(feature, feature.upper()),
                "Peer Context": f"Peer z {peer_z:.2f}" if pd.notna(peer_z) else "N/A",
                "Key Question": focus["question"],
                "Suggested Procedure": focus["procedure"],
                "Basis": focus["basis"],
                "Status": "Planning",
            }
        )
    return pd.DataFrame(rows)


def build_evidence_memo(row: pd.Series, workplan: pd.DataFrame) -> str:
    workplan_lines = []
    for idx, plan_row in workplan.iterrows():
        workplan_lines.append(
            f"{idx + 1}. [{plan_row['Priority']}] {plan_row['Audit Area']} - "
            f"{plan_row['Key Question']} ({plan_row['Basis']})"
        )

    return "\n".join(
        [
            "# Audit Risk Radar - Planning Memo",
            "",
            f"- Company: {row['company_name']}",
            f"- Year: {int(row['year'])}",
            f"- Industry: {row['industry']}",
            f"- Risk Level: {row['risk_level']}",
            f"- Final Risk: {row['final_risk_score']:.1f}",
            f"- Accounting Risk: {row['accounting_risk_score']:.1f}",
            f"- Peer Risk: {row['peer_risk_score']:.1f}",
            f"- ML Risk: {row['ml_risk_score']:.1f}",
            f"- M-Score: {row['m_score']:.2f}",
            "",
            "## Key Interpretation",
            str(row.get("risk_explanation", "")),
            "",
            "## Initial Workplan",
            "\n".join(workplan_lines) if workplan_lines else "No workplan rows generated.",
            "",
            "## Important Limitation",
            "This memo is based only on public DART financial statement data. It supports audit planning and risk prioritization, not an audit conclusion.",
        ]
    )


processed_data_path = Path("data/processed/financials_panel_2020_2024_full.csv")
if not processed_data_path.exists():
    processed_data_path = Path("data/processed/financials_panel.csv")
event_label_path = Path("data/labels/external_events_template.csv")
data_mtime = processed_data_path.stat().st_mtime if processed_data_path.exists() else 0.0
label_mtime = event_label_path.stat().st_mtime if event_label_path.exists() else 0.0
raw_financials = load_financials()
df = load_scored_data(model_version=11, data_mtime=data_mtime)
event_labels = load_labels(label_mtime=label_mtime)
df = attach_event_labels(df, event_labels)
df["risk_level"] = df["final_risk_score"].apply(classify_risk_level)
if "detailed_risk_analysis" not in df.columns:
    df["detailed_risk_analysis"] = df.apply(detailed_risk_analysis, axis=1)
if "accounting_risk_analysis" not in df.columns:
    df["accounting_risk_analysis"] = df.apply(explain_accounting_layer, axis=1)
if "peer_risk_analysis" not in df.columns:
    df["peer_risk_analysis"] = df.apply(explain_peer_layer, axis=1)
if "ml_risk_analysis" not in df.columns:
    df["ml_risk_analysis"] = df.apply(explain_ml_layer, axis=1)
if "feature_imputed_count" not in df.columns:
    df["feature_imputed_count"] = 0
if "feature_imputed_ratio" not in df.columns:
    df["feature_imputed_ratio"] = 0.0
if "imputed_features" not in df.columns:
    df["imputed_features"] = ""
data_source_label = "DART 실제 공시 데이터" if processed_data_path.exists() else "샘플 데이터"
data_source_detail = (
    f"{processed_data_path.name} | {df['company_name'].nunique():,}개 회사 | "
    f"{int(df['year'].min())}-{int(df['year'].max())}"
    if processed_data_path.exists() and not df.empty
    else "sample_financials.csv"
)

st.title("Audit Risk Radar")
st.caption("공시 재무제표 기반 감사 리스크 스크리닝 | Beneish-style indicators, Peer comparison, ML anomaly detection")
st.caption(f"Data Source: {data_source_label} · {data_source_detail}")
st.markdown(
    f"""
    <div class='intro-band'>
        <div class='hero-grid'>
            <div>
                <div class='system-kicker'>DART FINANCIAL RISK SYSTEM</div>
                <div class='hero-title'>공시 재무제표를 감사계획 신호로 변환합니다.</div>
                <div class='small-note'>
                Audit Risk Radar는 DART 공시 재무제표를 이용해 기업별 이상징후를 빠르게 선별하는 감사계획 보조 도구입니다.
                감사 결론을 내리는 시스템이 아니라, 감사인이 먼저 볼 회사와 계정 영역을 정하고 후속 질문을 설계하도록 돕는 risk prioritization dashboard입니다.
                </div>
                <div class='reference-chip-row'>
                    <span class='reference-chip'>Company Search</span>
                    <span class='reference-chip'>Beneish-style</span>
                    <span class='reference-chip'>Peer Benchmark</span>
                    <span class='reference-chip'>ML Anomaly</span>
                    <span class='reference-chip'>Audit Questions</span>
                </div>
            </div>
            <div class='preview-panel'>
                <div class='preview-topline'>
                    <span>Risk Signal Preview</span>
                    <span>2020-2024</span>
                </div>
                <div>
                    <div class='preview-number'>{df['company_name'].nunique():,}</div>
                    <div style='font-size:0.86rem; color:#4D5C45;'>scored companies in local panel</div>
                    <div class='preview-bars'>
                        <span style='height:32%;'></span>
                        <span style='height:58%;'></span>
                        <span style='height:42%;'></span>
                        <span style='height:76%;'></span>
                        <span style='height:64%;'></span>
                        <span style='height:88%;'></span>
                        <span style='height:48%;'></span>
                    </div>
                </div>
                <div class='preview-foot'>
                    <span>Accounting</span>
                    <span>Peer</span>
                    <span>ML</span>
                </div>
            </div>
        </div>
    </div>
    <div class='workflow-grid'>
        <div class='workflow-step'>
            <div class='step-label'>Step 1</div>
            <div class='step-title'>회사 검색</div>
            <div class='small-note'>감사인이 보고 싶은 회사와 분석 Year를 먼저 선택합니다.</div>
        </div>
        <div class='workflow-step'>
            <div class='step-label'>Step 2</div>
            <div class='step-title'>재무 리스크 해석</div>
            <div class='small-note'>Beneish-style, peer 비교, ML 이상탐지 신호를 함께 봅니다.</div>
        </div>
        <div class='workflow-step'>
            <div class='step-label'>Step 3</div>
            <div class='step-title'>감사 질문 설계</div>
            <div class='small-note'>재무비율과 peer 이례성을 근거로 후속 질문과 ISA/IFRS 관점을 연결합니다.</div>
        </div>
    </div>
    <div class='audit-callout'>
        <strong>사용 시 주의:</strong> 이 대시보드는 공시 재무제표만을 사용합니다. 내부 원장, 전표, 계약서, 수금내역을 직접 확인하지 않으므로
        결과는 부정 판단이 아니라 감사인이 추가 검토할 방향을 정하는 사전 신호입니다.
    </div>
    """,
    unsafe_allow_html=True,
)

years = sorted(df["year"].unique(), reverse=True)
industries = sorted(df["industry"].unique())

st.markdown("### 분석 범위 설정")
st.markdown(
    "<p class='section-note'>먼저 감사인이 검토하려는 보고연도와 Industry를 선택한 뒤, 회사명 또는 종목코드로 분석 대상 회사를 검색합니다.</p>",
    unsafe_allow_html=True,
)

selected_year = st.selectbox("Year", years)
selected_industries = st.multiselect("Industry", industries, default=industries)

filtered = df[(df["year"] == selected_year) & (df["industry"].isin(selected_industries))]
top_n = 10
top = filtered.head(top_n)

if filtered.empty:
    st.warning("선택한 조건에 해당하는 회사가 없습니다. Industry 필터를 하나 이상 선택해 주세요.")
    st.stop()

st.markdown("### 개별 회사 공시 Risk 분석")
st.markdown(
    "<p class='section-note'>회사명/종목코드로 원하는 기업을 검색하면 해당 회사의 공시 재무제표 기반 리스크, 전년 대비 지표 변화, 후속 감사 질문을 한 화면에서 확인합니다.</p>",
    unsafe_allow_html=True,
)
company_lookup = (
    df[["stock_code", "company_name", "industry"]]
    .drop_duplicates()
    .sort_values(["company_name", "stock_code"])
    .copy()
)
company_lookup["search_text"] = (
    company_lookup["company_name"].astype(str)
    + " "
    + company_lookup["stock_code"].astype(str)
    + " "
    + company_lookup["industry"].astype(str)
).str.lower()
company_lookup["label"] = (
    company_lookup["company_name"].astype(str)
    + " ("
    + company_lookup["stock_code"].astype(str)
    + ") · "
    + company_lookup["industry"].astype(str)
)

st.markdown("#### 회사 검색")
st.markdown(
    "<p class='small-note'>현재 확장 패널에 적재된 회사 중 분석 대상을 선택합니다. 전체 패널은 DART 공시 재무제표를 사전에 수집한 데이터베이스이므로, 화면에서 별도 API 호출 없이 즉시 분석합니다.</p>",
    unsafe_allow_html=True,
)
company_options = company_lookup["label"].tolist()
selected_label = st.selectbox(
    "Company 검색/선택",
    company_options,
    help="회사명 또는 종목코드를 입력하면 현재 수집된 전체 패널 안에서 자동완성 검색이 가능합니다.",
)
selected_stock_code = company_lookup.loc[
    company_lookup["label"] == selected_label, "stock_code"
].iloc[0]

company_df = df[df["stock_code"] == selected_stock_code].sort_values("year")
analysis_df = company_df[company_df["year"] == selected_year]
analysis_row = analysis_df.iloc[-1] if not analysis_df.empty else company_df.iloc[-1]
if analysis_df.empty:
    st.info(
        f"선택한 Year({selected_year})에는 해당 회사 데이터가 없어, "
        f"가장 최근 Year({int(analysis_row['year'])}) 기준으로 상세 분석을 표시합니다."
    )
trend_metrics = ["Final Risk", "Accounting Risk", "Peer Risk", "ML Risk"]

trend_df = company_df.rename(
    columns={
        "final_risk_score": "Final Risk",
        "accounting_risk_score": "Accounting Risk",
        "peer_risk_score": "Peer Risk",
        "ml_risk_score": "ML Risk",
    }
)
trend = px.line(
    trend_df,
    x="year",
    y=trend_metrics,
    markers=True,
    labels={"value": "Score", "year": "Year", "variable": "Metric"},
)
trend_min = float(trend_df[trend_metrics].min().min())
trend_max = float(trend_df[trend_metrics].max().max())
trend_padding = max((trend_max - trend_min) * 0.18, 5)
trend_y_min = max(0, trend_min - trend_padding)
trend_y_max = min(100, trend_max + trend_padding)
if trend_y_max - trend_y_min < 12:
    midpoint = (trend_y_max + trend_y_min) / 2
    trend_y_min = max(0, midpoint - 6)
    trend_y_max = min(100, midpoint + 6)
trend.update_traces(line=dict(width=3), marker=dict(size=8))
trend.update_layout(
    legend_title_text="",
    margin=dict(l=10, r=10, t=20, b=10),
    yaxis=dict(range=[trend_y_min, trend_y_max]),
)
st.plotly_chart(style_chart(trend), width="stretch")
st.markdown(
    "<p class='small-note'>가독성을 위해 이 그래프의 y축은 선택 회사의 점수 범위에 맞춰 확대됩니다. 각 점수의 절대 기준은 여전히 0~100 스케일입니다.</p>",
    unsafe_allow_html=True,
)

st.markdown("#### 선택 회사 요약")
company_metric_cols = st.columns(4)
company_metric_cols[0].metric("검토 등급", analysis_row["risk_level"])
company_metric_cols[1].metric("Final Risk", f"{analysis_row['final_risk_score']:.1f}")
company_metric_cols[2].metric("M-Score", f"{analysis_row['m_score']:.2f}")
company_metric_cols[3].metric("분석 Year", int(analysis_row["year"]))
st.markdown(
    f"<p class='small-note'><strong>{analysis_row['company_name']} · {analysis_row['industry']}</strong><br>{RISK_LEVEL_HELP.get(analysis_row['risk_level'], '')}</p>",
    unsafe_allow_html=True,
)

st.markdown("#### 감사 브리핑")
briefing_html = f"""
<div class='briefing-grid'>
    <div class='briefing-card'>
        <div class='briefing-kicker'>Priority</div>
        <div class='briefing-value'>{analysis_row['risk_level']} · Final Risk {analysis_row['final_risk_score']:.1f}</div>
        <div class='small-note'>이 점수는 감사 결론이 아니라, 선택 Year/Industry 표본 안에서 우선 검토 순서를 정하기 위한 신호입니다.</div>
    </div>
    <div class='briefing-card'>
        <div class='briefing-kicker'>Main Drivers</div>
        <div class='briefing-value'>{top_indicator_summary(analysis_row)}</div>
        <div class='small-note'>전년 대비 변화율과 발생액 성격 지표 중 눈에 띄는 항목입니다. 아래 점수 해부에서 원인을 더 확인합니다.</div>
    </div>
    <div class='briefing-card'>
        <div class='briefing-kicker'>First Audit Question</div>
        <div class='briefing-value'>후속 질문 후보</div>
        <div class='small-note'>{first_audit_question(analysis_row)}</div>
    </div>
</div>
"""
st.markdown(briefing_html, unsafe_allow_html=True)

st.markdown("#### 위험 신호 해석")
st.markdown(
    f"<div class='risk-analysis'>{analysis_to_html(analysis_row['detailed_risk_analysis'])}</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='small-note'>위 해석은 공시 재무제표 기반의 우선 검토 논리입니다. 실제 감사 단계에서는 중요성, 내부통제, 내부자료 접근 가능성에 따라 절차가 달라집니다.</p>",
    unsafe_allow_html=True,
)

st.markdown("#### Risk 점수 해부")
st.markdown(
    "<p class='small-note'>Final Risk를 구성하는 세 점수는 서로 다른 질문에 답합니다. Accounting Risk는 회계비율 자체의 red flag, Peer Risk는 유사 회사 대비 이례성, ML Risk는 여러 지표가 동시에 만드는 복합 이상 패턴을 봅니다.</p>",
    unsafe_allow_html=True,
)
layer_tabs = st.tabs(["Accounting Risk", "Peer Risk", "ML Risk"])
with layer_tabs[0]:
    st.markdown(
        f"<div class='risk-analysis'>{analysis_to_html(analysis_row['accounting_risk_analysis'])}</div>",
        unsafe_allow_html=True,
    )
with layer_tabs[1]:
    st.markdown(
        f"<div class='risk-analysis'>{analysis_to_html(analysis_row['peer_risk_analysis'])}</div>",
        unsafe_allow_html=True,
    )
with layer_tabs[2]:
    st.markdown(
        f"<div class='risk-analysis'>{analysis_to_html(analysis_row['ml_risk_analysis'])}</div>",
        unsafe_allow_html=True,
    )

st.markdown("#### 대표 Peer 비교군")
representative_peers = select_representative_peers(df, analysis_row, max_peers=8)
st.markdown(
    f"<p class='section-note'>{peer_methodology_note(analysis_row, representative_peers)}</p>",
    unsafe_allow_html=True,
)
if representative_peers.empty:
    st.info("현재 패널에서 표시할 peer 후보가 충분하지 않습니다.")
else:
    display_peers = representative_peers.copy()
    for amount_column in ["revenue", "total_assets"]:
        display_peers[amount_column] = display_peers[amount_column].map(
            lambda value: f"{value:,.0f}" if pd.notna(value) else ""
        )
    for ratio_column in ["operating_margin", "gross_margin", "sgi", "final_risk_score"]:
        display_peers[ratio_column] = display_peers[ratio_column].map(
            lambda value: f"{value:.3f}" if pd.notna(value) else ""
        )
    display_peers = display_peers.rename(
        columns={
            "company_name": "Peer Company",
            "stock_code": "종목코드",
            "industry": "Industry",
            "peer_similarity": "Peer 적합도",
            "revenue": "매출",
            "total_assets": "총자산",
            "operating_margin": "영업이익률",
            "gross_margin": "매출총이익률",
            "sgi": "SGI",
            "final_risk_score": "Final Risk",
            "peer_reason": "선정 근거",
        }
    )
    st.dataframe(display_peers, width="stretch", hide_index=True)
    st.markdown(
        f"<p class='small-note'>현재 Final Risk의 Peer Risk 점수는 Year/Industry 기준 robust z-score와 matched peer 기준 robust z-score를 50:50으로 반영합니다. 선택 회사의 matched peer group size는 {int(analysis_row.get('matched_peer_group_size', 0))}개입니다.</p>",
        unsafe_allow_html=True,
    )
    with st.expander("Peer 선정 기준 근거"):
        st.markdown(
            """
            - **Industry / Business model**: valuation과 deal comparable analysis에서 출발점이 되는 기준입니다. 다만 같은 Industry만으로는 충분하지 않으므로 보조 변수가 필요합니다.
            - **Size**: 매출과 총자산 규모가 크게 다르면 사업 안정성, 자금조달, 공시 품질, 성장 단계가 달라질 수 있어 비교 가능성이 약해집니다.
            - **Growth / Profitability**: 성장률과 margin은 valuation multiple과 위험 해석에 직접 영향을 주는 value driver입니다.
            - **Market / Liquidity**: 상장시장, 거래 유동성, 시가총액은 실무 valuation에서 중요한 변수입니다. 현재 DART 재무제표 패널에는 없으므로 향후 KRX/시장데이터 연동 시 반영합니다.
            - **Audit 적용**: valuation용 peer를 그대로 쓰는 것이 아니라, 재무제표 이상징후를 비교하기 위한 peer이므로 회계정책, 수익인식 구조, 운전자본 구조가 비슷한지도 함께 고려해야 합니다.
            """
        )

st.markdown("#### 주요 회계 지표")
latest = analysis_row
indicator_fig = go.Figure(
    data=[
        go.Bar(
            x=[
                latest["dsri"],
                latest["gmi"],
                latest["aqi"],
                latest["sgi"],
                latest["sgai"],
                latest["lvgi"],
                latest["tata"],
            ],
            y=["DSRI", "GMI", "AQI", "SGI", "SGAI", "LVGI", "TATA"],
            orientation="h",
            marker_color=COLORWAY,
        )
    ]
)
indicator_fig.update_layout(
    title="최근 Year 주요 회계 지표",
    xaxis_title="Index / Ratio",
    yaxis_title="Indicator",
    margin=dict(l=10, r=10, t=50, b=10),
)
st.plotly_chart(style_chart(indicator_fig), width="stretch")

st.markdown("##### 연도별 산출 내역")
st.markdown(
    "<p class='small-note'>Beneish-style 지표는 대부분 전년 대비 변화율입니다. 아래 표에서 기초 비율이 어떻게 움직였는지 보면 특정 연도 지표가 튄 이유를 추적할 수 있습니다.</p>",
    unsafe_allow_html=True,
)

calculation_columns = [
    "year",
    "revenue",
    "receivables",
    "receivables_to_sales",
    "gross_margin",
    "asset_quality",
    "sga_proxy",
    "leverage",
    "tata",
    "dsri",
    "gmi",
    "aqi",
    "sgi",
    "sgai",
    "lvgi",
    "m_score",
]
available_calculation_columns = [
    column for column in calculation_columns if column in company_df.columns
]
calculation_df = company_df[available_calculation_columns].copy()
ratio_columns = [
    "receivables_to_sales",
    "gross_margin",
    "asset_quality",
    "sga_proxy",
    "leverage",
    "tata",
    "dsri",
    "gmi",
    "aqi",
    "sgi",
    "sgai",
    "lvgi",
    "m_score",
]
amount_columns = ["revenue", "receivables"]
for column in ratio_columns:
    if column in calculation_df.columns:
        calculation_df[column] = calculation_df[column].round(3)
for column in amount_columns:
    if column in calculation_df.columns:
        calculation_df[column] = calculation_df[column].map(lambda value: f"{value:,.0f}" if pd.notna(value) else "")

calculation_df = calculation_df.rename(
    columns={
        "year": "Year",
        "revenue": "매출",
        "receivables": "매출채권",
        "receivables_to_sales": "매출채권/매출",
        "gross_margin": "매출총이익률",
        "asset_quality": "자산품질",
        "sga_proxy": "판관비 Proxy",
        "leverage": "레버리지",
        "tata": "TATA",
        "dsri": "DSRI",
        "gmi": "GMI",
        "aqi": "AQI",
        "sgi": "SGI",
        "sgai": "SGAI",
        "lvgi": "LVGI",
        "m_score": "M-Score",
    }
)
st.dataframe(calculation_df, width="stretch", hide_index=True)

with st.expander("회계 지표 설명"):
    st.markdown(
        """
        | 지표 | 산식 | 참고 기준과 해석 |
        | --- | --- | --- |
        | M-Score | Beneish-style 지표 종합 | `-2.22`보다 높으면 전통적으로 주의 신호로 봅니다. 이 앱에서는 단독 결론이 아니라 우선 검토 기준입니다. |
        | DSRI | 당기 `(매출채권 / 매출)` ÷ 전기 `(매출채권 / 매출)` | `1.0` 초과면 매출채권이 매출보다 빠르게 증가, `1.2` 이상이면 수익 인식과 회수가능성을 주의합니다. |
        | GMI | 전기 `매출총이익률` ÷ 당기 `매출총이익률` | `1.0` 초과면 수익성 악화로, 이익 조정 압력이 커질 수 있습니다. |
        | AQI | 당기 `자산품질` ÷ 전기 `자산품질` | `1.0` 초과면 비유동/기타 자산성 항목 비중 증가를 의미합니다. |
        | SGI | 당기 `매출` ÷ 전기 `매출` | `1.2` 이상이면 고성장 구간으로 보고 매출 인식 압력과 함께 해석합니다. |
        | SGAI | 당기 `판관비 Proxy` ÷ 전기 `판관비 Proxy` | `1.0` 초과면 매출 대비 비용 부담 증가를 의미합니다. |
        | LVGI | 당기 `레버리지` ÷ 전기 `레버리지` | `1.0` 초과면 부채 부담과 유동성 압력이 커진 것으로 봅니다. |
        | TATA | `(순이익 - 영업현금흐름)` ÷ `총자산` | `0.05` 이상이면 주의, `0.08` 이상이면 강한 발생액 신호로 봅니다. |

        위 기준은 감사 결론을 내리는 절대 임계값이 아니라 planning 단계의 참고 기준입니다.
        """
    )

st.markdown("#### 추천 감사 질문/후속 절차")
latest_steps = analysis_row["recommended_audit_steps"].splitlines()
for step in latest_steps:
    st.markdown(f"- {step}")
st.markdown(
    "<p class='small-note'>위 절차는 ISA 감사기준과 IFRS 회계기준 관점을 연결한 planning checklist입니다. 공시자료 단계에서는 검토 영역과 질문 후보를 제시하는 수준이며, 실제 감사에서는 중요성, 내부통제, 산업 특성, 내부자료 접근 가능성을 함께 고려해야 합니다.</p>",
    unsafe_allow_html=True,
)

with st.expander("Audit Tech 벤치마크 관점"):
    st.markdown(
        """
        | Big4 audit tech에서 관찰되는 방향 | 이 앱에서 구현한 방식 |
        | --- | --- |
        | 대량 데이터 기반 risk screening | DART 5개년 패널에서 회사별 Final Risk를 산출합니다. |
        | 회계 지표와 anomaly analytics 결합 | Beneish-style, peer risk, ML anomaly score를 분리해 보여줍니다. |
        | 결과 설명 가능성 | 각 점수별 원인, 주요 지표, peer z-score를 해석합니다. |
        | 감사 절차로 연결 | Risk signal을 Audit Area, Key Question, Suggested Procedure, ISA/IFRS 근거로 변환합니다. |
        | workpaper 재사용성 | Planning Memo를 다운로드해 면접/보고용 산출물로 사용할 수 있습니다. |

        현재 앱은 내부 원장, 전표, 계약 단위 데이터가 없기 때문에 journal testing이나 전수 거래 분석까지 수행하지 않습니다.
        대신 공시 재무제표만으로 가능한 planning analytics 범위에 집중합니다.
        """
    )

st.markdown("#### Audit Workplan")
st.markdown(
    "<p class='small-note'>Big4 감사 플랫폼의 공통 방향처럼, 분석 결과를 감사인이 실행할 수 있는 업무 단위로 변환합니다. 아래 표는 공시 데이터에서 포착된 신호를 계정 영역, 핵심 질문, 후속 절차, 근거 기준서로 연결한 planning workpaper 초안입니다.</p>",
    unsafe_allow_html=True,
)
workplan_df = build_audit_workplan(analysis_row)
if workplan_df.empty:
    st.info("현재 선택 회사에 대해 자동 생성된 workplan 항목이 없습니다.")
else:
    st.dataframe(
        workplan_df.rename(
            columns={
                "Priority": "우선순위",
                "Audit Area": "감사 영역",
                "Risk Signal": "Risk Signal",
                "Peer Context": "Peer Context",
                "Key Question": "핵심 질문",
                "Suggested Procedure": "추천 절차",
                "Basis": "근거",
                "Status": "상태",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    memo_text = build_evidence_memo(analysis_row, workplan_df)
    st.download_button(
        "Planning Memo 다운로드",
        data=memo_text.encode("utf-8"),
        file_name=f"audit_risk_memo_{analysis_row['stock_code']}_{int(analysis_row['year'])}.md",
        mime="text/markdown",
        help="선택 회사의 주요 점수, 해석, 추천 감사 질문을 Markdown 메모로 저장합니다.",
    )

with st.expander("시장/Industry 스크리닝 보조 보기"):
    st.markdown("#### 선택 범위 요약")
    metric_cols = st.columns(4)
    metric_cols[0].metric("검토 대상 회사", f"{len(filtered):,}")
    metric_cols[1].metric("최고 Final Risk", f"{filtered['final_risk_score'].max():.1f}")
    metric_cols[2].metric("평균 Final Risk", f"{filtered['final_risk_score'].mean():.1f}")
    metric_cols[3].metric("High 등급", f"{int((filtered['risk_level'] == 'High').sum()):,}")
    st.markdown(
        "<p class='small-note'>이 영역은 개별 회사 분석이 아니라, 선택 Year/Industry 안에서 어느 회사가 상대적으로 눈에 띄는지 보는 보조 스크리닝입니다.</p>",
        unsafe_allow_html=True,
    )

    st.markdown("#### 점수 해석")
    guide_cols = st.columns(4)
    for col, title in zip(guide_cols, ["Final Risk", "Accounting Risk", "Peer Risk", "ML Risk"]):
        col.markdown(
            f"<div class='score-guide'><strong>{title}</strong><br><span class='small-note'>{LAYER_HELP[title]}</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("#### 위험 순위")
    st.dataframe(
        top.sort_values("final_risk_score", ascending=False)[
            [
                "stock_code",
                "company_name",
                "industry",
                "risk_level",
                "final_risk_score",
                "accounting_risk_score",
                "peer_risk_score",
                "ml_risk_score",
                "m_score",
                "risk_explanation",
            ]
        ].rename(columns=DISPLAY_COLUMNS),
        width="stretch",
        hide_index=True,
    )
    st.markdown(
        "<p class='small-note'><strong>등급 기준:</strong> High 70점 이상, Watch 40점 이상, Normal 40점 미만. 등급은 절대적 판단이 아니라 감사계획상 우선순위 표시입니다.</p>",
        unsafe_allow_html=True,
    )

    breakdown = top.melt(
        id_vars=["company_name"],
        value_vars=["accounting_risk_score", "peer_risk_score", "ml_risk_score"],
        var_name="risk_layer",
        value_name="score",
    )
    breakdown["risk_layer"] = breakdown["risk_layer"].map(LAYER_LABELS)
    fig = px.bar(
        breakdown,
        x="company_name",
        y="score",
        color="risk_layer",
        barmode="group",
        labels={"score": "Score", "company_name": "Company", "risk_layer": "Risk Layer"},
        title="Top 그룹 리스크 구성",
    )
    fig.update_layout(legend_title_text="", margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(style_chart(fig), width="stretch")

    layer_means = top[["accounting_risk_score", "peer_risk_score", "ml_risk_score"]].mean()
    pie = go.Figure(
        data=[
            go.Pie(
                labels=[LAYER_LABELS[col] for col in layer_means.index],
                values=layer_means.values,
                hole=0.58,
                marker=dict(colors=COLORWAY[:3]),
                textinfo="label+percent",
            )
        ]
    )
    pie.update_layout(
        title="Top 그룹 평균 리스크 비중",
        showlegend=False,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(style_chart(pie), width="stretch")

with st.expander("데이터/모델 품질 및 검증 보기", expanded=False):
    st.markdown("### 데이터/모델 진단")
    st.markdown(
        "<p class='section-note'>이 영역은 사용자에게 “점수를 얼마나 믿고 해석할 수 있는지”를 보여줍니다. 표본 규모, 결측 대체, 점수 분포, 시간 기준 검증을 확인합니다.</p>",
        unsafe_allow_html=True,
    )

    diagnostic_cols = st.columns(4)
    diagnostic_cols[0].metric("Company 수", f"{df['company_name'].nunique():,}")
    diagnostic_cols[1].metric("Company-Year 수", f"{len(df):,}")
    diagnostic_cols[2].metric(
        "결측 대체 행",
        f"{int((df['feature_imputed_count'] > 0).sum()):,}",
        help="Beneish-style 지표 중 결측 또는 무한값이 있어 industry-year/year/global median으로 대체된 company-year 수입니다.",
    )
    diagnostic_cols[3].metric(
        "평균 대체 비율",
        f"{df['feature_imputed_ratio'].mean() * 100:.1f}%",
        help="전체 지표 중 대체된 지표의 평균 비율입니다. 낮을수록 원천 데이터 완결성이 높습니다.",
    )

    diag_tabs = st.tabs(["Data Quality", "Model Diagnostics", "Validation", "해석 기준"])

    with diag_tabs[0]:
        st.markdown(
            "<p class='small-note'>Data Quality는 원천 DART 패널이 얼마나 완성되어 있고, 그중 어느 범위가 리스크 scoring에 사용되었는지 보여줍니다. 특정 업종 표본이 너무 적으면 peer 비교 해석에 주의해야 합니다.</p>",
            unsafe_allow_html=True,
        )
        raw_company_years = len(raw_financials)
        raw_companies = raw_financials["company_name"].nunique()
        expected_years = raw_financials["year"].nunique()
        completed_company_counts = raw_financials.groupby("stock_code")["year"].nunique()
        completed_5yr_companies = int((completed_company_counts >= expected_years).sum())
        scored_company_codes = set(df["stock_code"].astype(str))
        raw_company_codes = set(raw_financials["stock_code"].astype(str))
        scoring_coverage = len(scored_company_codes) / len(raw_company_codes) if raw_company_codes else 0

        coverage_cols = st.columns(4)
        coverage_cols[0].metric("원천 패널 회사", f"{raw_companies:,}")
        coverage_cols[1].metric("5개년 완성 회사", f"{completed_5yr_companies:,}")
        coverage_cols[2].metric("Scoring 가능 회사", f"{df['company_name'].nunique():,}")
        coverage_cols[3].metric("Scoring 커버리지", f"{scoring_coverage * 100:.1f}%")
        st.markdown(
            "<p class='small-note'>원천 패널은 DART에서 수집한 회사-연도 데이터입니다. Scoring 패널은 전년 대비 지표가 필요한 Beneish-style 계산을 통과한 표본이며, 첫 연도 또는 비교연도 부족 행은 일부 제외됩니다.</p>",
            unsafe_allow_html=True,
        )

        year_counts = (
            df.groupby("year")
            .agg(company_years=("company_name", "count"), companies=("company_name", "nunique"))
            .reset_index()
            .sort_values("year")
        )
        year_fig = px.bar(
            year_counts,
            x="year",
            y="company_years",
            text="company_years",
            labels={"year": "Year", "company_years": "Company-Year"},
            title="Year별 표본 수",
        )
        year_fig.update_traces(textposition="outside", marker_color=COLORWAY[0])
        year_fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), yaxis_title="")
        st.plotly_chart(style_chart(year_fig), width="stretch")

        raw_year_counts = (
            raw_financials.groupby("year")
            .agg(raw_company_years=("company_name", "count"), raw_companies=("company_name", "nunique"))
            .reset_index()
            .sort_values("year")
        )
        coverage_by_year = raw_year_counts.merge(year_counts, on="year", how="left").fillna(0)
        coverage_by_year["scoring_rate"] = (
            coverage_by_year["companies"] / coverage_by_year["raw_companies"].replace(0, pd.NA)
        ).fillna(0)
        coverage_by_year["scoring_rate"] = (coverage_by_year["scoring_rate"] * 100).round(1)
        st.dataframe(
            coverage_by_year.rename(
                columns={
                    "year": "Year",
                    "raw_company_years": "원천 Company-Year",
                    "raw_companies": "원천 회사 수",
                    "company_years": "Scoring Company-Year",
                    "companies": "Scoring 회사 수",
                    "scoring_rate": "Scoring 커버리지(%)",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        industry_counts = (
            df.groupby("industry")["company_name"]
            .nunique()
            .sort_values(ascending=True)
            .reset_index(name="companies")
        )
        industry_fig = px.bar(
            industry_counts,
            x="companies",
            y="industry",
            orientation="h",
            text="companies",
            labels={"companies": "Companies", "industry": "Industry"},
            title="Industry별 회사 수",
        )
        industry_fig.update_traces(textposition="outside", marker_color=COLORWAY[2])
        industry_fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), xaxis_title="", yaxis_title="")
        st.plotly_chart(style_chart(industry_fig), width="stretch")

        available_quality_columns = [
            column for column in RAW_QUALITY_COLUMNS if column in raw_financials.columns
        ]
        missing_summary = (
            raw_financials[available_quality_columns]
            .isna()
            .mean()
            .mul(100)
            .round(2)
            .rename_axis("account")
            .reset_index(name="missing_rate")
        )
        missing_summary["account"] = missing_summary["account"].map(RAW_QUALITY_LABELS).fillna(
            missing_summary["account"]
        )
        missing_summary["available_rate"] = 100 - missing_summary["missing_rate"]
        missing_fig = px.bar(
            missing_summary.sort_values("available_rate"),
            x="available_rate",
            y="account",
            orientation="h",
            text="available_rate",
            labels={"available_rate": "수집 완성도(%)", "account": "Account"},
            title="핵심 재무제표 항목 수집 완성도",
        )
        missing_fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside",
            marker_color=COLORWAY[2],
        )
        missing_fig.update_layout(
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis=dict(range=[0, 105]),
            yaxis_title="",
        )
        st.plotly_chart(style_chart(missing_fig), width="stretch")

        st.dataframe(
            missing_summary[["account", "missing_rate", "available_rate"]]
            .sort_values("missing_rate", ascending=False)
            .rename(
                columns={
                    "account": "Account",
                    "missing_rate": "결측률(%)",
                    "available_rate": "수집 완성도(%)",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        imputed_values = []
        for value in df["imputed_features"].dropna():
            imputed_values.extend([feature.strip() for feature in value.split(",") if feature.strip()])

        if imputed_values:
            imputed_counts = (
                pd.Series(imputed_values)
                .value_counts()
                .rename_axis("feature")
                .reset_index(name="count")
            )
            imputed_counts["feature"] = imputed_counts["feature"].map(FEATURE_LABELS).fillna(
                imputed_counts["feature"]
            )
            imputed_fig = px.bar(
                imputed_counts,
                x="feature",
                y="count",
                labels={"feature": "Indicator", "count": "대체 건수"},
                title="지표별 결측 대체 건수",
            )
            imputed_fig.update_traces(marker_color=COLORWAY[1])
            imputed_fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(style_chart(imputed_fig), width="stretch")
        else:
            st.info("현재 선택된 DART 패널에서는 ML 입력 지표의 결측 대체가 발생하지 않았습니다.")

    with diag_tabs[1]:
        st.markdown(
            "<p class='small-note'>Model Diagnostics는 Final Risk와 세부 리스크 계층이 한쪽 모델에 과도하게 쏠리지 않는지 확인하기 위한 영역입니다.</p>",
            unsafe_allow_html=True,
        )
        score_hist = px.histogram(
            df,
            x="final_risk_score",
            nbins=25,
            labels={"final_risk_score": "Final Risk"},
            title="Final Risk 분포",
        )
        score_hist.update_traces(marker_color=COLORWAY[0])
        score_hist.update_layout(margin=dict(l=10, r=10, t=50, b=10), yaxis_title="Company-Year 수")
        st.plotly_chart(style_chart(score_hist), width="stretch")

        score_corr = df[
            ["final_risk_score", "accounting_risk_score", "peer_risk_score", "ml_risk_score"]
        ].corr()
        score_corr = score_corr.rename(
            index={
                "final_risk_score": "Final",
                "accounting_risk_score": "Accounting",
                "peer_risk_score": "Peer",
                "ml_risk_score": "ML",
            },
            columns={
                "final_risk_score": "Final",
                "accounting_risk_score": "Accounting",
                "peer_risk_score": "Peer",
                "ml_risk_score": "ML",
            },
        )
        corr_fig = px.imshow(
            score_corr,
            text_auto=".2f",
            zmin=-1,
            zmax=1,
            color_continuous_scale=["#C44536", "#F8FAFC", "#235789"],
            title="Risk Layer 상관관계",
        )
        corr_fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), coloraxis_showscale=False)
        st.plotly_chart(style_chart(corr_fig), width="stretch")

        ml_raw = df[["isolation_risk_raw", "pca_reconstruction_error"]].rename(
            columns={
                "isolation_risk_raw": "Isolation Forest",
                "pca_reconstruction_error": "PCA Error",
            }
        )
        ml_long = ml_raw.melt(var_name="Model Signal", value_name="Raw Score")
        ml_box = px.box(
            ml_long,
            x="Model Signal",
            y="Raw Score",
            color="Model Signal",
            title="ML 원천 신호 분포",
        )
        ml_box.update_layout(showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(style_chart(ml_box), width="stretch")

        industry_risk = (
            df.groupby("industry")
            .agg(avg_final_risk=("final_risk_score", "mean"), companies=("company_name", "nunique"))
            .reset_index()
            .sort_values("avg_final_risk", ascending=True)
        )
        industry_risk_fig = px.bar(
            industry_risk,
            x="avg_final_risk",
            y="industry",
            orientation="h",
            color="companies",
            color_continuous_scale=["#DDEBF4", "#235789"],
            labels={"avg_final_risk": "평균 Final Risk", "industry": "Industry", "companies": "Companies"},
            title="Industry별 평균 리스크",
        )
        industry_risk_fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), yaxis_title="")
        st.plotly_chart(style_chart(industry_risk_fig), width="stretch")

    with diag_tabs[2]:
        validation_year = int(df["year"].max())
        train_df = df[df["year"] < validation_year].copy()
        validation_df = df[df["year"] == validation_year].copy()
        validation_threshold = (
            train_df["final_risk_score"].quantile(0.90) if not train_df.empty else df["final_risk_score"].quantile(0.90)
        )
        validation_flagged = validation_df[validation_df["final_risk_score"] >= validation_threshold]

        st.markdown(
            f"<p class='small-note'>현재 패널에서는 {validation_year}년을 hold-out 검증 연도로 보고, 그 이전 연도를 기준 분포로 사용합니다. 이는 정답 라벨 검증이 아니라 시간 기준 sanity check입니다.</p>",
            unsafe_allow_html=True,
        )

        validation_metrics = st.columns(4)
        validation_metrics[0].metric(
            "Train 기간",
            f"{int(train_df['year'].min())}-{validation_year - 1}" if not train_df.empty else "N/A",
        )
        validation_metrics[1].metric("Validation Year", f"{validation_year}")
        validation_metrics[2].metric("검증 표본", f"{len(validation_df):,}")
        validation_metrics[3].metric(
            "상위 10% 기준 초과",
            f"{len(validation_flagged):,}",
            help="Train 기간의 Final Risk 90 percentile을 기준으로 Validation Year에서 초과한 company-year 수입니다.",
        )

        split_df = pd.concat(
            [
                train_df.assign(split="Train"),
                validation_df.assign(split="Validation"),
            ],
            ignore_index=True,
        )
        split_hist = px.histogram(
            split_df,
            x="final_risk_score",
            color="split",
            nbins=25,
            barmode="overlay",
            opacity=0.72,
            labels={"final_risk_score": "Final Risk", "split": "Split"},
            title="Train vs Validation 점수 분포",
        )
        split_hist.add_vline(
            x=validation_threshold,
            line_width=2,
            line_dash="dash",
            line_color=COLORWAY[3],
            annotation_text="Train 90%",
        )
        split_hist.update_layout(margin=dict(l=10, r=10, t=50, b=10), yaxis_title="Company-Year 수")
        st.plotly_chart(style_chart(split_hist), width="stretch")

        split_summary = (
            split_df.groupby("split")
            .agg(
                rows=("company_name", "count"),
                companies=("company_name", "nunique"),
                avg_final_risk=("final_risk_score", "mean"),
                p90_final_risk=("final_risk_score", lambda series: series.quantile(0.90)),
            )
            .reset_index()
        )
        split_summary["avg_final_risk"] = split_summary["avg_final_risk"].round(2)
        split_summary["p90_final_risk"] = split_summary["p90_final_risk"].round(2)
        st.dataframe(
            split_summary.rename(
                columns={
                    "split": "Split",
                    "rows": "Company-Year",
                    "companies": "Companies",
                    "avg_final_risk": "평균 Final Risk",
                    "p90_final_risk": "상위 10% 기준",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        prior_year = validation_year - 1
        prior_scores = df[df["year"] == prior_year][["stock_code", "company_name", "final_risk_score"]]
        current_scores = validation_df[["stock_code", "company_name", "industry", "final_risk_score"]]
        yoy = current_scores.merge(
            prior_scores,
            on=["stock_code", "company_name"],
            how="inner",
            suffixes=("_current", "_prior"),
        )
        yoy["risk_delta"] = yoy["final_risk_score_current"] - yoy["final_risk_score_prior"]
        yoy = yoy.sort_values("risk_delta", ascending=False)

        st.markdown("#### Validation Year 주요 관찰")
        st.markdown("##### 상위 10% 임계값 초과 회사")
        st.dataframe(
            validation_flagged.sort_values("final_risk_score", ascending=False)[
                [
                    "stock_code",
                    "company_name",
                    "industry",
                    "final_risk_score",
                    "accounting_risk_score",
                    "peer_risk_score",
                    "ml_risk_score",
                ]
            ]
            .head(10)
            .rename(columns=DISPLAY_COLUMNS),
            width="stretch",
            hide_index=True,
        )

        st.markdown("##### 전년 대비 Risk 상승폭 상위 회사")
        st.dataframe(
            yoy[
                [
                    "stock_code",
                    "company_name",
                    "industry",
                    "final_risk_score_prior",
                    "final_risk_score_current",
                    "risk_delta",
                ]
            ]
            .head(10)
            .rename(
                columns={
                    "stock_code": "종목코드",
                    "company_name": "회사명",
                    "industry": "Industry",
                    "final_risk_score_prior": f"{prior_year} Risk",
                    "final_risk_score_current": f"{validation_year} Risk",
                    "risk_delta": "Risk 상승폭",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        st.markdown(
            "<p class='small-note'>왼쪽 표는 과거 기준 상위 10% 임계값을 Validation Year에 적용했을 때 우선 검토 대상이 되는 회사입니다. 오른쪽 표는 전년 대비 Final Risk가 가장 크게 상승한 회사로, 당기 감사계획에서 변화 원인을 먼저 설명해야 할 후보입니다.</p>",
            unsafe_allow_html=True,
        )

        st.markdown("#### 외부 이벤트 라벨 검증")
        st.markdown(
            "<p class='small-note'>재무제표 정정, 감사의견 변형, 계속기업 불확실성, 거래소 제재 등 외부 이벤트 라벨을 붙이면 위험 점수가 실제 사후 이벤트를 얼마나 포착했는지 약한 검증을 수행할 수 있습니다.</p>",
            unsafe_allow_html=True,
        )

        if event_labels.empty:
            st.info(
                "아직 입력된 외부 이벤트 라벨이 없습니다. "
                "`data/labels/external_events_template.csv`에 확인된 이벤트를 추가하면 이 영역에서 이벤트 포착률이 자동 계산됩니다."
            )
            st.dataframe(
                pd.DataFrame(columns=EVENT_LABEL_COLUMNS),
                width="stretch",
                hide_index=True,
            )
        else:
            validation_events = validation_df[validation_df["event_flag"]].copy()
            validation_event_count = validation_events[["stock_code", "year"]].drop_duplicates().shape[0]
            captured_events = validation_flagged[validation_flagged["event_flag"]]
            captured_event_count = captured_events[["stock_code", "year"]].drop_duplicates().shape[0]
            capture_rate = (
                captured_event_count / validation_event_count if validation_event_count else 0.0
            )
            event_metrics = st.columns(4)
            event_metrics[0].metric("라벨 행", f"{len(event_labels):,}")
            event_metrics[1].metric("Validation 이벤트", f"{validation_event_count:,}")
            event_metrics[2].metric("상위 10% 포착", f"{captured_event_count:,}")
            event_metrics[3].metric("Event Capture Rate", f"{capture_rate * 100:.1f}%")

            event_comparison = (
                validation_df.assign(event_group=validation_df["event_flag"].map({True: "Event", False: "No Event"}))
                .groupby("event_group")
                .agg(
                    company_years=("company_name", "count"),
                    avg_final_risk=("final_risk_score", "mean"),
                    median_final_risk=("final_risk_score", "median"),
                )
                .reset_index()
            )
            event_comparison["avg_final_risk"] = event_comparison["avg_final_risk"].round(2)
            event_comparison["median_final_risk"] = event_comparison["median_final_risk"].round(2)

            event_fig = px.bar(
                event_comparison,
                x="event_group",
                y="avg_final_risk",
                color="event_group",
                labels={"event_group": "Event Group", "avg_final_risk": "평균 Final Risk"},
                title="이벤트 라벨 여부별 평균 리스크",
            )
            event_fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(style_chart(event_fig), width="stretch")

            st.dataframe(
                captured_events.sort_values("final_risk_score", ascending=False)[
                    [
                        "stock_code",
                        "company_name",
                        "industry",
                        "final_risk_score",
                        "event_types",
                        "event_sources",
                    ]
                ]
                .head(10)
                .rename(
                    columns={
                        "stock_code": "종목코드",
                        "company_name": "회사명",
                        "industry": "Industry",
                        "final_risk_score": "Final Risk",
                        "event_types": "Event Type",
                        "event_sources": "Source",
                    }
                ),
                width="stretch",
                hide_index=True,
            )

    with diag_tabs[3]:
        st.markdown(
            """
            - **결론이 아니라 우선순위**: Final Risk는 감사 결론이나 부정 판정이 아니라, 감사인이 먼저 검토할 회사를 정렬하기 위한 risk prioritization 점수입니다.
            - **공시 데이터 한계**: 내부 원장, 전표, 계약서, 수금내역이 없기 때문에 특정 전표를 지목하지 않고 계정 영역과 질문 후보만 제시합니다.
            - **결측치 처리**: 지표 결측은 Industry-Year median을 우선 사용하고, 표본이 부족하면 Year median과 Global median으로 보완합니다.
            - **극단값 통제**: ML 입력값은 winsorization과 RobustScaler를 거쳐 회사 규모나 단일 극단값의 영향을 줄입니다.
            - **검증 방식**: 현재 검증 탭은 과거 연도를 기준 분포로 두고 최신 연도를 hold-out으로 보는 시간 기준 검증입니다. 외부 제재, 정정공시, 감사의견 등 라벨을 붙이면 사후 이벤트 기반 검증으로 확장할 수 있습니다.
            - **모델 해석**: Accounting Risk는 설명 가능한 회계 지표, Peer Risk는 업종 내 이례성, ML Risk는 여러 지표가 동시에 움직이는 복합 패턴을 봅니다.
            """
        )
