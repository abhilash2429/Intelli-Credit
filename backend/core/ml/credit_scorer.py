"""
Two-stage credit scoring engine:
1) hard rules
2) XGBoost model (classifier + regressor) with explainable outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
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


GRADE_BANDS = [
    ("AAA", 850, 900),
    ("AA", 800, 849),
    ("A", 750, 799),
    ("BBB", 700, 749),
    ("BB", 650, 699),
    ("B", 600, 649),
    ("D", 300, 599),
]


def calculate_risk_premium(credit_score: float, sector: str, loan_type: str) -> float:
    """
    Interest pricing engine: base + score band premium + sector premium.
    Always returns a non-negative rate. For REJECT cases, returns the
    hypothetical rate (for informational purposes) rather than -1.
    """
    base_rate = settings.base_interest_rate

    # Premium in basis points based on score band
    if 850 <= credit_score <= 900:
        premium_bps = 25     # AA grade
    elif 750 <= credit_score < 850:
        premium_bps = 60     # A- grade
    elif 700 <= credit_score < 750:
        premium_bps = 120    # B grade
    elif 650 <= credit_score < 700:
        premium_bps = 200    # C grade
    elif 600 <= credit_score < 650:
        premium_bps = 300    # D grade (borderline)
    elif 450 <= credit_score < 600:
        premium_bps = 300    # D grade
    else:
        premium_bps = 300    # Below D — REJECT territory

    sector_map = {
        "nbfc": 50,
        "real_estate": 100,
        "manufacturing": 0,
        "it": 0,
        "energy": 25,
        "mining": 50,
    }
    premium_bps += sector_map.get(sector.lower(), 0)
    if loan_type.lower() == "unsecured":
        premium_bps += 50

    # Never allow negative premium
    premium_bps = max(premium_bps, 0)
    final_rate = round(base_rate + premium_bps / 100.0, 2)
    return final_rate


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
        sector: str,
        loan_type: str = "secured",
    ) -> CreditDecision:
        rule_hits = evaluate_hard_rules(features)
        if rule_hits:
            # On hard REJECT: compute limit and rate for informational display,
            # but mark as REJECT with clear "Not Sanctioned" semantics.
            pricing = calculate_risk_premium(450.0, sector, loan_type)
            return CreditDecision(
                credit_score=450.0,
                score_band="300-599",
                risk_grade="D",
                recommendation="REJECT",
                recommended_loan_amount=requested_loan_amount,  # Show requested amount (for "Not Sanctioned (Requested: ₹X Cr)")
                recommended_interest_rate=pricing,  # Informational rate, always positive
                confidence_interval=[420.0, 480.0],
                human_input_impact_points=0.0,
                rule_hits=rule_hits,
            )

        artifacts = self._load_or_train()
        X = pd.DataFrame([features], columns=self.feature_order)
        stress_prob = float(artifacts.classifier.predict_proba(X)[0][1])
        model_score = float(artifacts.regressor.predict(X)[0])
        human_input_impact = float(features.get("due_diligence_risk_adjustment", 0.0)) * 3.0

        # Blend model score with stress probability to reduce overconfidence.
        adjusted_score = model_score - (stress_prob * 220.0) + human_input_impact
        credit_score = float(np.clip(adjusted_score, 300, 900))
        risk_grade = self._grade_from_score(credit_score)
        recommendation = "REJECT" if credit_score < 600 else "APPROVE"
        if 620 <= credit_score < 720:
            recommendation = "CONDITIONAL_APPROVE"

        pricing = calculate_risk_premium(credit_score, sector, loan_type)

        if recommendation == "REJECT":
            # On REJECT, show requested amount for display purposes
            recommended_amount = requested_loan_amount
        elif recommendation == "CONDITIONAL_APPROVE":
            # Reduced limit for conditional approval
            collateral_cov = features.get("collateral_coverage_ratio", 1.0)
            reduced = requested_loan_amount * (credit_score / 900) * min(collateral_cov, 1.5)
            recommended_amount = round(
                max(0.25 * requested_loan_amount, min(reduced, requested_loan_amount)), 2
            )
        else:
            # Full APPROVE: risk-adjusted exposure
            exposure_factor = float(np.clip((credit_score - 500) / 350, 0.0, 1.1))
            recommended_amount = round(requested_loan_amount * exposure_factor, 2)

        ci_half_width = max(12.0, (1 - self._data_completeness(features)) * 70)
        return CreditDecision(
            credit_score=round(credit_score, 2),
            score_band=f"{int(max(300, credit_score - 25))}-{int(min(900, credit_score + 25))}",
            risk_grade=risk_grade,
            recommendation=recommendation,
            recommended_loan_amount=recommended_amount,
            recommended_interest_rate=pricing,
            confidence_interval=[
                round(max(300, credit_score - ci_half_width), 2),
                round(min(900, credit_score + ci_half_width), 2),
            ],
            human_input_impact_points=round(human_input_impact, 2),
            rule_hits=rule_hits,
        )

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
    def _grade_from_score(score: float) -> str:
        for grade, low, high in GRADE_BANDS:
            if low <= score <= high:
                return grade
        return "D"

    @staticmethod
    def _data_completeness(features: Dict[str, float]) -> float:
        vals = list(features.values())
        if not vals:
            return 0.0
        non_zero = sum(1 for v in vals if v not in (0, 0.0))
        return non_zero / len(vals)
