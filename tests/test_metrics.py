import unittest
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from src.event_labels import attach_event_labels, load_event_labels
from src.dart_pipeline import _extract_amount_with_match
from src.data_loader import generate_sample_financials
from src.metrics import add_beneish_style_features
from src.risk_scoring import PEER_Z_SCORE_CAP, prepare_model_features, score_financials
from src.regulatory_focus import load_regulatory_focus_issues, match_regulatory_focus_issues
from scripts.audit_mapping_quality import audit_mapping_quality


class MetricsTest(unittest.TestCase):
    def test_beneish_style_features_are_created(self):
        with TemporaryDirectory() as temp_dir:
            df = generate_sample_financials(f"{temp_dir}/sample.csv")
        result = add_beneish_style_features(df)

        self.assertIn("m_score", result.columns)
        self.assertGreater(result["m_score"].notna().sum(), 0)

    def test_risk_scoring_tracks_imputation_and_scales_scores(self):
        with TemporaryDirectory() as temp_dir:
            df = generate_sample_financials(f"{temp_dir}/sample.csv")
        features = add_beneish_style_features(df).dropna(subset=["m_score"]).copy()
        features.loc[features.index[:2], "dsri"] = np.nan
        features.loc[features.index[2], "gmi"] = np.inf

        scored = score_financials(features)

        self.assertIn("feature_imputed_count", scored.columns)
        self.assertIn("imputed_features", scored.columns)
        self.assertGreaterEqual(scored["feature_imputed_count"].max(), 1)
        self.assertTrue(scored["final_risk_score"].between(0, 100).all())
        self.assertTrue(scored["ml_risk_score"].between(0, 100).all())

    def test_model_feature_preparation_uses_fallbacks(self):
        with TemporaryDirectory() as temp_dir:
            df = generate_sample_financials(f"{temp_dir}/sample.csv")
        features = add_beneish_style_features(df).dropna(subset=["m_score"]).copy()
        features["aqi"] = np.nan

        result, model_features = prepare_model_features(features)

        self.assertTrue(model_features.notna().all().all())
        self.assertEqual(result["feature_imputed_count"].max(), 1)

    def test_event_labels_attach_to_company_years(self):
        scored = pd.DataFrame(
            {
                "stock_code": ["000001", "000002"],
                "company_name": ["A", "B"],
                "year": [2024, 2024],
                "final_risk_score": [90.0, 10.0],
            }
        )
        labels = pd.DataFrame(
            {
                "stock_code": ["1"],
                "company_name": ["A"],
                "year": [2024],
                "event_type": ["restatement"],
                "event_date": ["2025-03-01"],
                "source": ["DART"],
                "source_url": ["https://example.com"],
                "notes": ["manual test label"],
            }
        )

        attached = attach_event_labels(scored, labels)

        self.assertTrue(attached.loc[attached["stock_code"] == "000001", "event_flag"].item())
        self.assertFalse(attached.loc[attached["stock_code"] == "000002", "event_flag"].item())
        self.assertEqual(
            attached.loc[attached["stock_code"] == "000001", "event_types"].item(),
            "restatement",
        )

    def test_empty_event_label_file_loads(self):
        with TemporaryDirectory() as temp_dir:
            label_path = f"{temp_dir}/labels.csv"
            with open(label_path, "w", encoding="utf-8") as file:
                file.write("stock_code,company_name,year,event_type,event_date,source,source_url,notes\n")

            labels = load_event_labels(label_path)

        self.assertTrue(labels.empty)
        self.assertIn("event_type", labels.columns)

    def test_dart_account_auto_matching_scores_synonyms(self):
        fs = pd.DataFrame(
            {
                "account_id": ["custom_Revenue", "custom_FinanceIncome"],
                "account_nm": ["영업수익", "금융수익"],
                "sj_div": ["IS", "IS"],
                "fs_div": ["CFS", "CFS"],
                "thstrm_amount": ["1,000", "9,999"],
            }
        )
        amount, match = _extract_amount_with_match(
            fs,
            {
                "ids": ["ifrs-full_Revenue"],
                "keywords": ["매출액", "수익", "영업수익"],
                "exclude_keywords": ["금융수익"],
                "preferred_statement": ["IS"],
            },
        )

        self.assertEqual(amount, 1000.0)
        self.assertEqual(match["account_name"], "영업수익")

    def test_mapping_quality_flags_revenue_mapped_as_gross_profit(self):
        panel = pd.DataFrame(
            {
                "year": [2022, 2023],
                "stock_code": ["035720", "035720"],
                "company_name": ["카카오", "카카오"],
                "industry": ["Information/Communication", "Information/Communication"],
                "industry_code": ["J", "J"],
                "revenue": [6_799_048_000_000, 7_557_002_000_000],
                "receivables": [100, 110],
                "gross_profit": [6_799_048_000_000, 460_857_800_000],
                "operating_income": [569_355_700_000, 460_857_800_000],
                "total_assets": [10_000, 11_000],
                "current_assets": [4_000, 4_200],
                "ppe": [1_000, 1_100],
                "total_liabilities": [3_000, 3_200],
                "net_income": [300, 320],
                "operating_cash_flow": [280, 290],
                "matched_accounts": [
                    "revenue:영업수익; gross_profit:영업수익; operating_income:영업이익(손실)",
                    "revenue:영업수익; gross_profit:영업이익(손실); operating_income:영업이익(손실)",
                ],
                "missing_optional_accounts": ["", ""],
                "gross_profit_proxy_used": [False, False],
            }
        )

        issues = audit_mapping_quality(panel)

        self.assertIn("gross_profit_mapped_to_revenue", set(issues["issue_type"]))
        self.assertIn("gross_profit_uses_operating_income_proxy", set(issues["issue_type"]))

    def test_peer_signals_are_capped_to_avoid_overwarning(self):
        rows = []
        for idx in range(10):
            rows.append(
                {
                    "stock_code": f"000{idx:03d}",
                    "company_name": f"Peer {idx}",
                    "year": 2024,
                    "industry": "Software",
                    "revenue": 1000 + idx,
                    "gross_profit": 500,
                    "operating_income": 100,
                    "total_assets": 2000,
                    "dsri": 1.0,
                    "gmi": 1.0 + idx * 0.001,
                    "aqi": 1.0,
                    "sgi": 1.0,
                    "sgai": 1.0,
                    "lvgi": 1.0,
                    "tata": 0.0,
                    "m_score": -2.5,
                }
            )
        rows.append(
            {
                "stock_code": "999999",
                "company_name": "Target",
                "year": 2024,
                "industry": "Software",
                "revenue": 1000,
                "gross_profit": 350,
                "operating_income": 80,
                "total_assets": 2000,
                "dsri": 1.0,
                "gmi": 1.35,
                "aqi": 1.0,
                "sgi": 1.0,
                "sgai": 1.0,
                "lvgi": 1.0,
                "tata": 0.0,
                "m_score": -2.0,
            }
        )

        scored = score_financials(pd.DataFrame(rows))

        self.assertLessEqual(scored["gmi_peer_z"].abs().max(), PEER_Z_SCORE_CAP)

    def test_regulatory_focus_issues_match_company_signals(self):
        issues = load_regulatory_focus_issues()
        row = pd.Series(
            {
                "dsri": 1.00,
                "sgi": 1.05,
                "gmi": 1.32,
                "aqi": 1.28,
                "lvgi": 0.95,
                "tata": 0.09,
            }
        )

        matches = match_regulatory_focus_issues(row, issues)

        self.assertFalse(matches.empty)
        self.assertIn("손상", matches.iloc[0]["issue_name"])
        self.assertEqual(matches.iloc[0]["source_agency"], "금융감독원")
        self.assertIn("2025년 재무제표", matches.iloc[0]["source_title"])
        self.assertIn("K-IFRS", matches.iloc[0]["basis_standards"])
        self.assertGreaterEqual(matches.iloc[0]["match_strength"], 50)


if __name__ == "__main__":
    unittest.main()
