import unittest
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from src.event_labels import attach_event_labels, load_event_labels
from src.dart_pipeline import _extract_amount_with_match
from src.metrics import add_beneish_style_features
from src.risk_scoring import prepare_model_features, score_financials
from src.regulatory_focus import load_regulatory_focus_issues, match_regulatory_focus_issues
from src.sample_data import generate_sample_financials


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
