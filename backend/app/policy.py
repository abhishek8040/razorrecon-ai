from decimal import Decimal
from typing import List, Tuple
from app.models import Payment, Settlement, BankTransaction

class PolicyEngine:
    MIN_AUTO_RESOLUTION_CONFIDENCE = 0.90
    MAX_AMOUNT_TOLERANCE_PERCENT = 2.0
    MAX_TIME_WINDOW_DAYS = 5
    MAX_COMPETING_CANDIDATES = 3

    @classmethod
    def evaluate_match(cls, payment: Payment, settlement: Settlement = None, bank_tx: BankTransaction = None) -> Tuple[List[str], List[str], List[str], str]:
        """
        Returns:
            passed_checks: List of strings detailing checks that passed
            failed_checks: List of strings detailing checks that failed but are non-blocking (informative)
            blocking_checks: List of strings detailing checks that caused the match to fail completely
            final_decision: "MATCH_3_WAY", "MATCH_2_WAY", or "ESCALATE"
        """
        passed = []
        failed = []
        blocking = []

        if not settlement:
            blocking.append("Missing settlement candidate.")
            return passed, failed, blocking, "ESCALATE"
            
        # Amount tolerance check
        amount_diff = abs(payment.amount - settlement.settlement_amount)
        if payment.amount > 0:
            diff_percent = (amount_diff / payment.amount) * Decimal("100.0")
        else:
            diff_percent = Decimal("0.0")
            
        if diff_percent <= Decimal(str(cls.MAX_AMOUNT_TOLERANCE_PERCENT)):
            passed.append(f"Amount difference ({diff_percent:.2f}%) is within tolerance.")
        else:
            blocking.append(f"Amount difference ({diff_percent:.2f}%) exceeds tolerance of {cls.MAX_AMOUNT_TOLERANCE_PERCENT}%.")
            
        # Time window check
        time_diff = abs((settlement.settlement_time - payment.payment_time).total_seconds()) / (24 * 3600)
        if time_diff <= cls.MAX_TIME_WINDOW_DAYS:
            passed.append(f"Settlement time difference ({time_diff:.1f} days) is within {cls.MAX_TIME_WINDOW_DAYS} days.")
        else:
            blocking.append(f"Settlement time difference ({time_diff:.1f} days) exceeds {cls.MAX_TIME_WINDOW_DAYS} days limit.")

        # Reference check
        if settlement.reference == payment.id:
            passed.append("Settlement reference exactly matches payment ID.")
        else:
            failed.append(f"Settlement reference '{settlement.reference}' does not strictly match payment ID.")
            
        # Bank transaction checks
        if bank_tx:
            if bank_tx.amount == settlement.settlement_amount:
                passed.append("Bank transaction amount matches settlement amount.")
            else:
                blocking.append(f"Bank transaction amount ({bank_tx.amount}) differs from settlement amount ({settlement.settlement_amount}).")
                
            if bank_tx.bank_reference in [payment.id, settlement.reference, settlement.id]:
                passed.append("Bank transaction reference traces back to payment/settlement.")
            else:
                failed.append("Bank transaction reference does not strictly match payment or settlement IDs.")
        else:
            failed.append("No bank transaction found for this settlement.")
            
        if len(blocking) > 0:
            return passed, failed, blocking, "ESCALATE"
        
        # If no blocking checks and bank_tx exists -> 3-way
        if bank_tx:
            return passed, failed, blocking, "MATCH_3_WAY"
        else:
            return passed, failed, blocking, "MATCH_2_WAY"
