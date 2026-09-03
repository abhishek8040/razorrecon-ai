from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, func
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import pandas as pd
import io
import os
from decimal import Decimal
from pydantic import BaseModel
from dotenv import load_dotenv

from app.database import get_session, create_db_and_tables
from app.models import Merchant, Payment, Settlement, BankTransaction, ReconciliationRun, ReconciliationResult, ExceptionRecord, AuditEvent, EvaluationRun
from app.engine import ReconciliationEngine
from app.policy import PolicyEngine
from app.evaluation import EvaluationEngine
from app.ai import AIInvestigator, FinancialAssistant

load_dotenv()

app = FastAPI(title="RazorRecon AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/health")
def health_check():
    return {"status": "ok", "time": datetime.utcnow()}

@app.post("/api/reconcile")
def run_reconciliation(merchant_id: str = None, session: Session = Depends(get_session)):
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    engine = ReconciliationEngine(session, run_id)
    run = engine.run(merchant_id)
    
    # Run evaluation automatically for demo
    eval_engine = EvaluationEngine(session)
    eval_engine.evaluate(run.id, "demo")
    
    session.refresh(run)
    return run.model_dump()

@app.get("/api/metrics")
def get_metrics(session: Session = Depends(get_session)):
    total_payments = session.exec(select(func.count(Payment.id))).one()
    total_value = session.exec(select(func.sum(Payment.amount))).one() or 0
    latest_run = session.exec(select(ReconciliationRun).order_by(ReconciliationRun.created_at.desc()).limit(1)).first()
    latest_eval = session.exec(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(1)).first()
    
    metrics = {
        "total_payments": total_payments,
        "total_value": float(total_value),
        "latest_run": latest_run,
        "latest_eval": latest_eval
    }
    
    if latest_run and latest_run.total_records > 0:
        metrics["auto_match_rate"] = latest_run.auto_matched / latest_run.total_records
        metrics["exception_rate"] = latest_run.escalated / latest_run.total_records
        metrics["processing_time_ms"] = latest_run.processing_time_ms
        if latest_run.processing_time_ms and latest_run.processing_time_ms > 0:
            metrics["records_per_second"] = latest_run.total_records / (latest_run.processing_time_ms / 1000)
        else:
            metrics["records_per_second"] = 0
            
        unresolved_results = session.exec(select(ReconciliationResult).where(ReconciliationResult.run_id == latest_run.id, ReconciliationResult.result_type == "UNRESOLVED")).all()
        unresolved_payment_ids = [r.source_record_id for r in unresolved_results]
        
        unreconciled_amount = 0
        if unresolved_payment_ids:
            unresolved_payments = session.exec(select(Payment).where(Payment.id.in_(unresolved_payment_ids))).all()
            unreconciled_amount = sum([p.amount for p in unresolved_payments])
            
        metrics["unreconciled_amount"] = float(unreconciled_amount)
        
        # Exception breakdown
        exceptions = session.exec(select(ExceptionRecord).where(ExceptionRecord.run_id == latest_run.id)).all()
        breakdown = {}
        for exc in exceptions:
            breakdown[exc.exception_type] = breakdown.get(exc.exception_type, 0) + 1
        metrics["exception_breakdown"] = breakdown

    return metrics

@app.get("/api/transactions")
def get_transactions(limit: int = 100, offset: int = 0, session: Session = Depends(get_session)):
    payments = session.exec(select(Payment).offset(offset).limit(limit)).all()
    results = []
    for p in payments:
        res = session.exec(select(ReconciliationResult).where(ReconciliationResult.source_record_id == p.id)).first()
        results.append({
            "payment": p,
            "reconciliation": res
        })
    return results

@app.get("/api/exceptions")
def get_exceptions(session: Session = Depends(get_session)):
    exceptions = session.exec(select(ExceptionRecord).order_by(ExceptionRecord.created_at.desc())).all()
    return exceptions

@app.post("/api/exceptions/{exception_id}/investigate")
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
            ai_decision["explanation"] += f"\\n\\n[POLICY OVERRIDE] {policy_reason}"
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
        return {"status": "success", "investigation": fallback_decision}

class HumanReview(BaseModel):
    notes: Optional[str] = None
    
@app.post("/api/exceptions/{exception_id}/resolve")
def resolve_exception(exception_id: str, review: HumanReview = None, session: Session = Depends(get_session)):
    exc = session.exec(select(ExceptionRecord).where(ExceptionRecord.id == exception_id)).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
        
    exc.status = "RESOLVED"
    exc.reviewed_by = "USER"
    exc.reviewed_at = datetime.utcnow()
    session.add(exc)
    
    notes = review.notes if review else None
    
    audit = AuditEvent(
        id=f"evt_{uuid.uuid4().hex[:12]}",
        run_id=exc.run_id,
        action="HUMAN_REVIEW_RESOLVED",
        entity_type="Exception",
        entity_id=exc.id,
        actor="USER",
        decision="RESOLVED",
        reason=notes
    )
    session.add(audit)
    session.commit()
    return {"status": "success", "message": "Exception resolved"}

@app.post("/api/exceptions/{exception_id}/reject")
def reject_exception(exception_id: str, review: HumanReview = None, session: Session = Depends(get_session)):
    exc = session.exec(select(ExceptionRecord).where(ExceptionRecord.id == exception_id)).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
        
    exc.status = "REJECTED"
    exc.reviewed_by = "USER"
    exc.reviewed_at = datetime.utcnow()
    session.add(exc)
    
    notes = review.notes if review else None
    
    audit = AuditEvent(
        id=f"evt_{uuid.uuid4().hex[:12]}",
        run_id=exc.run_id,
        action="HUMAN_REVIEW_REJECTED",
        entity_type="Exception",
        entity_id=exc.id,
        actor="USER",
        decision="REJECTED",
        reason=notes
    )
    session.add(audit)
    session.commit()
    return {"status": "success", "message": "Exception rejected"}

@app.get("/api/audit")
def get_audit_trail(session: Session = Depends(get_session)):
    events = session.exec(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100)).all()
    return events

@app.get("/api/evaluations")
def get_evaluations(session: Session = Depends(get_session)):
    evals = session.exec(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(10)).all()
    return evals

@app.post("/api/evaluate/heldout")
def evaluate_heldout(session: Session = Depends(get_session)):
    from sqlmodel import create_engine, Session as SQLSession, SQLModel
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    heldout_dir = os.path.join(project_root, "data", "heldout")
    
    try:
        # 1. Create a completely isolated in-memory DB for the engine run
        mem_engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(mem_engine)
        
        with SQLSession(mem_engine) as mem_session:
            payments_df = pd.read_csv(os.path.join(heldout_dir, "payments.csv"))
            settlements_df = pd.read_csv(os.path.join(heldout_dir, "settlements.csv"))
            bank_txs_df = pd.read_csv(os.path.join(heldout_dir, "bank_transactions.csv"))
            
            # Load heldout data temporarily
            for _, row in payments_df.iterrows():
                row_dict = row.to_dict()
                row_dict["payment_time"] = pd.to_datetime(row_dict["payment_time"]).to_pydatetime()
                mem_session.add(Payment(**row_dict))
                
            for _, row in settlements_df.iterrows():
                row_dict = row.to_dict()
                row_dict["settlement_time"] = pd.to_datetime(row_dict["settlement_time"]).to_pydatetime()
                mem_session.add(Settlement(**row_dict))
                
            for _, row in bank_txs_df.iterrows():
                row_dict = row.to_dict()
                row_dict["transaction_time"] = pd.to_datetime(row_dict["transaction_time"]).to_pydatetime()
                mem_session.add(BankTransaction(**row_dict))
                
            mem_session.commit()
            
            # Run reconciliation on isolated DB
            run_id = f"run_{uuid.uuid4().hex[:12]}"
            recon_engine = ReconciliationEngine(mem_session, run_id)
            run = recon_engine.run(None)
            
            # Run evaluation on isolated DB
            eval_engine = EvaluationEngine(mem_session)
            eval_run = eval_engine.evaluate(run.id, "heldout")
            
            # Copy evaluation run to the main DB
            main_eval_run = EvaluationRun(**eval_run.model_dump())
            session.add(main_eval_run)
            session.commit()
            
            return main_eval_run
            
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class QAQuery(BaseModel):
    query: str

@app.post("/api/qa")
def ask_finance_assistant(query: QAQuery, session: Session = Depends(get_session)):
    # Build context
    total_payments = session.exec(select(func.count(Payment.id))).one()
    total_value = session.exec(select(func.sum(Payment.amount))).one() or 0
    open_exceptions = session.exec(select(func.count(ExceptionRecord.id)).where(ExceptionRecord.status == "OPEN")).one()
    latest_eval = session.exec(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(1)).first()
    recent_exc = session.exec(select(ExceptionRecord).order_by(ExceptionRecord.created_at.desc()).limit(5)).all()
    latest_run = session.exec(select(ReconciliationRun).order_by(ReconciliationRun.created_at.desc()).limit(1)).first()
    
    context = {
        "total_payments": total_payments,
        "total_value": float(total_value),
        "open_exceptions": open_exceptions,
        "accuracy": float(latest_eval.accuracy * 100) if latest_eval else 0.0,
        "recent_exceptions": [{"id": e.id, "type": e.exception_type, "severity": e.severity} for e in recent_exc]
    }
    
    if latest_run and latest_run.total_records > 0:
        context["auto_match_rate"] = latest_run.auto_matched / latest_run.total_records
        context["processing_time"] = latest_run.processing_time_ms
        
        unresolved_results = session.exec(select(ReconciliationResult).where(ReconciliationResult.run_id == latest_run.id, ReconciliationResult.result_type == "UNRESOLVED")).all()
        unresolved_payment_ids = [r.source_record_id for r in unresolved_results]
        
        unreconciled_amount = 0
        if unresolved_payment_ids:
            unresolved_payments = session.exec(select(Payment).where(Payment.id.in_(unresolved_payment_ids))).all()
            unreconciled_amount = sum([p.amount for p in unresolved_payments])
        context["unreconciled_amount"] = float(unreconciled_amount)
        
        exceptions = session.exec(select(ExceptionRecord).where(ExceptionRecord.run_id == latest_run.id)).all()
        breakdown = {}
        for exc in exceptions:
            breakdown[exc.exception_type] = breakdown.get(exc.exception_type, 0) + 1
        context["exception_breakdown"] = breakdown
        
        # Get top 3 largest exceptions
        if unresolved_payment_ids:
            largest_unresolved = session.exec(select(Payment).where(Payment.id.in_(unresolved_payment_ids)).order_by(Payment.amount.desc()).limit(3)).all()
            context["top_3_largest_exceptions"] = [{"id": p.id, "amount": float(p.amount)} for p in largest_unresolved]
            
    assistant = FinancialAssistant()
    answer = assistant.answer_query(query.query, context)
    return {"answer": answer}

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...), data_type: str = Form(...), session: Session = Depends(get_session)):
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        required_columns = {
            "payment": ["id", "external_id", "amount", "payment_time"],
            "settlement": ["id", "external_id", "settlement_amount", "settlement_time", "reference"],
            "bank": ["id", "external_id", "amount", "transaction_time", "bank_reference"]
        }
        
        if data_type not in required_columns:
            raise HTTPException(status_code=400, detail="Invalid data_type")
            
        missing_cols = [col for col in required_columns[data_type] if col not in df.columns]
        if missing_cols:
            raise HTTPException(status_code=400, detail=f"CSV missing required columns: {', '.join(missing_cols)}")
        
        merchants_seen = set()
        records_added = 0
        
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            merchant_id = row_dict.get("merchant_id", "merch_custom")
            
            if merchant_id not in merchants_seen:
                if not session.exec(select(Merchant).where(Merchant.id == merchant_id)).first():
                    session.add(Merchant(id=merchant_id, name="Custom Upload Merchant"))
                merchants_seen.add(merchant_id)
                
            if data_type == "payment":
                row_dict["payment_time"] = pd.to_datetime(row_dict["payment_time"]).to_pydatetime()
                record = Payment(**row_dict)
            elif data_type == "settlement":
                row_dict["settlement_time"] = pd.to_datetime(row_dict["settlement_time"]).to_pydatetime()
                record = Settlement(**row_dict)
            elif data_type == "bank":
                row_dict["transaction_time"] = pd.to_datetime(row_dict["transaction_time"]).to_pydatetime()
                record = BankTransaction(**row_dict)
            else:
                raise HTTPException(status_code=400, detail="Invalid data_type")
                
            session.add(record)
            records_added += 1
            
        session.commit()
        return {"success": True, "message": f"Successfully ingested {records_added} {data_type} records."}
        
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
