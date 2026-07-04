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

    df["receivables_to_sales"] = _safe_divide(df["receivables"], df["revenue"])
    df["gross_margin"] = _safe_divide(df["gross_profit"], df["revenue"])
    df["asset_quality"] = 1 - _safe_divide(df["current_assets"] + df["ppe"], df["total_assets"])
    df["sga_proxy"] = _safe_divide(df["gross_profit"] - df["operating_income"], df["revenue"])
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
