"""
Two-stage credit scoring engine:
1) hard rules
2) XGBoost model (classifier + regressor) with explainable outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier, XGBRegressor

from backend.config import settings
from backend.core.ml.feature_engineering import CREDIT_FEATURES
from backend.core.ml.risk_rules import evaluate_hard_rules
from backend.schemas.credit import CreditDecision

logger = logging.getLogger(__name__)


def compute_interest_premium_bps(grade: str) -> int:
    """
    Maps credit grade to risk premium in basis points above benchmark.
    Benchmark = RBI repo rate or MCLR as applicable.
    """
    premium_map = {
        "AAA": 50,
        "AA+": 60,
        "AA": 100,
        "AA-": 100,
        "A+": 125,
        "A": 150,
        "A-": 175,
        "BBB+": 200,
        "BBB": 225,
        "BBB-": 250,
        "BB+": 275,
        "BB": 300,
        "BB-": 325,
        "B+": 350,
        "B": 400,
        "B-": 450,
        "C": 600,
        "D": 0,  # reject, no lending
    }
    return int(premium_map.get(grade, 300))


def format_interest_rate(grade: str, base_rate_pct: float = 8.5) -> dict:
    bps = compute_interest_premium_bps(grade)
    total_rate = base_rate_pct + (bps / 100)
    return {
        "premium_bps": bps,
        "display": f"Benchmark + {bps} bps",
        "effective_rate": f"{total_rate:.2f}%",
    }


def compute_recommended_limit(
    requested_amount_cr: float,
    extracted_revenue_cr: float,
    grade: str,
) -> float:
    """
    Compute approved limit in Cr based on request, annual revenue cap, and risk grade.
    """
    max_allowable = max(extracted_revenue_cr, 0.0) * 0.25
    logger.info(
        "LIMIT DEBUG: %s",
        {
            "form_turnover": None,
            "extracted_revenue": float(extracted_revenue_cr or 0.0),
            "requested_amount": float(requested_amount_cr or 0.0),
            "using_value": "compute_recommended_limit",
        },
    )
    grade_multiplier = {
        "AAA": 1.0,
        "AA+": 1.0,
        "AA": 1.0,
        "AA-": 1.0,
        "A+": 0.95,
        "A": 0.90,
        "BBB+": 0.80,
        "BBB": 0.75,
        "BB+": 0.65,
        "BB": 0.60,
        "B": 0.45,
        "D": 0.0,
    }
    multiplier = grade_multiplier.get(grade, 0.70)
    base_approved = min(max(requested_amount_cr, 0.0), max_allowable)
    approved = base_approved * multiplier
    return round(approved, 2)


@dataclass
class ModelArtifacts:
    classifier: XGBClassifier
    regressor: XGBRegressor


class CreditScoringModel:
    """
    Production-style scoring facade with train/save/load/predict methods.
    """

    def __init__(self, model_dir: str = "ml/model") -> None:
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.classifier_path = self.model_dir / "xgb_credit_classifier.joblib"
        self.regressor_path = self.model_dir / "xgb_credit_regressor.joblib"
        self.feature_order = list(CREDIT_FEATURES.keys())

    def train_on_synthetic_data(self, n_samples: int = 600) -> ModelArtifacts:
        df = self._generate_synthetic_profiles(n_samples=n_samples)
        X = df[self.feature_order]
        y_stress = df["stress_label"]
        y_score = df["credit_score"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y_stress, test_size=0.2, random_state=42, stratify=y_stress
        )

        classifier = XGBClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="binary:logistic",
            random_state=42,
        )
        classifier.fit(X_train, y_train)

        regressor = XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
        regressor.fit(X, y_score)

        joblib.dump(classifier, self.classifier_path)
        joblib.dump(regressor, self.regressor_path)
        return ModelArtifacts(classifier=classifier, regressor=regressor)

    def predict(
        self,
        features: Dict[str, float],
        *,
        requested_loan_amount: float,
        annual_revenue_cr: float = 0.0,
        revenue_cr: float = 0.0,
        gross_receipts_cr: float = 0.0,
        form_turnover_cr: float = 0.0,
        revenue_source: str = "extracted_data.annual_revenue_cr",
        sector: str,
        loan_type: str = "secured",
    ) -> CreditDecision:
        score_features = self._doc_only_score_features(features)
        rule_hits = evaluate_hard_rules(score_features)
        scoring_warnings: List[str] = []
        revenue_candidates = [
            ("extracted_data.revenue_cr", float(revenue_cr or 0.0)),
            ("extracted_data.annual_revenue_cr", float(annual_revenue_cr or 0.0)),
            ("extracted_data.gross_receipts_cr", float(gross_receipts_cr or 0.0)),
        ]
        extracted_revenue = 0.0
        using_value = "company.turnover"
        for source_name, candidate in revenue_candidates:
            if candidate > 0:
                extracted_revenue = candidate
                using_value = source_name
                break
        logger.info(
            "SCORING INPUT DEBUG: %s",
            {
                "form_turnover_cr": float(form_turnover_cr or 0.0),
                "extracted_revenue_cr": float(extracted_revenue) if extracted_revenue > 0 else None,
                "which_is_used": using_value if extracted_revenue > 0 else "company.turnover",
            },
        )
        score_cap = 100.0
        if extracted_revenue <= 0:
            warning = (
                "WARNING: Using form turnover as revenue fallback. "
                "Document extraction may have failed. Score may be inaccurate."
            )
            logger.warning(warning)
            scoring_warnings.append(warning)
            extracted_revenue = float(form_turnover_cr or 0.0)
            score_cap = 70.0
            using_value = "company.turnover"
        logger.info(
            "LIMIT DEBUG: %s",
            {
                "form_turnover": float(form_turnover_cr or 0.0),
                "extracted_revenue": float(extracted_revenue or 0.0),
                "requested_amount": float(requested_loan_amount or 0.0),
                "using_value": using_value,
            },
        )
        if rule_hits:
            # On hard REJECT: compute limit and rate for informational display,
            # but mark as REJECT with clear "Not Sanctioned" semantics.
            risk_grade = "D"
            pricing = float(
                format_interest_rate(risk_grade, settings.base_interest_rate)["effective_rate"].rstrip("%")
            )
            return CreditDecision(
                credit_score=450.0,
                normalized_score=round((450.0 / 900.0) * 100.0, 1),
                score_band="300-599",
                risk_grade=risk_grade,
                recommendation="REJECT",
                recommended_loan_amount=compute_recommended_limit(
                    requested_loan_amount,
                    extracted_revenue,
                    risk_grade,
                ),
                recommended_interest_rate=pricing,  # Informational rate, always positive
                interest_premium_bps=compute_interest_premium_bps(risk_grade),
                confidence_interval=[420.0, 480.0],
                human_input_impact_points=0.0,
                rule_hits=rule_hits,
                scoring_warnings=scoring_warnings,
            )

        artifacts = self._load_or_train()
        X = pd.DataFrame([score_features], columns=self.feature_order)
        stress_prob = float(artifacts.classifier.predict_proba(X)[0][1])
        model_score = float(artifacts.regressor.predict(X)[0])
        human_input_impact = float(score_features.get("due_diligence_risk_adjustment", 0.0)) * 3.0

        # Blend model score with stress probability to reduce overconfidence.
        adjusted_score = model_score - (stress_prob * 220.0) + human_input_impact
        credit_score = float(np.clip(adjusted_score, 0, 900))
        normalized_score = round((credit_score / 900.0) * 100.0, 1)
        if normalized_score > score_cap:
            logger.warning(
                "scoring.score_capped_due_to_revenue_fallback: cap=%s original_normalized_score=%s",
                score_cap,
                normalized_score,
            )
            normalized_score = round(score_cap, 1)
            credit_score = min(credit_score, score_cap * 9.0)
        risk_grade = self._grade_from_normalized(normalized_score)
        recommendation = "REJECT" if normalized_score < 50 else "APPROVE"
        if 60 <= normalized_score < 70:
            recommendation = "CONDITIONAL_APPROVE"
        if recommendation == "REJECT":
            risk_grade = "D"

        premium_bps = compute_interest_premium_bps(risk_grade)
        pricing = float(format_interest_rate(risk_grade, settings.base_interest_rate)["effective_rate"].rstrip("%"))
        # Compute limit after grade is determined.
        recommended_amount = compute_recommended_limit(
            requested_loan_amount,
            extracted_revenue,
            risk_grade,
        )

        ci_half_width = max(12.0, (1 - self._data_completeness(features)) * 70)
        return CreditDecision(
            credit_score=round(credit_score, 2),
            normalized_score=normalized_score,
            score_band=f"{int(max(0, normalized_score - 5))}-{int(min(100, normalized_score + 5))}",
            risk_grade=risk_grade,
            recommendation=recommendation,
            recommended_loan_amount=recommended_amount,
            recommended_interest_rate=pricing,
            interest_premium_bps=premium_bps,
            confidence_interval=[
                round(max(0, credit_score - ci_half_width), 2),
                round(min(900, credit_score + ci_half_width), 2),
            ],
            human_input_impact_points=round(human_input_impact, 2),
            rule_hits=rule_hits,
            scoring_warnings=scoring_warnings,
        )

    @staticmethod
    def _doc_only_score_features(features: Dict[str, float]) -> Dict[str, float]:
        """
        Keep credit score document-driven.
        Research/news signals are advisory and must not directly drive score/reject.
        """
        score_features = dict(features)
        for key in (
            "has_promoter_fraud_news",
            "has_nclt_proceedings",
            "has_litigation",
            "has_sector_headwinds",
            "has_mca_struck_off_associates",
        ):
            score_features[key] = 0.0
        return score_features

    def _load_or_train(self) -> ModelArtifacts:
        if self.classifier_path.exists() and self.regressor_path.exists():
            return ModelArtifacts(
                classifier=joblib.load(self.classifier_path),
                regressor=joblib.load(self.regressor_path),
            )
        return self.train_on_synthetic_data()

    def _generate_synthetic_profiles(self, n_samples: int) -> pd.DataFrame:
        rng = np.random.default_rng(42)
        data: Dict[str, np.ndarray] = {}

        for feature in self.feature_order:
            if feature.startswith("has_"):
                data[feature] = rng.integers(0, 2, size=n_samples)
            elif "score" in feature:
                data[feature] = rng.normal(70, 15, size=n_samples)
            elif "ratio" in feature:
                data[feature] = rng.normal(1.2, 0.6, size=n_samples)
            elif "gap" in feature:
                data[feature] = np.abs(rng.normal(6, 9, size=n_samples))
            elif "utilization" in feature:
                data[feature] = np.clip(rng.normal(65, 18, size=n_samples), 5, 100)
            elif feature == "cibil_commercial_score":
                data[feature] = np.clip(rng.normal(700, 80, size=n_samples), 500, 850)
            else:
                data[feature] = rng.normal(1.0, 0.5, size=n_samples)

        df = pd.DataFrame(data)

        stress_signal = (
            0.8 * (df["has_going_concern_doubt"] + df["has_nclt_proceedings"])
            + 0.5 * df["has_promoter_fraud_news"]
            + 0.4 * (df["gstr3b_vs_2a_itc_gap"] > 15).astype(float)
            + 0.3 * (df["dscr"] < 1.1).astype(float)
            + 0.25 * (df["debt_equity_ratio"] > 2.5).astype(float)
            + rng.normal(0, 0.25, size=n_samples)
        )
        df["stress_label"] = (stress_signal > 0.9).astype(int)

        raw_score = (
            780
            + (df["dscr"] * 40)
            + (df["interest_coverage_ratio"] * 25)
            + (df["management_integrity_score"] * 8)
            - (df["gstr3b_vs_2a_itc_gap"] * 3)
            - (df["has_litigation"] * 35)
            - (df["has_promoter_fraud_news"] * 60)
            - (df["due_diligence_risk_adjustment"] * -1.5)
            + rng.normal(0, 22, size=n_samples)
        )
        df["credit_score"] = np.clip(raw_score, 300, 900)
        return df

    @staticmethod
    def _grade_from_normalized(score: float) -> str:
        s = max(0.0, min(100.0, score))
        if s >= 90:
            return "AAA"
        if s >= 80:
            return "AA"
        if s >= 75:
            return "AA-"
        if s >= 70:
            return "A+"
        if s >= 65:
            return "A"
        if s >= 60:
            return "A-"
        if s >= 55:
            return "BBB+"
        if s >= 50:
            return "BBB"
        if s >= 45:
            return "BB+"
        if s >= 40:
            return "BB"
        return "B"

    @staticmethod
    def _data_completeness(features: Dict[str, float]) -> float:
        vals = list(features.values())
        if not vals:
            return 0.0
        non_zero = sum(1 for v in vals if v not in (0, 0.0))
        return non_zero / len(vals)
