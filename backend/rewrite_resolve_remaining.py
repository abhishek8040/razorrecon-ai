import re

with open("backend/app/engine.py", "r") as f:
    content = f.read()

new_resolve = """    def _resolve_remaining(self, unmatched_payments, unmatched_settlements, unmatched_bank_txs):
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
            for s in candidates:
                # Find best bank transaction match if any
                b_match = None
                for b_id, b in unmatched_bank_txs.items():
                    # We relax the strict == s.settlement_amount check and let PolicyEngine handle tolerance checks if we wanted, 
                    # but since the prompt says "Do not require exact bank_reference matching for every legitimate candidate"
                    # let's just find the one that either matches the settlement reference or the payment reference.
                    if b.bank_reference in [p.id, s.reference, s.id]:
                        b_match = b
                        break

                passed, failed, blocking, decision = PolicyEngine.evaluate_match(p, s, b_match)
                
                if decision in ["MATCH_3_WAY", "MATCH_2_WAY"]:
                    time_diff = abs((s.settlement_time - p.payment_time).total_seconds())
                    diff = abs(p.amount - s.settlement_amount)
                    
                    explanation = ", ".join(passed)
                    if failed:
                        explanation += ". Warnings: " + ", ".join(failed)
                        
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
                        explanation=explanation
                    )
                    self.session.add(result)
                    
                    if decision == "MATCH_2_WAY":
                        exc = ExceptionRecord(
                            id=f"exc_{uuid.uuid4().hex[:12]}",
                            run_id=self.run_id,
                            result_id=result.id,
                            exception_type="MISSING_BANK_TRANSACTION",
                            severity="HIGH",
                            description="Resolved via 2-way match. " + explanation,
                            status="OPEN"
                        )
                        self.session.add(exc)
                        self._log_audit("ESCALATE_MISSING_BANK", "Payment", p.id, "SYSTEM", decision="ESCALATE", reason=explanation)
                    else:
                        unmatched_bank_txs.pop(b_match.id, None)
                        self._log_audit("MATCH_3_WAY", "Payment", p.id, "SYSTEM", decision="MATCH", reason=explanation)

                    resolved = True
                    unmatched_settlements.pop(s.id, None)
                    break
            
            if not resolved:
                exc_type = "AMBIGUOUS_MATCH"
                if len(candidates) == 0:
                    exc_type = "MISSING_SETTLEMENT"
                elif len(same_ref_settlements) > 1:
                    exc_type = "DUPLICATE_SETTLEMENT"
                elif len(same_ref_settlements) == 1:
                    s = same_ref_settlements[0]
                    # We can use policy to get the exact failure reasons
                    b_match = next((b for b in unmatched_bank_txs.values() if b.bank_reference in [p.id, s.reference, s.id]), None)
                    passed, failed, blocking, dec = PolicyEngine.evaluate_match(p, s, b_match)
                    if any("time" in b.lower() for b in blocking):
                        exc_type = "DELAYED_SETTLEMENT"
                    elif any("tolerance" in b.lower() for b in blocking):
                        exc_type = "AMOUNT_MISMATCH"
                
                # Fetch a detailed explanation using policy on the best candidate if it exists
                best_cand = candidates[0] if candidates else None
                b_best = None
                if best_cand:
                    b_best = next((b for b in unmatched_bank_txs.values() if b.bank_reference in [p.id, best_cand.reference, best_cand.id]), None)
                passed, failed, blocking, dec = PolicyEngine.evaluate_match(p, best_cand, b_best)
                
                blocking_str = ", ".join(blocking) if blocking else "No specific blocks."
                
                result = ReconciliationResult(
                    id=f"res_{uuid.uuid4().hex[:12]}",
                    run_id=self.run_id,
                    source_record_type="PAYMENT",
                    source_record_id=p.id,
                    result_type="UNRESOLVED",
                    confidence=0.0,
                    decision_source="DETERMINISTIC",
                    explanation=f"Policy Blockers: {blocking_str}"
                )
                self.session.add(result)
                
                exc = ExceptionRecord(
                    id=f"exc_{uuid.uuid4().hex[:12]}",
                    run_id=self.run_id,
                    result_id=result.id,
                    exception_type=exc_type,
                    severity="HIGH" if p.amount > 10000 else "MEDIUM",
                    description=f"Blockers: {blocking_str}",
                    status="OPEN"
                )
                self.session.add(exc)
                self._log_audit("ESCALATE_TO_REVIEW", "Payment", p.id, "SYSTEM", decision="ESCALATE", reason="No deterministic match")"""

start_idx = content.find("    def _resolve_remaining")
end_idx = content.find("    def _log_audit")

new_content = content[:start_idx] + new_resolve + "\n\n" + content[end_idx:]

with open("backend/app/engine.py", "w") as f:
    f.write(new_content)
