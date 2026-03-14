"""
Bank statement analyzer for fraud and cashflow signal extraction.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd

from backend.schemas.credit import BankStatementMetrics, EMIPayment, Transaction


class BankStatementAnalyzer:
    """
    Analyze CSV/Excel bank statements and extract credit-relevant metrics.
    """

    def analyze(
        self,
        file_path: str,
        *,
        annual_revenue: float = 1.0,
        gst_turnover: float = 1.0,
    ) -> BankStatementMetrics:
        df = self._load_dataframe(file_path)
        if df.empty:
            return BankStatementMetrics(
                average_monthly_balance=0.0,
                abb_to_claimed_revenue_ratio=0.0,
                max_debit_single_transaction=0.0,
                circular_credit_debit_pairs=[],
                emi_payments=[],
                suspected_shell_company_transfers=[],
                cash_withdrawal_pattern="NORMAL",
                year_end_window_dressing=False,
                banking_turnover=0.0,
                banking_to_gst_ratio=0.0,
            )

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")

        credits = df["credit"].fillna(0.0).astype(float)
        debits = df["debit"].fillna(0.0).astype(float)
        balances = df["balance"].ffill().fillna(0.0).astype(float)

        monthly_balance = df.assign(month=df["date"].dt.to_period("M")).groupby("month")[
            "balance"
        ].mean()
        average_monthly_balance = float(monthly_balance.mean()) if not monthly_balance.empty else 0.0  # type: ignore[reportArgumentType, reportAttributeAccessIssue]

        banking_turnover = float(credits.sum())  # type: ignore[reportArgumentType]
        abb_ratio = average_monthly_balance / max(annual_revenue, 1.0)
        banking_to_gst_ratio = banking_turnover / max(gst_turnover, 1.0)

        circular_pairs = self._detect_circular_pairs(df)
        emi = self._detect_emi(df)
        shell_transfers = self._detect_shell_transfers(df)
        cash_pattern = self._cash_pattern(df)
        window_dressing = self._detect_window_dressing(df)

        return BankStatementMetrics(
            average_monthly_balance=round(average_monthly_balance, 2),
            abb_to_claimed_revenue_ratio=round(abb_ratio, 4),
            max_debit_single_transaction=round(float(debits.max()), 2),  # type: ignore[reportArgumentType]
            circular_credit_debit_pairs=circular_pairs,
            emi_payments=emi,
            suspected_shell_company_transfers=shell_transfers,
            cash_withdrawal_pattern=cash_pattern,
            year_end_window_dressing=window_dressing,
            banking_turnover=round(banking_turnover, 2),
            banking_to_gst_ratio=round(banking_to_gst_ratio, 4),
        )

    @staticmethod
    def _load_dataframe(file_path: str) -> pd.DataFrame:
        suffix = Path(file_path).suffix.lower()
        if suffix in {".xlsx", ".xls"}:
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        normalized_cols = {c.lower().strip(): c for c in df.columns}
        req = ["date", "debit", "credit", "balance", "narration", "party"]
        for col in req:
            if col not in normalized_cols:
                df[col] = None
            else:
                df[col] = df[normalized_cols[col]]

        return df[req].copy()  # type: ignore[reportReturnType]

    @staticmethod
    def _detect_circular_pairs(df: pd.DataFrame) -> List[Transaction]:
        txns: List[Transaction] = []
        credits = df[df["credit"].fillna(0) > 0]
        debits = df[df["debit"].fillna(0) > 0]

        for _, debit_row in debits.iterrows():
            d_date = debit_row["date"]
            d_amount = float(debit_row["debit"] or 0.0)  # type: ignore[reportArgumentType]
            d_party = str(debit_row.get("party") or "").strip().lower()
            if d_amount <= 0:
                continue

            candidate = credits[
                (credits["date"] >= d_date)
                & (credits["date"] <= d_date + timedelta(days=3))
            ]
            for _, credit_row in candidate.iterrows():  # type: ignore[reportAttributeAccessIssue]
                c_amount = float(credit_row["credit"] or 0.0)  # type: ignore[reportArgumentType]
                lower = d_amount * 0.98
                upper = d_amount * 1.02
                c_party = str(credit_row.get("party") or "").strip().lower()
                if lower <= c_amount <= upper and d_party and c_party == d_party:
                    txns.append(
                        Transaction(
                            date=credit_row["date"].date(),  # type: ignore[reportAttributeAccessIssue]
                            party=str(credit_row.get("party") or "Unknown"),
                            amount=round(c_amount, 2),
                            txn_type="CIRCULAR_PAIR",
                            narration=str(credit_row.get("narration") or "")[:160],
                        )
                    )
                    break
        return txns[:50]

    @staticmethod
    def _detect_emi(df: pd.DataFrame) -> List[EMIPayment]:
        emi: List[EMIPayment] = []
        mask = df["narration"].fillna("").str.contains(r"emi|ecs|nach|loan", case=False, regex=True)
        for _, row in df[mask & (df["debit"].fillna(0) > 0)].iterrows():
            emi.append(
                EMIPayment(
                    date=row["date"].date(),  # type: ignore[reportAttributeAccessIssue]
                    lender=str(row.get("party") or "") or None,
                    amount=round(float(row["debit"]), 2),  # type: ignore[reportArgumentType]
                    confidence_score=0.75,
                )
            )
        return emi[:100]

    @staticmethod
    def _detect_shell_transfers(df: pd.DataFrame) -> List[str]:
        findings: List[str] = []
        suspicious = df[
            (df["debit"].fillna(0) > 0)
            & (df["debit"].fillna(0) % 100000 == 0)
            & (~df["party"].fillna("").str.contains("bank|gst|salary|tax", case=False))
        ]
        for _, row in suspicious.iterrows():
            findings.append(
                f"{row['date'].date()}: round transfer ₹{float(row['debit']):,.0f} to {row.get('party') or 'Unknown'}"  # type: ignore[reportArgumentType, reportAttributeAccessIssue]
            )
        return findings[:20]

    @staticmethod
    def _cash_pattern(df: pd.DataFrame) -> str:
        cash_debits = df[
            df["narration"].fillna("").str.contains(r"cash|atm", case=False, regex=True)
            & (df["debit"].fillna(0) > 0)
        ]["debit"].sum()
        total_debits = df["debit"].fillna(0).sum()
        if total_debits <= 0:
            return "NORMAL"
        ratio = cash_debits / total_debits
        if ratio > 0.35:
            return "ALARMING"
        if ratio > 0.2:
            return "SUSPICIOUS"
        return "NORMAL"

    @staticmethod
    def _detect_window_dressing(df: pd.DataFrame) -> bool:
        march_data = df[df["date"].dt.month == 3]
        if march_data.empty:
            return False

        first_half = march_data[march_data["date"].dt.day <= 15]["credit"].fillna(0).sum()  # type: ignore[reportAttributeAccessIssue]
        second_half = march_data[march_data["date"].dt.day > 15]["credit"].fillna(0).sum()  # type: ignore[reportAttributeAccessIssue]
        if first_half <= 0:
            return second_half > 0
        return second_half > 3 * first_half
