import re

with open("backend/app/main.py", "r") as f:
    content = f.read()

# Replace import
content = content.replace("from app.engine import ReconciliationEngine, MAX_TIME_WINDOW_DAYS", 
                          "from app.engine import ReconciliationEngine\nfrom app.policy import PolicyEngine")

# Update investigate_exception
new_investigate = """@app.post("/api/exceptions/{exception_id}/investigate")
def investigate_exception(exception_id: str, session: Session = Depends(get_session)):
    exc = session.exec(select(ExceptionRecord).where(ExceptionRecord.id == exception_id)).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
        
    res = session.exec(select(ReconciliationResult).where(ReconciliationResult.id == exc.result_id)).first()
    if not res:
        raise HTTPException(status_code=404, detail="Result not found")
        
    p = session.exec(select(Payment).where(Payment.id == res.source_record_id)).first()
    
    settlements = session.exec(select(Settlement).where(Settlement.merchant_id == p.merchant_id)).all()
    
    # Filter by time proximity and sort by amount difference
    valid_candidates = []
    for s in settlements:
        time_diff = abs((s.settlement_time - p.payment_time).total_seconds())
        if time_diff <= PolicyEngine.MAX_TIME_WINDOW_DAYS * 86400:
            valid_candidates.append(s)
            
    valid_candidates.sort(key=lambda s: abs(s.settlement_amount - p.amount))
    candidates = valid_candidates[:5]
    
    # Bank Candidates
    bank_txs = session.exec(select(BankTransaction).where(BankTransaction.merchant_id == p.merchant_id)).all()
    valid_bank_candidates = []
    for b in bank_txs:
        time_diff = abs((b.transaction_time - p.payment_time).total_seconds())
        if time_diff <= PolicyEngine.MAX_TIME_WINDOW_DAYS * 86400 * 2: # Give bank extra time
            valid_bank_candidates.append(b)
            
    valid_bank_candidates.sort(key=lambda b: abs(b.amount - p.amount))
    bank_candidates = valid_bank_candidates[:5]
    
    investigator = AIInvestigator()
    try:
        ai_decision = investigator.investigate_exception(p, candidates, bank_candidates)
        
        # Deterministic Policy Checks
        policy_overridden = False
        policy_reason = ""
        passed_checks = []
        failed_checks = []
        blocking_checks = []
        
        if ai_decision.get("decision") == "MATCH":
            confidence = ai_decision.get("confidence", 0.0)
            if confidence < PolicyEngine.MIN_AUTO_RESOLUTION_CONFIDENCE:
                policy_overridden = True
                policy_reason = f"AI confidence ({confidence}) is below the strict {PolicyEngine.MIN_AUTO_RESOLUTION_CONFIDENCE} threshold for auto-resolution."
                blocking_checks.append(policy_reason)
            else:
                # Use policy engine to evaluate the matched candidate
                matched_s_id = ai_decision.get("matched_settlement_id")
                matched_s = next((s for s in candidates if s.id == matched_s_id), None) if matched_s_id else None
                
                matched_b_id = ai_decision.get("matched_bank_transaction_id")
                matched_b = next((b for b in bank_candidates if b.id == matched_b_id), None) if matched_b_id else None
                
                if matched_s:
                    passed, failed, blocking, dec = PolicyEngine.evaluate_match(p, matched_s, matched_b)
                    passed_checks = passed
                    failed_checks = failed
                    blocking_checks = blocking
                    if len(blocking) > 0:
                        policy_overridden = True
                        policy_reason = "Policy Blockers: " + ", ".join(blocking)
                else:
                    policy_overridden = True
                    policy_reason = "AI suggested a MATCH but did not provide a valid matched_settlement_id."
                    blocking_checks.append(policy_reason)

        if policy_overridden:
            ai_decision["decision"] = "REVIEW"
            ai_decision["explanation"] += f"\n\n[POLICY OVERRIDE] {policy_reason}"
            ai_decision["recommended_action"] = "Manual human review required"
            
        ai_decision["passed_checks"] = passed_checks
        ai_decision["failed_checks"] = failed_checks
        ai_decision["blocking_checks"] = blocking_checks

        res.metadata_json = json.dumps({"ai_investigation": ai_decision})
        session.add(res)
        
        audit = AuditEvent(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            run_id=res.run_id,
            action="AI_INVESTIGATION",
            entity_type="Payment",
            entity_id=p.id,
            actor="AI",
            decision=ai_decision.get("decision"),
            reason=ai_decision.get("explanation")
        )
        session.add(audit)
        
        session.commit()
        return {"status": "success", "investigation": ai_decision}
    except Exception as e:
        # Structured fallback for AI failure
        fallback_decision = {
            "decision": "REVIEW",
            "confidence": 0.0,
            "reason_codes": ["AI_FAILURE"],
            "explanation": f"AI investigation failed: {str(e)}. Case escalated to human review.",
            "recommended_action": "Manual human review required",
            "passed_checks": [],
            "failed_checks": [],
            "blocking_checks": ["AI_FAILURE"]
        }
        res.metadata_json = json.dumps({"ai_investigation": fallback_decision})
        session.add(res)
        
        audit = AuditEvent(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            run_id=res.run_id,
            action="AI_FAILURE",
            entity_type="Payment",
            entity_id=p.id,
            actor="SYSTEM",
            decision="REVIEW",
            reason=str(e)
        )
        session.add(audit)
        session.commit()
        return {"status": "success", "investigation": fallback_decision}"""

start_idx = content.find("@app.post(\"/api/exceptions/{exception_id}/investigate\")")
end_idx = content.find("@app.post(\"/api/exceptions/{exception_id}/resolve\")")

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_investigate + "\n\n" + content[end_idx:]

with open("backend/app/main.py", "w") as f:
    f.write(content)
