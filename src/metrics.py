from __future__ import annotations

import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "dsri",
    "gmi",
    "aqi",
    "sgi",
    "sgai",
    "lvgi",
    "tata",
]


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    return numerator / denominator


def _safe_index(current: pd.Series, prior: pd.Series) -> pd.Series:
    result = _safe_divide(current, prior)
    both_zero = current.fillna(0).abs().le(1e-12) & prior.fillna(0).abs().le(1e-12)
    return result.mask(both_zero, 1.0)


def add_beneish_style_features(financials: pd.DataFrame) -> pd.DataFrame:
    df = financials.sort_values(["stock_code", "year"]).copy()
    grouped = df.groupby("stock_code", group_keys=False)
    profit_for_margin, margin_proxy_used = _profit_for_margin(df)

    df["receivables_to_sales"] = _safe_divide(df["receivables"], df["revenue"])
    df["gross_margin_proxy_used"] = margin_proxy_used
    df["gross_margin"] = _safe_divide(profit_for_margin, df["revenue"])
    df["asset_quality"] = 1 - _safe_divide(df["current_assets"] + df["ppe"], df["total_assets"])
    df["sga_proxy"] = _safe_divide(profit_for_margin - df["operating_income"], df["revenue"])
    df["leverage"] = _safe_divide(df["total_liabilities"], df["total_assets"])
    df["tata"] = _safe_divide(df["net_income"] - df["operating_cash_flow"], df["total_assets"])

    df["dsri"] = _safe_index(df["receivables_to_sales"], grouped["receivables_to_sales"].shift(1))
    df["gmi"] = _safe_index(grouped["gross_margin"].shift(1), df["gross_margin"])
    df["aqi"] = _safe_index(df["asset_quality"], grouped["asset_quality"].shift(1))
    df["sgi"] = _safe_index(df["revenue"], grouped["revenue"].shift(1))
    df["sgai"] = _safe_index(df["sga_proxy"], grouped["sga_proxy"].shift(1))
    df["lvgi"] = _safe_index(df["leverage"], grouped["leverage"].shift(1))

    df["m_score"] = (
        -4.84
        + 0.920 * df["dsri"]
        + 0.528 * df["gmi"]
        + 0.404 * df["aqi"]
        + 0.892 * df["sgi"]
        + 0.115 * df["sgai"]
        - 0.172 * df["lvgi"]
        + 4.679 * df["tata"]
    )

    return df.replace([np.inf, -np.inf], np.nan)


def _profit_for_margin(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    gross_profit = pd.to_numeric(df["gross_profit"], errors="coerce")
    operating_income = pd.to_numeric(df["operating_income"], errors="coerce")
    revenue = pd.to_numeric(df["revenue"], errors="coerce")

    proxy_used = df.get("gross_profit_proxy_used", False)
    if not isinstance(proxy_used, pd.Series):
        proxy_used = pd.Series(bool(proxy_used), index=df.index)
    proxy_used = proxy_used.fillna(False).astype(bool)

    revenue_like_gross_profit = (
        gross_profit.notna()
        & revenue.notna()
        & revenue.ne(0)
        & gross_profit.div(revenue).abs().ge(0.98)
        & operating_income.notna()
        & operating_income.abs().lt(gross_profit.abs() * 0.8)
    )
    use_operating_income_proxy = proxy_used | revenue_like_gross_profit
    return gross_profit.mask(use_operating_income_proxy, operating_income), use_operating_income_proxy
