from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import os
import uuid
import json
import time

from app.models import Payment, Settlement, BankTransaction, ReconciliationRun, ReconciliationResult, ExceptionRecord, AuditEvent
from app.policy import PolicyEngine


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
            
        # Idempotency: We no longer delete old results.
        # Run scoping (querying by latest run_id) prevents duplicates in the UI.
        pass
        
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
        run.auto_matched = self.session.exec(select(ReconciliationResult).where(ReconciliationResult.run_id == self.run_id, ReconciliationResult.decision_source == "DETERMINISTIC", ReconciliationResult.result_type.in_(["MATCHED_3_WAY"]))).all().__len__()
        run.unresolved = self.session.exec(select(ReconciliationResult).where(ReconciliationResult.run_id == self.run_id, ReconciliationResult.result_type.in_(["UNRESOLVED", "MATCHED_2_WAY"]))).all().__len__()
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
                    
                    # 3-way match using unified logic
                    available_banks = {k: v for k, v in unmatched_bank_txs.items() if k not in matched_bank_tx_ids}
                    match_res = self._find_best_bank_match(p, s, available_banks)
                    b_match = match_res.get("selected_candidate") if not match_res.get("is_ambiguous") else None
                            
                    if b_match:
                        explanation = "Exact 3-way match on reference and amount."
                        matched_bank_tx_ids.append(b_match.id)
                        
                        result = ReconciliationResult(
                            id=f"res_{uuid.uuid4().hex[:12]}",
                            run_id=self.run_id,
                            source_record_type="PAYMENT",
                            source_record_id=p.id,
                            matched_record_id=s.id,
                            bank_transaction_id=b_match.id,
                            result_type="MATCHED_3_WAY",
                            confidence=1.0,
                            amount_difference=Decimal("0.0"),
                            decision_source="DETERMINISTIC",
                            time_difference_seconds=time_diff,
                            explanation=explanation
                        )
                        self.session.add(result)
                        self._log_audit("MATCH_EXACT_3_WAY", "Payment", p.id, "SYSTEM", decision="MATCH", reason=explanation)
                    else:
                        explanation = "Payment and settlement match, but missing bank transaction."
                        result = ReconciliationResult(
                            id=f"res_{uuid.uuid4().hex[:12]}",
                            run_id=self.run_id,
                            source_record_type="PAYMENT",
                            source_record_id=p.id,
                            matched_record_id=s.id,
                            bank_transaction_id=None,
                            result_type="MATCHED_2_WAY",
                            confidence=0.8,
                            amount_difference=Decimal("0.0"),
                            decision_source="DETERMINISTIC",
                            time_difference_seconds=time_diff,
                            explanation=explanation
                        )
                        self.session.add(result)
                        
                        exc = ExceptionRecord(
                            id=f"exc_{uuid.uuid4().hex[:12]}",
                            run_id=self.run_id,
                            result_id=result.id,
                            exception_type="MISSING_BANK_TRANSACTION",
                            severity="HIGH",
                            description=explanation,
                            status="OPEN"
                        )
                        self.session.add(exc)
                        self._log_audit("ESCALATE_MISSING_BANK", "Payment", p.id, "SYSTEM", decision="ESCALATE", reason=explanation)
                    
                    matched_payment_ids.append(p.id)
                    matched_settlement_ids.append(s.id)
                    
                    break
                    
        for pid in matched_payment_ids:
            unmatched_payments.pop(pid, None)
        for sid in matched_settlement_ids:
            unmatched_settlements.pop(sid, None)
        for bid in matched_bank_tx_ids:
            unmatched_bank_txs.pop(bid, None)


    def _find_best_bank_match(self, p, s, bank_txs):
        from decimal import Decimal
        candidates = [b for b in bank_txs.values() if b.merchant_id == p.merchant_id]
        if not candidates:
            return {"selected_candidate_id": None, "candidate_count": 0, "is_ambiguous": False, "evidence": {}}
            
        scored = []
        for b in candidates:
            score = 0.0
            evidence = {
                "reference_match": False,
                "amount_match": False,
                "merchant_match": True,
                "time_difference_seconds": abs((b.transaction_time - s.settlement_time).total_seconds())
            }
            
            if b.bank_reference in [p.id, s.reference, s.id]:
                score += 0.4
                evidence["reference_match"] = True
                
            if b.amount == s.settlement_amount:
                score += 0.4
                evidence["amount_match"] = True
            elif s.settlement_amount > 0 and abs(b.amount - s.settlement_amount) / s.settlement_amount <= Decimal("0.05"):
                score += 0.2
                
            if evidence["time_difference_seconds"] <= 86400 * 3:
                score += 0.1
                
            scored.append((score, b, evidence))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        
        best_score = scored[0][0]
        second_best_score = scored[1][0] if len(scored) > 1 else 0.0
        
        is_ambiguous = False
        selected_candidate = None
        
        if best_score >= 0.5:
            ties = [x for x in scored if x[0] == best_score]
            if len(ties) > 1:
                is_ambiguous = True
            else:
                selected_candidate = ties[0][1]
                
        return {
            "selected_candidate_id": selected_candidate.id if selected_candidate else None,
            "selected_candidate": selected_candidate,
            "candidate_count": len(scored),
            "candidate_score": best_score,
            "second_best_score": second_best_score,
            "is_ambiguous": is_ambiguous,
            "evidence": scored[0][2] if scored else {}
        }

    def _score_bank_candidates_old(self, p, s, bank_candidates):
        from decimal import Decimal
        scored = []
        for b in bank_candidates:
            score = 0.0
            
            # 1. Merchant match
            if b.merchant_id == s.merchant_id:
                score += 0.2
            
            # 2. Reference match
            if b.bank_reference in [p.id, s.reference, s.id]:
                score += 0.4
                
            # 3. Amount match
            if b.amount == s.settlement_amount:
                score += 0.3
            elif s.settlement_amount > 0 and abs(b.amount - s.settlement_amount) / s.settlement_amount <= Decimal("0.05"):
                score += 0.1
                
            # 4. Time proximity
            time_diff = abs((b.transaction_time - s.settlement_time).total_seconds())
            if time_diff <= 86400 * 3: # 3 days
                score += 0.1
                
            scored.append((score, b))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _resolve_remaining(self, unmatched_payments, unmatched_settlements, unmatched_bank_txs):
        import uuid
        import json
        from decimal import Decimal
        for p_id, p in unmatched_payments.items():
            candidates = []
            same_ref_settlements = []
            for s_id, s in unmatched_settlements.items():
                if s.reference == p.id:
                    same_ref_settlements.append(s)
                time_diff = abs((s.settlement_time - p.payment_time).total_seconds())
                if time_diff <= PolicyEngine.MAX_TIME_WINDOW_DAYS * 86400:
                    candidates.append(s)
            
            resolved = False
            exc_type = "AMBIGUOUS_MATCH"
            explanation = ""
            
            for s in candidates:
                # 1. Deterministic bank candidate scoring (Unified)
                match_res = self._find_best_bank_match(p, s, unmatched_bank_txs)
                b_match = match_res.get("selected_candidate")
                ambiguous_bank = match_res.get("is_ambiguous")

                passed, failed, blocking, decision = PolicyEngine.evaluate_match(p, s, b_match)
                
                if ambiguous_bank:
                    decision = "ESCALATE"
                    blocking.append("AMBIGUOUS_BANK_MATCH: Multiple bank transactions have equally high match scores.")
                    exc_type = "AMBIGUOUS_BANK_MATCH"
                elif b_match is None:
                    # If we have a settlement but no bank match, it's missing bank tx
                    exc_type = "MISSING_BANK_TRANSACTION"
                
                if decision in ["MATCH_3_WAY", "MATCH_2_WAY"]:
                    time_diff = abs((s.settlement_time - p.payment_time).total_seconds())
                    diff = abs(p.amount - s.settlement_amount)
                    
                    explanation_text = ", ".join(passed)
                    if failed:
                        explanation_text += ". Warnings: " + ", ".join(failed)
                        
                    result = ReconciliationResult(
                        id=f"res_{uuid.uuid4().hex[:12]}",
                        run_id=self.run_id,
                        source_record_type="PAYMENT",
                        source_record_id=p.id,
                        matched_record_id=s.id,
                        bank_transaction_id=b_match.id if b_match else None,
                        result_type="MATCHED_3_WAY" if decision == "MATCH_3_WAY" else "MATCHED_2_WAY",
                        confidence=0.95 if decision == "MATCH_3_WAY" else 0.8,
                        amount_difference=diff,
                        decision_source="DETERMINISTIC",
                        reason_codes_json=json.dumps(["FEE_MISMATCH"] if diff > 0 else []),
                        time_difference_seconds=time_diff,
                        explanation=explanation_text
                    )
                    self.session.add(result)
                    
                    if decision == "MATCH_2_WAY":
                        exc = ExceptionRecord(
                            id=f"exc_{uuid.uuid4().hex[:12]}",
                            run_id=self.run_id,
                            result_id=result.id,
                            exception_type="MISSING_BANK_TRANSACTION",
                            severity="HIGH",
                            description="Resolved via 2-way match. " + explanation_text,
                            status="OPEN"
                        )
                        self.session.add(exc)
                        self._log_audit("ESCALATE_MISSING_BANK", "Payment", p.id, "SYSTEM", decision="ESCALATE", reason=explanation_text)
                    else:
                        unmatched_bank_txs.pop(b_match.id, None)
                        self._log_audit("MATCH_3_WAY", "Payment", p.id, "SYSTEM", decision="MATCH", reason=explanation_text)

                    resolved = True
                    unmatched_settlements.pop(s.id, None)
                    break
                else:
                    explanation = ". ".join(blocking)
            
            if not resolved:
                if exc_type == "AMBIGUOUS_MATCH":
                    if len(candidates) == 0:
                        exc_type = "MISSING_SETTLEMENT"
                        explanation = "No settlement candidates found within time window."
                    elif len(same_ref_settlements) > 1:
                        exc_type = "DUPLICATE_SETTLEMENT"
                    elif len(same_ref_settlements) == 1:
                        s = same_ref_settlements[0]
                        b_match = next((b for b in unmatched_bank_txs.values() if b.bank_reference in [p.id, s.reference, s.id]), None)
                        passed, failed, blocking, dec = PolicyEngine.evaluate_match(p, s, b_match)
                        explanation = ". ".join(blocking)
                        if any("time" in b.lower() for b in blocking):
                            exc_type = "DELAYED_SETTLEMENT"
                        elif any("tolerance" in b.lower() for b in blocking):
                            exc_type = "AMOUNT_MISMATCH"
                
                # Fetch a detailed explanation using policy on the best candidate if it exists
                if not explanation and candidates:
                    passed, failed, blocking, dec = PolicyEngine.evaluate_match(p, candidates[0], None)
                    explanation = ". ".join(blocking)

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
                    severity="HIGH",
                    description=explanation or "No viable candidates found.",
                    status="OPEN"
                )
                self.session.add(exc)
                self._log_audit(f"ESCALATE_{exc_type}", "Payment", p.id, "SYSTEM", decision="ESCALATE", reason=explanation)

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
