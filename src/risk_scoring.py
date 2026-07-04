from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler, RobustScaler

from src.metrics import FEATURE_COLUMNS


def prepare_model_features(
    df: pd.DataFrame,
    feature_columns: list[str] | None = None,
    lower_quantile: float = 0.01,
    upper_quantile: float = 0.99,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    feature_columns = feature_columns or FEATURE_COLUMNS
    result = df.copy()
    features = result[feature_columns].replace([np.inf, -np.inf], np.nan)
    missing_mask = features.isna()

    result["feature_imputed_count"] = missing_mask.sum(axis=1)
    result["feature_imputed_ratio"] = result["feature_imputed_count"] / len(feature_columns)
    result["imputed_features"] = missing_mask.apply(
        lambda row: ", ".join(row.index[row].tolist()),
        axis=1,
    )

    imputed = features.copy()
    group_keys = [result["year"], result["industry"]]
    for col in feature_columns:
        industry_year_median = imputed[col].groupby(group_keys).transform("median")
        year_median = imputed[col].groupby(result["year"]).transform("median")
        global_median = imputed[col].median()
        if pd.isna(global_median):
            global_median = 0.0

        imputed[col] = (
            imputed[col]
            .fillna(industry_year_median)
            .fillna(year_median)
            .fillna(global_median)
            .fillna(0.0)
        )

    clipped = imputed.copy()
    for col in feature_columns:
        lower = clipped[col].quantile(lower_quantile)
        upper = clipped[col].quantile(upper_quantile)
        if pd.notna(lower) and pd.notna(upper) and lower < upper:
            clipped[col] = clipped[col].clip(lower=lower, upper=upper)

    return result, clipped


def _robust_z(series: pd.Series) -> pd.Series:
    median = series.median()
    mad = (series - median).abs().median()
    if pd.isna(mad) or mad == 0:
        return pd.Series(0.0, index=series.index)
    return 0.6745 * (series - median) / mad


def add_peer_risk(df: pd.DataFrame, peer_features: pd.DataFrame | None = None) -> pd.DataFrame:
    result = df.copy()
    feature_source = peer_features if peer_features is not None else result[FEATURE_COLUMNS]
    z_cols = []
    for col in FEATURE_COLUMNS:
        z_col = f"{col}_peer_z"
        result[z_col] = feature_source[col].groupby([result["year"], result["industry"]]).transform(
            _robust_z
        )
        z_cols.append(z_col)

    result["industry_peer_risk_raw"] = result[z_cols].abs().mean(axis=1)
    result = add_matched_peer_risk(result, feature_source)
    result["peer_risk_raw"] = (
        0.50 * result["industry_peer_risk_raw"]
        + 0.50 * result["matched_peer_risk_raw"]
    )
    result["peer_risk_score"] = _scale_0_100(result["peer_risk_raw"])
    return result


def add_matched_peer_risk(
    df: pd.DataFrame,
    feature_source: pd.DataFrame,
    max_peers: int = 12,
    min_peers: int = 5,
) -> pd.DataFrame:
    result = df.copy()
    matched_raw = pd.Series(0.0, index=result.index)
    matched_sizes = pd.Series(0, index=result.index, dtype=int)

    for idx, row in result.iterrows():
        peers = _matched_peer_indices(result, row, max_peers=max_peers)
        if len(peers) < min_peers:
            peers = result[
                (result["year"] == row["year"])
                & (result["industry"] == row["industry"])
                & (result.index != idx)
            ].index.tolist()
        if not peers:
            matched_raw.loc[idx] = result.loc[idx, "industry_peer_risk_raw"]
            matched_sizes.loc[idx] = 0
            continue

        feature_z_values = []
        for col in FEATURE_COLUMNS:
            peer_values = feature_source.loc[peers, col]
            feature_z_values.append(abs(_robust_z_value(feature_source.loc[idx, col], peer_values)))
        matched_raw.loc[idx] = float(np.mean(feature_z_values))
        matched_sizes.loc[idx] = len(peers)

    result["matched_peer_risk_raw"] = matched_raw
    result["matched_peer_group_size"] = matched_sizes
    return result


def add_ml_risk(
    df: pd.DataFrame,
    random_state: int = 42,
    model_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    result = df.copy()
    features = model_features if model_features is not None else prepare_model_features(result)[1]

    scaled = RobustScaler().fit_transform(features)

    iso = IsolationForest(contamination=0.08, random_state=random_state)
    iso.fit(scaled)
    result["isolation_risk_raw"] = -iso.decision_function(scaled)

    pca_components = min(3, scaled.shape[1])
    pca = PCA(n_components=pca_components, random_state=random_state)
    reconstructed = pca.inverse_transform(pca.fit_transform(scaled))
    result["pca_reconstruction_error"] = np.mean((scaled - reconstructed) ** 2, axis=1)

    result["ml_risk_score"] = _scale_0_100(
        result["isolation_risk_raw"] + result["pca_reconstruction_error"]
    )
    return result


def add_composite_risk(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["accounting_risk_score"] = _scale_0_100(result["m_score"])
    result["final_risk_score"] = (
        0.45 * result["accounting_risk_score"]
        + 0.30 * result["peer_risk_score"]
        + 0.25 * result["ml_risk_score"]
    )
    return result.sort_values("final_risk_score", ascending=False)


def score_financials(df: pd.DataFrame) -> pd.DataFrame:
    result, model_features = prepare_model_features(df)
    result = add_peer_risk(result, model_features)
    result = add_ml_risk(result, model_features=model_features)
    return add_composite_risk(result)


def _scale_0_100(series: pd.Series) -> pd.Series:
    values = series.replace([np.inf, -np.inf], np.nan)
    fill_value = values.median()
    if pd.isna(fill_value):
        fill_value = 0.0
    values = values.fillna(fill_value)
    lower = values.quantile(0.01)
    upper = values.quantile(0.99)
    if pd.notna(lower) and pd.notna(upper) and lower < upper:
        values = values.clip(lower=lower, upper=upper)
    if values.nunique(dropna=True) <= 1:
        return pd.Series(0.0, index=series.index)
    scaler = MinMaxScaler(feature_range=(0, 100))
    return pd.Series(scaler.fit_transform(values.to_frame()).ravel(), index=series.index)


def _matched_peer_indices(df: pd.DataFrame, target: pd.Series, max_peers: int = 12) -> list:
    candidates = df[
        (df["year"] == target["year"])
        & (df["stock_code"].astype(str) != str(target["stock_code"]))
    ].copy()
    if candidates.empty:
        return []

    target_operating_margin = _safe_scalar_divide(target.get("operating_income"), target.get("revenue"))
    candidates["operating_margin"] = _safe_divide(
        pd.to_numeric(candidates.get("operating_income"), errors="coerce"),
        pd.to_numeric(candidates.get("revenue"), errors="coerce"),
    )
    candidates["industry_match"] = (candidates["industry"] == target["industry"]).astype(float)
    candidates["industry_code_match"] = _industry_prefix_match(candidates, target)
    candidates["size_distance"] = _ranked_distance(
        _log_distance(candidates["revenue"], target.get("revenue"))
        + _log_distance(candidates["total_assets"], target.get("total_assets"))
    )
    candidates["profit_distance"] = _ranked_distance(
        (candidates.get("gross_margin", 0) - target.get("gross_margin", 0)).abs()
        + (candidates["operating_margin"] - target_operating_margin).abs()
    )
    candidates["growth_distance"] = _ranked_distance(
        (candidates.get("sgi", 1.0) - target.get("sgi", 1.0)).abs()
    )
    candidates["peer_distance"] = (
        0.36 * (1 - candidates["industry_match"])
        + 0.14 * (1 - candidates["industry_code_match"])
        + 0.28 * candidates["size_distance"]
        + 0.14 * candidates["profit_distance"]
        + 0.08 * candidates["growth_distance"]
    )
    return candidates.sort_values("peer_distance").head(max_peers).index.tolist()


def _robust_z_value(value: float, peer_values: pd.Series) -> float:
    values = pd.to_numeric(peer_values, errors="coerce").dropna()
    if values.empty:
        return 0.0
    median = values.median()
    mad = (values - median).abs().median()
    if pd.isna(mad) or mad == 0:
        return 0.0
    return float(0.6745 * (value - median) / mad)


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
