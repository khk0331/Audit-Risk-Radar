from __future__ import annotations

import argparse
import io
import os
import re
import time
import zipfile
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd
import requests

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - keeps the collector runnable before optional deps are installed.
    def tqdm(iterable, **_kwargs):
        return iterable


DART_BASE_URL = "https://opendart.fss.or.kr/api"
REPORT_CODE_ANNUAL = "11011"

ACCOUNT_CANDIDATES = {
    "revenue": {
        "ids": ["ifrs-full_Revenue", "ifrs-full_SalesRevenue", "ifrs-full_RevenueFromContractsWithCustomers"],
        "keywords": ["매출액", "수익", "영업수익", "용역매출", "게임매출", "콘텐츠매출"],
        "exclude_keywords": ["금융수익", "이자수익", "배당수익", "기타수익", "영업외수익"],
        "preferred_statement": ["IS"],
    },
    "receivables": {
        "ids": [
            "ifrs-full_TradeAndOtherCurrentReceivables",
            "dart_ShortTermTradeReceivable",
            "ifrs-full_TradeReceivables",
        ],
        "keywords": ["매출채권", "매출채권및기타채권", "매출채권 및 기타채권", "영업채권", "미수금"],
        "exclude_keywords": ["기타채권", "장기", "비유동"],
        "preferred_statement": ["BS"],
    },
    "gross_profit": {
        "ids": ["ifrs-full_GrossProfit"],
        "keywords": ["매출총이익", "매출 총이익", "영업총이익", "매출총손익"],
        "exclude_keywords": ["영업이익", "영업손익", "영업손실"],
        "preferred_statement": ["IS"],
    },
    "operating_income": {
        "ids": ["dart_OperatingIncomeLoss", "ifrs-full_ProfitLossFromOperatingActivities"],
        "keywords": ["영업이익", "영업손익", "영업손실"],
        "exclude_keywords": ["계속영업", "중단영업"],
        "preferred_statement": ["IS"],
    },
    "total_assets": {
        "ids": ["ifrs-full_Assets"],
        "keywords": ["자산총계", "자산 총계"],
        "exclude_keywords": ["유동자산", "비유동자산"],
        "preferred_statement": ["BS"],
    },
    "current_assets": {
        "ids": ["ifrs-full_CurrentAssets"],
        "keywords": ["유동자산"],
        "exclude_keywords": ["비유동자산"],
        "preferred_statement": ["BS"],
    },
    "ppe": {
        "ids": ["ifrs-full_PropertyPlantAndEquipment"],
        "keywords": ["유형자산", "유형자산순액"],
        "exclude_keywords": ["투자부동산"],
        "preferred_statement": ["BS"],
    },
    "total_liabilities": {
        "ids": ["ifrs-full_Liabilities"],
        "keywords": ["부채총계", "부채 총계"],
        "exclude_keywords": ["유동부채", "비유동부채"],
        "preferred_statement": ["BS"],
    },
    "net_income": {
        "ids": ["ifrs-full_ProfitLoss", "ifrs-full_ProfitLossAttributableToOwnersOfParent"],
        "keywords": ["당기순이익", "당기순손익", "분기순이익", "연결당기순이익"],
        "exclude_keywords": ["기타포괄", "총포괄", "지배기업"],
        "preferred_statement": ["IS"],
    },
    "operating_cash_flow": {
        "ids": ["ifrs-full_CashFlowsFromUsedInOperatingActivities"],
        "keywords": ["영업활동현금흐름", "영업활동 현금흐름", "영업활동으로인한현금흐름", "영업에서창출된현금"],
        "exclude_keywords": [],
        "preferred_statement": ["CF"],
    },
}


@dataclass(frozen=True)
class DartCompany:
    corp_code: str
    stock_code: str
    company_name: str
    industry_code: str = ""
    industry: str = "Unclassified"


def get_api_key(explicit_key: str | None = None) -> str:
    api_key = explicit_key or os.getenv("DART_API_KEY") or os.getenv("OPENDART_API_KEY")
    if not api_key:
        raise ValueError("DART API key is missing. Set DART_API_KEY or pass --api-key.")
    return api_key


def load_corp_codes(api_key: str, cache_path: str | Path = "data/raw/dart/corp_codes.csv") -> pd.DataFrame:
    cache_path = Path(cache_path)
    if cache_path.exists():
        return pd.read_csv(cache_path, dtype={"corp_code": str, "stock_code": str})

    response = requests.get(f"{DART_BASE_URL}/corpCode.xml", params={"crtfc_key": api_key}, timeout=60)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        xml_name = archive.namelist()[0]
        xml_bytes = archive.read(xml_name)

    root = ElementTree.fromstring(xml_bytes)
    rows = []
    for item in root.findall("list"):
        stock_code = _text(item, "stock_code")
        if not stock_code:
            continue
        rows.append(
            {
                "corp_code": _text(item, "corp_code"),
                "company_name": _text(item, "corp_name"),
                "stock_code": stock_code.zfill(6),
                "modify_date": _text(item, "modify_date"),
            }
        )

    df = pd.DataFrame(rows).drop_duplicates(subset=["stock_code"]).sort_values("stock_code")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False, encoding="utf-8-sig")
    return df


def load_all_corp_codes(api_key: str, cache_path: str | Path = "data/raw/dart/corp_codes_all.csv") -> pd.DataFrame:
    cache_path = Path(cache_path)
    if cache_path.exists():
        return pd.read_csv(cache_path, dtype={"corp_code": str, "stock_code": str})

    response = requests.get(f"{DART_BASE_URL}/corpCode.xml", params={"crtfc_key": api_key}, timeout=60)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        xml_name = archive.namelist()[0]
        xml_bytes = archive.read(xml_name)

    root = ElementTree.fromstring(xml_bytes)
    rows = []
    for item in root.findall("list"):
        stock_code = _text(item, "stock_code")
        rows.append(
            {
                "corp_code": _text(item, "corp_code"),
                "company_name": _text(item, "corp_name"),
                "stock_code": stock_code.zfill(6) if stock_code else "",
                "modify_date": _text(item, "modify_date"),
            }
        )

    df = pd.DataFrame(rows).drop_duplicates(subset=["corp_code"]).sort_values("company_name")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False, encoding="utf-8-sig")
    return df


def search_dart_companies(api_key: str, query: str, limit: int = 30) -> pd.DataFrame:
    corp_codes = load_all_corp_codes(api_key)
    query = str(query or "").strip().lower()
    if not query:
        return corp_codes.head(0)

    search_text = (
        corp_codes["company_name"].fillna("").astype(str)
        + " "
        + corp_codes["stock_code"].fillna("").astype(str)
        + " "
        + corp_codes["corp_code"].fillna("").astype(str)
    ).str.lower()
    result = corp_codes[search_text.str.contains(query, regex=False)].copy()
    result["listed"] = result["stock_code"].fillna("").astype(str).str.len() > 0
    return result.sort_values(["listed", "company_name"], ascending=[False, True]).head(limit)


def collect_single_company_panel(
    api_key: str,
    corp_code: str,
    company_name: str,
    stock_code: str = "",
    start_year: int = 2019,
    end_year: int = 2024,
    sleep_seconds: float = 0.2,
    output_path: str | Path = "data/processed/financials_panel.csv",
) -> pd.DataFrame:
    stock_code = str(stock_code or "").strip().zfill(6) if str(stock_code or "").strip() else f"C{corp_code}"
    profile = fetch_company_profile(api_key, corp_code) or {}
    industry_code = str(profile.get("industry_code", "") or profile.get("induty_code", "") or "")
    company = DartCompany(
        corp_code=str(corp_code),
        stock_code=stock_code,
        company_name=str(company_name),
        industry_code=industry_code,
        industry=map_industry_code(industry_code),
    )

    rows = _collect_company_rows(api_key, company, start_year, end_year, sleep_seconds)

    if not rows:
        return pd.DataFrame()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_panel = pd.DataFrame(rows)
    if output_path.exists():
        existing = pd.read_csv(output_path, dtype={"stock_code": str})
        new_panel = pd.concat([existing, new_panel], ignore_index=True)
    new_panel = new_panel.drop_duplicates(subset=["stock_code", "year"], keep="last").sort_values(
        ["stock_code", "year"]
    )
    new_panel.to_csv(output_path, index=False, encoding="utf-8-sig")
    return pd.DataFrame(rows)


def collect_company_and_peer_panel(
    api_key: str,
    corp_code: str,
    company_name: str,
    stock_code: str = "",
    start_year: int = 2020,
    end_year: int = 2024,
    peer_limit: int = 20,
    profile_scan_limit: int = 300,
    sleep_seconds: float = 0.2,
    output_path: str | Path = "data/processed/financials_panel.csv",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    target = _build_dart_company(api_key, corp_code, company_name, stock_code)
    print(
        f"Collecting target and peers: {target.company_name}({target.stock_code}), "
        f"industry_code={target.industry_code}, years={start_year}-{end_year}, peer_limit={peer_limit}"
    )
    peers = find_peer_company_candidates(
        api_key=api_key,
        target_company=target,
        peer_limit=peer_limit,
        profile_scan_limit=profile_scan_limit,
    )
    print(f"Peer candidates selected: {len(peers)}")
    companies = [target] + peers

    all_rows = []
    collection_summary = []
    for company in companies:
        print(f"Collecting financial statements: {company.company_name}({company.stock_code})")
        rows, diagnostics = _collect_company_rows_with_diagnostics(
            api_key, company, start_year, end_year, sleep_seconds
        )
        all_rows.extend(rows)
        collection_summary.append(
            {
                "stock_code": company.stock_code,
                "company_name": company.company_name,
                "industry_code": company.industry_code,
                "industry": company.industry,
                "role": "target" if company.corp_code == target.corp_code else "peer",
                "collected_years": len(rows),
                "diagnostics": "; ".join(diagnostics[:3]),
            }
        )

    collected = pd.DataFrame(all_rows)
    summary = pd.DataFrame(collection_summary)
    if collected.empty:
        return collected, summary

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        existing = pd.read_csv(output_path, dtype={"stock_code": str})
        collected = pd.concat([existing, collected], ignore_index=True)
    collected = collected.drop_duplicates(subset=["stock_code", "year"], keep="last").sort_values(
        ["stock_code", "year"]
    )
    collected.to_csv(output_path, index=False, encoding="utf-8-sig")
    return pd.DataFrame(all_rows), summary


def find_peer_company_candidates(
    api_key: str,
    target_company: DartCompany,
    peer_limit: int = 20,
    profile_scan_limit: int = 1200,
    cache_path: str | Path = "data/raw/dart/company_profiles.csv",
) -> list[DartCompany]:
    target_prefix = str(target_company.industry_code or "")[:2]
    if not target_prefix:
        return []

    corp_codes = load_corp_codes(api_key)
    corp_codes = corp_codes[corp_codes["corp_code"].astype(str) != str(target_company.corp_code)].copy()
    corp_codes = corp_codes.sort_values("stock_code").head(profile_scan_limit)
    profiles = load_company_profile_cache(cache_path)

    exact_matches: list[DartCompany] = []
    prefix_matches: list[DartCompany] = []
    for row in corp_codes.itertuples(index=False):
        profile = get_cached_or_fetch_profile(api_key, row.corp_code, row.stock_code, profiles)
        industry_code = str(profile.get("industry_code", "") or "")
        if _is_financial_industry(industry_code) or _is_special_purpose_name(row.company_name):
            continue
        if not industry_code.startswith(target_prefix):
            continue
        candidate = DartCompany(
            corp_code=row.corp_code,
            stock_code=str(row.stock_code).zfill(6),
            company_name=row.company_name,
            industry_code=industry_code,
            industry=map_industry_code(industry_code),
        )
        if industry_code == target_company.industry_code:
            exact_matches.append(candidate)
        else:
            prefix_matches.append(candidate)
        if len(exact_matches) + len(prefix_matches) >= peer_limit * 3:
            break

    save_company_profile_cache(profiles, cache_path)
    return (exact_matches + prefix_matches)[:peer_limit]


def _build_dart_company(api_key: str, corp_code: str, company_name: str, stock_code: str = "") -> DartCompany:
    stock_code = str(stock_code or "").strip().zfill(6) if str(stock_code or "").strip() else f"C{corp_code}"
    profile = fetch_company_profile(api_key, corp_code) or {}
    industry_code = str(profile.get("industry_code", "") or profile.get("induty_code", "") or "")
    return DartCompany(
        corp_code=str(corp_code),
        stock_code=stock_code,
        company_name=str(company_name),
        industry_code=industry_code,
        industry=map_industry_code(industry_code),
    )


def _collect_company_rows(
    api_key: str,
    company: DartCompany,
    start_year: int,
    end_year: int,
    sleep_seconds: float,
) -> list[dict[str, object]]:
    rows, _diagnostics = _collect_company_rows_with_diagnostics(
        api_key, company, start_year, end_year, sleep_seconds
    )
    return rows


def _collect_company_rows_with_diagnostics(
    api_key: str,
    company: DartCompany,
    start_year: int,
    end_year: int,
    sleep_seconds: float,
) -> tuple[list[dict[str, object]], list[str]]:
    rows = []
    diagnostics = []
    for year in range(start_year, end_year + 1):
        fs = fetch_financial_statement(api_key, company, year, fs_div="CFS")
        if fs is None:
            fs = fetch_financial_statement(api_key, company, year, fs_div="OFS")
        if fs is not None:
            row, row_diagnostics = extract_standard_row_with_diagnostics(fs, company, year)
            if row is not None:
                rows.append(row)
            else:
                diagnostics.append(f"{year}: {'; '.join(row_diagnostics)}")
        else:
            diagnostics.append(f"{year}: 표준 재무제표 API 응답 없음")
        time.sleep(sleep_seconds)
    return rows, diagnostics


def build_company_universe(corp_codes: pd.DataFrame, limit: int = 500) -> list[DartCompany]:
    listed = corp_codes.dropna(subset=["stock_code"]).copy()
    listed["stock_code"] = listed["stock_code"].astype(str).str.zfill(6)
    if "exclude" in listed.columns:
        listed = listed[~listed["exclude"].fillna(False)]
    listed = listed.sort_values("stock_code").head(limit)
    return [
        DartCompany(
            corp_code=row.corp_code,
            stock_code=row.stock_code,
            company_name=row.company_name,
            industry_code=getattr(row, "industry_code", "") or "",
            industry=getattr(row, "industry", "Unclassified") or "Unclassified",
        )
        for row in listed.itertuples(index=False)
    ]


def select_company_universe(
    api_key: str,
    corp_codes: pd.DataFrame,
    limit: int = 500,
    cache_path: str | Path = "data/raw/dart/company_profiles.csv",
    exclude_stock_codes: set[str] | None = None,
) -> list[DartCompany]:
    listed = corp_codes.dropna(subset=["stock_code"]).copy()
    listed["stock_code"] = listed["stock_code"].astype(str).str.zfill(6)
    if exclude_stock_codes:
        normalized_exclusions = {str(code).zfill(6) for code in exclude_stock_codes}
        listed = listed[~listed["stock_code"].isin(normalized_exclusions)]
    listed = listed.sort_values("stock_code")

    profiles = load_company_profile_cache(cache_path)
    selected: list[DartCompany] = []
    excluded_count = 0

    for row_index, row in enumerate(tqdm(listed.itertuples(index=False), total=len(listed), desc="Selecting companies"), start=1):
        profile = get_cached_or_fetch_profile(api_key, row.corp_code, row.stock_code, profiles)
        industry_code = str(profile.get("industry_code", "") or "")
        industry = map_industry_code(industry_code)
        excluded = _is_excluded_financial_company(industry_code, row.company_name)

        if excluded:
            excluded_count += 1
            continue

        selected.append(
            DartCompany(
                corp_code=row.corp_code,
                stock_code=row.stock_code,
                company_name=row.company_name,
                industry_code=industry_code,
                industry=industry,
            )
        )
        if len(selected) >= limit:
            break
        if row_index % 50 == 0:
            save_company_profile_cache(profiles, cache_path)
            print(
                f"Universe scan checkpoint: scanned {row_index:,}, selected {len(selected):,}, "
                f"excluded {excluded_count:,}, cached profiles {len(profiles):,}",
                flush=True,
            )

    save_company_profile_cache(profiles, cache_path)
    print(f"Company universe: {len(selected):,} selected after skipping {excluded_count:,} financial/SPAC candidates.")
    return selected


def load_company_profile_cache(cache_path: str | Path = "data/raw/dart/company_profiles.csv") -> dict[str, dict[str, str]]:
    cache_path = Path(cache_path)
    if not cache_path.exists():
        return {}

    df = pd.read_csv(cache_path, dtype={"corp_code": str, "stock_code": str, "industry_code": str})
    return {
        row.corp_code: {
            "corp_code": row.corp_code,
            "stock_code": row.stock_code,
            "industry_code": getattr(row, "industry_code", "") or "",
            "corp_cls": getattr(row, "corp_cls", "") or "",
        }
        for row in df.itertuples(index=False)
    }


def save_company_profile_cache(
    profiles: dict[str, dict[str, str]],
    cache_path: str | Path = "data/raw/dart/company_profiles.csv",
) -> None:
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if not profiles:
        return
    pd.DataFrame(profiles.values()).sort_values("stock_code").to_csv(
        cache_path,
        index=False,
        encoding="utf-8-sig",
    )


def get_cached_or_fetch_profile(
    api_key: str,
    corp_code: str,
    stock_code: str,
    profiles: dict[str, dict[str, str]],
) -> dict[str, str]:
    if corp_code in profiles:
        return profiles[corp_code]

    profile = fetch_company_profile(api_key, corp_code) or {}
    normalized = {
        "corp_code": corp_code,
        "stock_code": stock_code,
        "industry_code": profile.get("induty_code", "") or "",
        "corp_cls": profile.get("corp_cls", "") or "",
    }
    profiles[corp_code] = normalized
    time.sleep(0.05)
    return normalized


def fetch_company_profile(api_key: str, corp_code: str) -> dict[str, str] | None:
    try:
        response = requests.get(
            f"{DART_BASE_URL}/company.json",
            params={"crtfc_key": api_key, "corp_code": corp_code},
            timeout=(5, 10),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Company profile fetch failed for {corp_code}: {exc}", flush=True)
        return None
    payload = response.json()
    if payload.get("status") != "000":
        return None
    return payload


def _merge_profiles(corp_codes: pd.DataFrame, profiles: pd.DataFrame) -> pd.DataFrame:
    if profiles.empty:
        result = corp_codes.copy()
        result["industry_code"] = ""
        result["industry"] = "Unclassified"
        result["exclude"] = result["company_name"].map(_is_special_purpose_name)
        return result

    result = corp_codes.merge(
        profiles[["corp_code", "industry_code", "corp_cls"]],
        on="corp_code",
        how="left",
    )
    result["industry_code"] = result["industry_code"].fillna("").astype(str)
    result["industry"] = result["industry_code"].map(map_industry_code)
    result["exclude"] = result.apply(
        lambda row: _is_excluded_financial_company(row["industry_code"], row["company_name"]),
        axis=1,
    )
    return result


def map_industry_code(industry_code: str) -> str:
    code = str(industry_code or "").strip()
    prefix = code[:2]
    mapping = {
        "01": "Agriculture",
        "02": "Forestry",
        "03": "Fishing",
        "05": "Mining",
        "06": "Mining",
        "07": "Mining",
        "08": "Mining",
        "10": "Manufacturing",
        "11": "Manufacturing",
        "12": "Manufacturing",
        "13": "Manufacturing",
        "14": "Manufacturing",
        "15": "Manufacturing",
        "16": "Manufacturing",
        "17": "Manufacturing",
        "18": "Manufacturing",
        "19": "Manufacturing",
        "20": "Manufacturing",
        "21": "Manufacturing",
        "22": "Manufacturing",
        "23": "Manufacturing",
        "24": "Manufacturing",
        "25": "Manufacturing",
        "26": "Manufacturing",
        "27": "Manufacturing",
        "28": "Manufacturing",
        "29": "Manufacturing",
        "30": "Manufacturing",
        "31": "Manufacturing",
        "32": "Manufacturing",
        "33": "Manufacturing",
        "34": "Manufacturing",
        "35": "Utilities",
        "36": "Utilities",
        "37": "Utilities",
        "38": "Utilities",
        "39": "Utilities",
        "41": "Construction",
        "42": "Construction",
        "45": "Wholesale/Retail",
        "46": "Wholesale/Retail",
        "47": "Wholesale/Retail",
        "49": "Transportation",
        "50": "Transportation",
        "51": "Transportation",
        "52": "Transportation",
        "55": "Hospitality",
        "56": "Hospitality",
        "58": "Information/Communication",
        "59": "Information/Communication",
        "60": "Information/Communication",
        "61": "Information/Communication",
        "62": "Information/Communication",
        "63": "Information/Communication",
        "68": "Real Estate",
        "70": "Professional Services",
        "71": "Professional Services",
        "72": "Professional Services",
        "73": "Professional Services",
        "74": "Professional Services",
        "75": "Business Services",
        "76": "Business Services",
        "85": "Education",
        "86": "Healthcare",
        "87": "Healthcare",
        "90": "Arts/Sports",
        "91": "Arts/Sports",
    }
    if _is_financial_industry(code):
        return "Financial"
    return mapping.get(prefix, "Unclassified")


def _is_financial_industry(industry_code: str) -> bool:
    code = str(industry_code or "").strip()
    if code.startswith("649"):
        return False
    return code[:2] in {"64", "65", "66"}


def _is_excluded_financial_company(industry_code: str, company_name: str) -> bool:
    return (
        _is_financial_industry(industry_code)
        or _is_financial_company_name(company_name)
        or _is_special_purpose_name(company_name)
    )


def _is_financial_company_name(company_name: str) -> bool:
    normalized = str(company_name or "").lower().replace(" ", "")
    keywords = [
        "금융",
        "은행",
        "증권",
        "보험",
        "생명보험",
        "손보",
        "화재",
        "카드",
        "캐피탈",
        "인베스트",
        "투자",
        "신탁",
        "자산운용",
        "저축은행",
        "파이낸",
        "리츠",
        "reit",
        "리얼티",
        "인프라",
        "신한지주",
        "미래에셋생명",
        "한화생명",
        "동양생명",
        "kb금융",
        "우리금융",
        "하나금융",
        "bnk금융",
        "dgb금융",
        "jb금융",
    ]
    return any(keyword in normalized for keyword in keywords)


def _is_special_purpose_name(company_name: str) -> bool:
    normalized = str(company_name or "").lower().replace(" ", "")
    return any(keyword in normalized for keyword in ["스팩", "기업인수목적", "spac"])


def fetch_financial_statement(
    api_key: str,
    company: DartCompany,
    year: int,
    fs_div: str = "CFS",
) -> pd.DataFrame | None:
    params = {
        "crtfc_key": api_key,
        "corp_code": company.corp_code,
        "bsns_year": str(year),
        "reprt_code": REPORT_CODE_ANNUAL,
        "fs_div": fs_div,
    }
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = requests.get(
                f"{DART_BASE_URL}/fnlttSinglAcntAll.json",
                params=params,
                timeout=(5, 45),
            )
            response.raise_for_status()
            payload = response.json()
            break
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1.0)
    else:
        print(
            f"Financial statement fetch failed for {company.company_name} "
            f"({company.stock_code}) {year} {fs_div}: {last_error}",
            flush=True,
        )
        return None
    if payload.get("status") != "000":
        return None
    rows = payload.get("list", [])
    if not rows:
        return None
    return pd.DataFrame(rows)


def extract_standard_row(fs: pd.DataFrame, company: DartCompany, year: int) -> dict[str, object] | None:
    row, _diagnostics = extract_standard_row_with_diagnostics(fs, company, year)
    return row


def extract_standard_row_with_diagnostics(
    fs: pd.DataFrame,
    company: DartCompany,
    year: int,
) -> tuple[dict[str, object] | None, list[str]]:
    # Convert one company's raw DART statement rows into the standard schema
    # used by the metrics layer. This is the main guardrail against company-by-
    # company account-name differences breaking downstream risk scores.
    values = {
        "year": year,
        "stock_code": company.stock_code,
        "company_name": company.company_name,
        "industry": company.industry,
        "industry_code": company.industry_code,
    }

    matched_accounts = {}
    for target, spec in ACCOUNT_CANDIDATES.items():
        # Each target account is matched using IFRS/DART account_id, Korean name
        # candidates, exclusion keywords, and preferred statement type.
        amount, match = _extract_amount_with_match(fs, spec)
        values[target] = amount
        if match:
            matched_accounts[target] = match

    values["gross_profit_proxy_used"] = False
    if pd.isna(values["gross_profit"]) and not pd.isna(values["operating_income"]):
        # Some service companies do not provide a clean gross-profit line. Using
        # operating income as an explicit proxy is better than silently dropping
        # the company, and the proxy flag is carried into later quality checks.
        values["gross_profit"] = values["operating_income"]
        values["gross_profit_proxy_used"] = True
        matched_accounts["gross_profit"] = {
            "account_name": "영업이익 기반 proxy",
            "account_id": "",
            "statement": "IS",
            "score": 0,
        }

    essential = ["revenue", "total_assets", "gross_profit", "operating_income"]
    missing_essential = [col for col in essential if pd.isna(values[col])]
    if missing_essential:
        # Return account-name samples with the failure so the mapping dictionary
        # can be improved later instead of leaving a black-box collection error.
        account_sample = summarize_statement_accounts(fs)
        return None, [
            "필수 계정 자동 매칭 실패",
            f"누락 필수 계정={', '.join(missing_essential)}",
            f"계정명 샘플={account_sample}",
        ]
    values["matched_accounts"] = "; ".join(
        f"{target}:{match['account_name']}" for target, match in matched_accounts.items()
    )
    values["missing_optional_accounts"] = ", ".join(
        target for target in ACCOUNT_CANDIDATES if pd.isna(values.get(target))
    )
    return values, []


def summarize_statement_accounts(fs: pd.DataFrame, limit: int = 18) -> str:
    if fs.empty or "account_nm" not in fs.columns:
        return ""
    statement_order = {"BS": 0, "IS": 1, "CIS": 2, "CF": 3}
    sample = fs.copy()
    sample["_statement_order"] = sample.get("sj_div", "").map(statement_order).fillna(9)
    names = (
        sample.sort_values(["_statement_order", "ord"] if "ord" in sample.columns else ["_statement_order"])
        ["account_nm"]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .head(limit)
        .tolist()
    )
    return ", ".join(names)


def collect_financial_panel(
    api_key: str,
    start_year: int = 2019,
    end_year: int = 2024,
    limit: int = 500,
    sleep_seconds: float = 0.25,
    output_path: str | Path = "data/processed/financials_panel.csv",
    checkpoint_every: int = 25,
    resume: bool = True,
) -> pd.DataFrame:
    corp_codes = load_corp_codes(api_key)
    output_path = Path(output_path)
    rows = []
    completed_pairs: set[tuple[str, int]] = set()
    completed_stock_codes: set[str] = set()

    if resume and output_path.exists():
        existing = pd.read_csv(output_path, dtype={"stock_code": str})
        rows.extend(existing.to_dict("records"))
        completed_pairs = set(zip(existing["stock_code"].astype(str), existing["year"].astype(int)))
        completed_counts = existing.groupby(existing["stock_code"].astype(str).str.zfill(6))["year"].nunique()
        required_years = end_year - start_year + 1
        completed_stock_codes = set(completed_counts[completed_counts >= required_years].index)
        print(f"Resuming from {output_path}: {len(existing):,} existing company-year rows loaded.")
        print(f"Skipping {len(completed_stock_codes):,} companies that already have {required_years} years.")

    companies = select_company_universe(
        api_key,
        corp_codes,
        limit=limit,
        exclude_stock_codes=completed_stock_codes,
    )

    for company_index, company in enumerate(tqdm(companies, desc="Companies"), start=1):
        company_rows_before = len(rows)
        for year in range(start_year, end_year + 1):
            if (company.stock_code, year) in completed_pairs:
                continue
            fs = fetch_financial_statement(api_key, company, year, fs_div="CFS")
            if fs is None:
                fs = fetch_financial_statement(api_key, company, year, fs_div="OFS")
            if fs is not None:
                row = extract_standard_row(fs, company, year)
                if row is not None:
                    rows.append(row)
                    completed_pairs.add((company.stock_code, year))
            time.sleep(sleep_seconds)

        new_rows = len(rows) - company_rows_before
        print(
            f"[{company_index}/{len(companies)}] {company.company_name}({company.stock_code}) "
            f"saved rows +{new_rows}, total {len(rows):,}"
        )
        if checkpoint_every > 0 and company_index % checkpoint_every == 0:
            _save_panel(rows, output_path)
            print(f"Checkpoint saved to {output_path}")

    return _save_panel(rows, output_path)


def _save_panel(rows: list[dict[str, object]], output_path: Path) -> pd.DataFrame:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    panel = pd.DataFrame(rows)
    if not panel.empty:
        panel = panel.drop_duplicates(subset=["stock_code", "year"]).sort_values(["stock_code", "year"])
    panel.to_csv(output_path, index=False, encoding="utf-8-sig")
    return panel


def _extract_amount_with_match(fs: pd.DataFrame, spec: dict[str, object]) -> tuple[float | None, dict[str, object] | None]:
    candidates = []
    for row in fs.to_dict("records"):
        amount = _parse_amount(row.get("thstrm_amount"))
        if pd.isna(amount):
            continue
        score = _account_match_score(row, spec)
        if score <= 0:
            continue
        candidates.append((score, amount, row))

    if not candidates:
        return None, None

    # Keep the best-scoring account and return its metadata. The metadata is
    # later stored in matched_accounts so suspicious mappings can be audited.
    score, amount, row = sorted(candidates, key=lambda item: item[0], reverse=True)[0]
    match = {
        "account_id": row.get("account_id", ""),
        "account_name": row.get("account_nm", ""),
        "statement": row.get("sj_div", ""),
        "score": round(float(score), 3),
    }
    return float(amount), match


def _extract_amount(fs: pd.DataFrame, account_ids: list[str], keywords: list[str]) -> float | None:
    amount, _match = _extract_amount_with_match(
        fs,
        {
            "ids": account_ids,
            "keywords": keywords,
            "exclude_keywords": [],
            "preferred_statement": [],
        },
    )
    return amount


def _account_match_score(row: dict[str, object], spec: dict[str, object]) -> float:
    account_id = str(row.get("account_id", "") or "")
    account_name = _normalize_account_text(row.get("account_nm", ""))
    statement = str(row.get("sj_div", "") or "")
    score = 0.0

    # account_id is the strongest signal because it is less language-dependent
    # than Korean account names.
    if account_id in set(spec.get("ids", [])):
        score += 100.0

    for keyword in spec.get("keywords", []):
        # Name matching catches cases where account_id is absent or too generic.
        # Exact and substring matches are favored; fuzzy matching is a fallback.
        normalized_keyword = _normalize_account_text(keyword)
        if not normalized_keyword:
            continue
        if normalized_keyword == account_name:
            score += 60.0
        elif normalized_keyword in account_name:
            score += 42.0
        else:
            similarity = SequenceMatcher(None, normalized_keyword, account_name).ratio()
            if similarity >= 0.72:
                score += 18.0 * similarity

    for keyword in spec.get("exclude_keywords", []):
        # Exclusion keywords prevent broad accounts such as total assets or cash
        # balance from being incorrectly used as receivables or cash flow.
        normalized_keyword = _normalize_account_text(keyword)
        if normalized_keyword and normalized_keyword in account_name:
            score -= 45.0

    if statement in set(spec.get("preferred_statement", [])):
        score += 8.0

    if str(row.get("fs_div", "") or "") == "CFS":
        score += 2.0

    return score


def _parse_amount(value: object) -> float:
    if value is None:
        return float("nan")
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "nan", "None"}:
        return float("nan")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    return pd.to_numeric(text, errors="coerce")


def _normalize_account_text(value: object) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", str(value or "")).lower()


def _text(element: ElementTree.Element, tag: str) -> str:
    child = element.find(tag)
    return "" if child is None or child.text is None else child.text.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect DART financial statements into a panel CSV.")
    parser.add_argument("--api-key", default=None, help="OpenDART API key. Defaults to DART_API_KEY env var.")
    parser.add_argument("--start-year", type=int, default=2019)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument("--output", default="data/processed/financials_panel.csv")
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--no-resume", action="store_true", help="Ignore an existing output CSV and start over.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = get_api_key(args.api_key)
    panel = collect_financial_panel(
        api_key=api_key,
        start_year=args.start_year,
        end_year=args.end_year,
        limit=args.limit,
        sleep_seconds=args.sleep,
        output_path=args.output,
        checkpoint_every=args.checkpoint_every,
        resume=not args.no_resume,
    )
    print(f"Saved {len(panel):,} company-year rows to {args.output}")


if __name__ == "__main__":
    main()
