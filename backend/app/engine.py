from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import os
import uuid
import json
import time

from app.models import Payment, Settlement, BankTransaction, ReconciliationRun, ReconciliationResult, ExceptionRecord, AuditEvent

MAX_AMOUNT_TOLERANCE_PERCENT = Decimal(os.environ.get("MAX_AMOUNT_TOLERANCE_PERCENT", "2.0"))
MAX_TIME_WINDOW_DAYS = int(os.environ.get("MAX_TIME_WINDOW_DAYS", "5"))

class ReconciliationEngine:
    def __init__(self, session: Session, run_id: str):
        self.session = session
        self.run_id = run_id
        
    def run(self, merchant_id: str = None):
        start_time = time.time()
        
        # 1. Setup run
        run = ReconciliationRun(
            id=self.run_id,
            merchant_id=merchant_id or "ALL",
            status="RUNNING"
        )
        self.session.add(run)
        self.session.commit()
        
        # Log audit
        self._log_audit("START_RECONCILIATION", "ReconciliationRun", run.id, "SYSTEM")
        
        if merchant_id:
            payments = self.session.exec(select(Payment).where(Payment.merchant_id == merchant_id)).all()
            settlements = self.session.exec(select(Settlement).where(Settlement.merchant_id == merchant_id)).all()
            bank_txs = self.session.exec(select(BankTransaction).where(BankTransaction.merchant_id == merchant_id)).all()
        else:
            payments = self.session.exec(select(Payment)).all()
            settlements = self.session.exec(select(Settlement)).all()
            bank_txs = self.session.exec(select(BankTransaction)).all()
            
        # Idempotency: DELETE old results for the same payments
        payment_ids = [p.id for p in payments]
        if payment_ids:
            old_results = self.session.exec(select(ReconciliationResult).where(ReconciliationResult.source_record_id.in_(payment_ids))).all()
            old_result_ids = [r.id for r in old_results]
            if old_result_ids:
                old_exceptions = self.session.exec(select(ExceptionRecord).where(ExceptionRecord.result_id.in_(old_result_ids))).all()
                for exc in old_exceptions:
                    self.session.delete(exc)
                for res in old_results:
                    self.session.delete(res)
            self.session.commit()
        
        # Dictionaries for quick lookup
        unmatched_payments = {p.id: p for p in payments}
        unmatched_settlements = {s.id: s for s in settlements}
        unmatched_bank_txs = {b.id: b for b in bank_txs}
        
        run.total_records = len(payments)
        
        # Exact Matching
        self._exact_match(unmatched_payments, unmatched_settlements, unmatched_bank_txs)
        
        # Find candidates for remaining
        self._resolve_remaining(unmatched_payments, unmatched_settlements, unmatched_bank_txs)
        
        # Finalize run
        run.status = "COMPLETED"
        run.processing_time_ms = int((time.time() - start_time) * 1000)
        run.auto_matched = self.session.exec(select(ReconciliationResult).where(ReconciliationResult.run_id == self.run_id, ReconciliationResult.decision_source == "DETERMINISTIC", ReconciliationResult.result_type.in_(["MATCHED_EXACT", "MATCHED_AFTER_FEE_ADJUSTMENT"]))).all().__len__()
        run.unresolved = self.session.exec(select(ReconciliationResult).where(ReconciliationResult.run_id == self.run_id, ReconciliationResult.result_type == "UNRESOLVED")).all().__len__()
        run.escalated = self.session.exec(select(ExceptionRecord).where(ExceptionRecord.run_id == self.run_id)).all().__len__()
        self.session.add(run)
        self.session.commit()
        self._log_audit("COMPLETE_RECONCILIATION", "ReconciliationRun", run.id, "SYSTEM")
        
        return run

    def _exact_match(self, unmatched_payments, unmatched_settlements, unmatched_bank_txs):
        matched_payment_ids = []
        matched_settlement_ids = []
        matched_bank_tx_ids = []
        
        for p_id, p in unmatched_payments.items():
            for s_id, s in unmatched_settlements.items():
                if s_id in matched_settlement_ids: continue
                
                if s.reference == p.id and s.settlement_amount == p.amount:
                    time_diff = abs((s.settlement_time - p.payment_time).total_seconds())
                    
                    # 3-way match
                    b_match = None
                    for b_id, b in unmatched_bank_txs.items():
                        if b_id in matched_bank_tx_ids: continue
                        if b.bank_reference == s.id and b.amount == s.settlement_amount:
                            b_match = b
                            break
                            
                    explanation = "Exact match on reference and amount (2-way)."
                    if b_match:
                        explanation = "Exact 3-way match on reference and amount."
                        matched_bank_tx_ids.append(b_match.id)
                        
                    result = ReconciliationResult(
                        id=f"res_{uuid.uuid4().hex[:12]}",
                        run_id=self.run_id,
                        source_record_type="PAYMENT",
                        source_record_id=p.id,
                        matched_record_id=s.id,
                        result_type="MATCHED_EXACT",
                        confidence=1.0,
                        amount_difference=Decimal("0.0"),
                        decision_source="DETERMINISTIC",
                        time_difference_seconds=time_diff,
                        explanation=explanation
                    )
                    self.session.add(result)
                    
                    matched_payment_ids.append(p.id)
                    matched_settlement_ids.append(s.id)
                    
                    self._log_audit("MATCH_EXACT", "Payment", p.id, "SYSTEM", decision="MATCH", reason=explanation)
                    break
                    
        for pid in matched_payment_ids:
            unmatched_payments.pop(pid, None)
        for sid in matched_settlement_ids:
            unmatched_settlements.pop(sid, None)
        for bid in matched_bank_tx_ids:
            unmatched_bank_txs.pop(bid, None)

    def _resolve_remaining(self, unmatched_payments, unmatched_settlements, unmatched_bank_txs):
        for p_id, p in unmatched_payments.items():
            candidates = []
            same_ref_settlements = []
            for s_id, s in unmatched_settlements.items():
                if s.reference == p.id:
                    same_ref_settlements.append(s)
                time_diff = abs((s.settlement_time - p.payment_time).total_seconds())
                if time_diff <= MAX_TIME_WINDOW_DAYS * 86400:
                    candidates.append(s)
            
            resolved = False
            for s in candidates:
                if s.reference == p.id:
                    diff = abs(p.amount - s.settlement_amount)
                    pct_diff = (diff / p.amount) * 100
                    time_diff = abs((s.settlement_time - p.payment_time).total_seconds())
                    
                    if pct_diff <= MAX_AMOUNT_TOLERANCE_PERCENT:
                        explanation = "Fee adjustment within 2% tolerance."
                        result = ReconciliationResult(
                            id=f"res_{uuid.uuid4().hex[:12]}",
                            run_id=self.run_id,
                            source_record_type="PAYMENT",
                            source_record_id=p.id,
                            matched_record_id=s.id,
                            result_type="MATCHED_AFTER_FEE_ADJUSTMENT",
                            confidence=0.95,
                            amount_difference=diff,
                            decision_source="DETERMINISTIC",
                            reason_codes_json=json.dumps(["FEE_MISMATCH"]),
                            time_difference_seconds=time_diff,
                            explanation=explanation
                        )
                        self.session.add(result)
                        resolved = True
                        unmatched_settlements.pop(s.id, None)
                        self._log_audit("MATCH_FEE_ADJUSTMENT", "Payment", p.id, "SYSTEM", decision="MATCH", reason=explanation)
                        break
            
            if not resolved:
                exc_type = "AMBIGUOUS_MATCH"
                if len(candidates) == 0:
                    exc_type = "MISSING_SETTLEMENT"
                elif len(same_ref_settlements) > 1:
                    exc_type = "DUPLICATE_SETTLEMENT"
                elif len(same_ref_settlements) == 1:
                    s = same_ref_settlements[0]
                    time_diff = abs((s.settlement_time - p.payment_time).total_seconds())
                    diff = abs(p.amount - s.settlement_amount)
                    pct_diff = (diff / p.amount) * 100
                    if time_diff > MAX_TIME_WINDOW_DAYS * 86400:
                        exc_type = "DELAYED_SETTLEMENT"
                    elif s.settlement_amount < (p.amount * Decimal("0.5")):
                        exc_type = "PARTIAL_SETTLEMENT"
                    elif pct_diff > MAX_AMOUNT_TOLERANCE_PERCENT:
                        exc_type = "AMOUNT_MISMATCH"
                
                explanation = "No automatic resolution found."
                result = ReconciliationResult(
                    id=f"res_{uuid.uuid4().hex[:12]}",
                    run_id=self.run_id,
                    source_record_type="PAYMENT",
                    source_record_id=p.id,
                    result_type="UNRESOLVED",
                    confidence=0.0,
                    decision_source="DETERMINISTIC",
                    explanation=explanation
                )
                self.session.add(result)
                
                exc = ExceptionRecord(
                    id=f"exc_{uuid.uuid4().hex[:12]}",
                    run_id=self.run_id,
                    result_id=result.id,
                    exception_type=exc_type,
                    severity="HIGH" if p.amount > 10000 else "MEDIUM",
                    description=f"Could not automatically reconcile payment {p.id}. Candidates found: {len(candidates)}. Reason: {exc_type.replace('_', ' ')}",
                    status="OPEN"
                )
                self.session.add(exc)
                self._log_audit("ESCALATE_TO_REVIEW", "Payment", p.id, "SYSTEM", decision="ESCALATE", reason="No deterministic match")

    def _log_audit(self, action: str, entity_type: str, entity_id: str, actor: str, decision: str = None, reason: str = None):
        audit = AuditEvent(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            run_id=self.run_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            decision=decision,
            reason=reason
        )
        self.session.add(audit)
