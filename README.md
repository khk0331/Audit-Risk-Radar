# Audit Risk Radar

Audit Risk Radar는 DART 공시 재무제표를 이용해 감사 대상 회사의 재무 흐름, 동종기업 대비 위치, 주요 회계 지표 변동을 감사계획 단계에서 구조화하는 Streamlit 기반 planning analytics dashboard입니다.

이 프로젝트는 부정 적발이나 감사 결론을 내리는 모델이 아닙니다. 내부 원장, 전표, 계약서, 수금내역 없이도 공시 재무제표만으로 감사인이 먼저 확인해야 할 계정과 질문을 정리하는 데 목적이 있습니다.

## Executive Summary

- **Problem**: 감사인은 감사계획 단계에서 회사의 사업·재무 리스크를 빠르게 이해해야 하지만, 공시 재무제표만으로는 계정 변동, peer 대비 위치, 이익과 현금흐름의 괴리를 한눈에 보기 어렵습니다.
- **Solution**: DART 재무제표를 표준 계정 체계로 정리하고, Beneish-style 지표, peer 비교, ML anomaly signal을 결합해 회사별 감사계획 신호를 시각화했습니다.
- **Output**: 회사 검색 중심 대시보드, M-Score 기준선, 주요 회계 지표 추세, 대표 peer 비교, 공시 기반 확인 포인트를 제공합니다.
- **Scope**: 부정 탐지 모델이 아니라, 감사인이 더 좋은 질문을 더 일찍 설계하도록 돕는 디지털 감사계획 보조 도구입니다.

## Current Dataset

저장소에는 기본 실행에 필요한 사전 수집 데이터가 포함되어 있습니다.

- Raw DART panel: `2,574` companies / `11,583` company-year rows
- Scored dashboard dataset: `2,436` companies / `8,947` company-year rows
- Period: raw collection `2020-2024`, scored rows mostly `2021-2024`
- Universe: KRX 상장회사와 DART corp code를 매칭하고, 금융회사·SPAC·리츠성 특수목적회사는 분석 목적에 맞게 제외

기본 대시보드 실행에는 **DART API key가 필요하지 않습니다.** API key는 데이터를 새로 수집하거나 업데이트할 때만 필요합니다.

## Key Features

- Company search 중심의 감사계획 분석 화면
- DART/OpenDART 재무제표 수집 및 KRX 상장사 universe 매칭
- 회사별 계정명 차이를 보완하는 표준 계정 매핑 로직
- Beneish-style M-Score 및 DSRI, GMI, AQI, SGI, SGAI, LVGI, TATA 지표 계산
- Industry/year 및 matched peer 기반 비교 분석
- Isolation Forest와 PCA reconstruction error 기반 비지도 이상 패턴 탐지
- M-Score `-2.22` 기준선 시각화
- 회사별 주요 지표, 연도별 산출 내역, peer 비교군 표시
- 공시 재무제표와 주석으로 먼저 확인할 수 있는 ISA/IFRS 기반 질문 제시
- 계정 매핑 품질 점검 및 결측/대체 지표 진단

## Methodology

### 1. Accounting Risk

Beneish-style 지표를 사용해 회계적 red flag를 설명 가능한 방식으로 계산합니다.

| Indicator | Meaning |
| --- | --- |
| DSRI | 매출 대비 매출채권 증가 속도 |
| GMI | 매출총이익률 악화 |
| AQI | 자산 품질 변화 |
| SGI | 매출 성장률 |
| SGAI | 매출 대비 판관비성 비용 변화 |
| LVGI | 레버리지 변화 |
| TATA | 이익-현금흐름 괴리 |

M-Score는 전통적인 `-2.22` 기준선을 참고하지만, 이 앱에서는 단독 결론이 아니라 감사계획 단계의 회계적 신호로 사용합니다.

### 2. Peer Risk

회사 자체의 전년 대비 변화만 보면 산업 전반의 변화와 회사 고유 이슈를 구분하기 어렵습니다. 따라서 동일 Year/Industry 비교와 함께 매출, 총자산, 수익성, 성장성이 유사한 matched peer를 사용해 상대적 이례성을 확인합니다.

### 3. ML Risk

확정 부정 라벨이 부족한 공시 데이터 특성을 고려해 비지도 방식의 anomaly signal을 보조 지표로 사용했습니다.

- `Isolation Forest`: 주변 회사들과 다른 정도
- `PCA reconstruction error`: 일반적인 재무비율 조합으로 설명하기 어려운 정도
- `RobustScaler` 및 winsorization: 극단값과 규모 차이의 영향을 완화

ML Risk는 결론을 내리는 모델이 아니라, Accounting/Peer 분석에서 놓칠 수 있는 복합 패턴을 보조적으로 알려주는 신호입니다.

## Account Mapping Challenge

가장 중요한 기술적 난제는 DART에서 데이터를 가져오는 것 자체보다 **회사별 계정과목명 차이를 표준 계정으로 변환하는 것**이었습니다.

예를 들어 회사마다 매출을 다음처럼 다르게 표시할 수 있습니다.

- 매출액
- 영업수익
- 수익
- 용역매출
- 게임매출
- 콘텐츠매출

이를 보완하기 위해 다음 로직을 결합했습니다.

- DART/IFRS `account_id` 우선 매칭
- 한국어 계정명 후보 사전
- 잘못된 broad account 매칭을 막기 위한 exclusion keyword
- BS, IS, CF 등 재무제표 유형 선호도
- 연결재무제표 우선 사용
- fuzzy text matching
- 매칭 실패 및 의심 계정 로그 저장

또한 `scripts/audit_mapping_quality.py`로 매핑 품질을 사후 점검합니다. 예를 들어 매출총이익이 영업수익 계정에 매칭되거나, 매출채권이 자산총계에 매칭되는 경우를 review queue로 표시합니다.

## How To Run

For normal dashboard review, choose **one** quick start path for your operating system. You do not need to run both Windows and macOS/Linux commands.

The **Full development setup** section is optional. Use it only if you want to run tests, inspect scripts, or recollect data.

### Option A. Windows dashboard only

Windows users can run the dashboard with Python already installed.

Open PowerShell in the repository folder and run:

```powershell
.\run_windows.bat
```


The script creates a local `.venv`, installs dashboard-only dependencies from `requirements-app.txt`, and opens Streamlit at:

```text
http://127.0.0.1:8501
```

See [Windows Setup Guide](docs/windows_setup.md) for troubleshooting.

### Option B. macOS / Linux dashboard only

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-app.txt
python -m streamlit run audit_risk_radar/app.py --server.address 127.0.0.1 --server.port 8501
```

### Optional. Full development setup

This section is not required to open the dashboard. Use it only when running tests, data collection scripts, or optional DART/FinanceDataReader workflows.

Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover tests
```

macOS / Linux:

```bash
python -m pip install -r requirements.txt
python -m unittest discover tests
```

Run dashboard manually if needed:

Windows:

```powershell
.\.venv\Scripts\python.exe -m streamlit run audit_risk_radar\app.py
```

macOS / Linux:

```bash
python -m streamlit run audit_risk_radar/app.py
```

Streamlit이 출력하는 로컬 주소를 열면 됩니다.

```text
http://localhost:8501
```

## Optional: Recollect DART Data

기본 실행에는 API key가 필요하지 않습니다. 아래 절차는 데이터를 새로 수집하거나 업데이트할 때만 사용합니다.

```bash
export DART_API_KEY="your_open_dart_api_key"
```

```bash
python3 scripts/backfill_missing_listed_companies.py \
  --start-year 2020 \
  --end-year 2024 \
  --sleep 0.03 \
  --checkpoint-every 25 \
  --skip-existing-failures \
  --universe data/raw/krx/current_listed_companies.csv \
  --input data/processed/financials_panel_2020_2024_full.csv \
  --output data/processed/financials_panel_2020_2024_full.csv \
  --failure-log data/processed/dart_backfill_failures.csv
```

## Repository Structure

```text
audit_risk_radar/
  app.py                         # Streamlit dashboard
src/
  dart_pipeline.py               # DART collection and account matching
  data_loader.py                 # Processed/sample data loader
  metrics.py                     # Beneish-style feature engineering
  risk_scoring.py                # Accounting, peer, ML, final risk scores
  peer_selection.py              # Representative peer selection
  explanations.py                # Korean explanations and audit questions
  event_labels.py                # Weak-label template support
scripts/
  fetch_krx_universe.py
  backfill_missing_listed_companies.py
  collect_dart_panel.py
  audit_mapping_quality.py
docs/
  methodology.md
  implementation_report.md
  implementation_report_ko.md
  windows_setup.md
data/
  processed/                     # Pre-collected execution data
  raw/                           # DART/KRX reference data
  sample/                        # Small fallback sample data
tests/
  test_metrics.py
```

## Project Value

이 프로젝트의 핵심은 “AI가 감사를 대체한다”가 아니라, **감사인이 더 빠르게 회사의 리스크 구조를 이해하고 더 좋은 질문을 설계하도록 돕는 것**입니다.

프로젝트가 제공하는 실무적 가치는 다음과 같습니다.

1. 공시 재무제표만으로 감사계획 단계에서 관찰 가능한 위험 신호를 구조화합니다.
2. 회사별 계정명 차이를 표준 항목으로 매핑해 지표 계산의 일관성을 높입니다.
3. Beneish-style 지표로 설명 가능한 회계적 기준점을 제공합니다.
4. Peer 비교와 ML anomaly를 더해 회사 고유 이례성과 복합 패턴을 보완합니다.
5. 최종 결과를 점수에 그치지 않고 공시 기반 확인 포인트로 연결합니다.

## Limitations

- 공시 재무제표만 사용하므로 원장, 전표, 계약서, 수금내역 수준의 결론을 낼 수 없습니다.
- Final Risk는 부정 확률이나 공식 감사기준이 아니라 내부 모델의 상대적 planning signal입니다.
- Peer 비교는 산업 분류와 공시 데이터의 완전성에 영향을 받습니다.
- 계정명 매핑 품질은 지표 계산과 점수에 직접 영향을 줍니다.
- 실제 감사에서는 중요성, 내부통제, 회사 특수성, 내부자료 접근 가능성을 함께 고려해야 합니다.

## More Detail

- [Methodology](docs/methodology.md)
- [Implementation Report](docs/implementation_report.md)
- [Korean Implementation Report](docs/implementation_report_ko.md)
