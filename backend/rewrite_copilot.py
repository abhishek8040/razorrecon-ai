import os
import json

code = """
import os
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlmodel import Session, select, func
from pydantic import BaseModel, Field

from app.models import Payment, Settlement, BankTransaction, ReconciliationRun, ReconciliationResult, ExceptionRecord, AuditEvent
from app.policy import PolicyEngine

class CopilotTools:
    def __init__(self, session: Session):
        self.session = session
        
    def get_reconciliation_metrics(self) -> dict:
        \"\"\"Retrieve live metrics for the current/latest reconciliation run.\"\"\"
        latest_run = self.session.exec(select(ReconciliationRun).order_by(ReconciliationRun.created_at.desc()).limit(1)).first()
        if not latest_run:
            return {"message": "No reconciliation runs found."}
            
        run_results = self.session.exec(select(ReconciliationResult).where(ReconciliationResult.run_id == latest_run.id)).all()
        payment_ids = [r.source_record_id for r in run_results]
        
        total_payments = len(payment_ids)
        total_value = float(self.session.exec(select(func.sum(Payment.amount)).where(Payment.id.in_(payment_ids))).one() or 0) if payment_ids else 0.0
        
        matched_3_way = sum(1 for r in run_results if r.result_type == "MATCHED_3_WAY")
        matched_2_way = sum(1 for r in run_results if r.result_type == "MATCHED_2_WAY")
        unresolved = sum(1 for r in run_results if r.result_type == "UNRESOLVED")
        
        exceptions = self.session.exec(select(ExceptionRecord).where(ExceptionRecord.run_id == latest_run.id)).all()
        
        return {
            "total_payments": total_payments,
            "total_value": total_value,
            "matched_3_way": matched_3_way,
            "matched_2_way": matched_2_way,
            "unresolved": unresolved,
            "exceptions": len(exceptions),
            "exception_rate": len(exceptions) / total_payments if total_payments > 0 else 0,
            "three_way_match_rate": matched_3_way / total_payments if total_payments > 0 else 0
        }

    def get_transaction_details(self, transaction_id: str) -> dict:
        \"\"\"Retrieve verified structured information about a specific transaction.\"\"\"
        if not isinstance(transaction_id, str) or not transaction_id.strip():
            return {"error": "Invalid transaction_id"}
        transaction_id = transaction_id.strip()[:100]
        
        latest_run = self.session.exec(select(ReconciliationRun).order_by(ReconciliationRun.created_at.desc()).limit(1)).first()
        
        p = self.session.exec(select(Payment).where(Payment.id == transaction_id)).first()
        if not p:
            s = self.session.exec(select(Settlement).where(Settlement.id == transaction_id)).first()
            if s:
                p = self.session.exec(select(Payment).where(Payment.id == s.reference)).first()
        
        if not p:
            return {"found": False, "message": "Transaction not found"}
            
        res = None
        if latest_run:
            res = self.session.exec(select(ReconciliationResult).where(
                ReconciliationResult.source_record_id == p.id,
                ReconciliationResult.run_id == latest_run.id
            )).first()
            
        if not res:
            return {
                "found": True,
                "payment": p.model_dump(),
                "reconciliation_result": None,
                "status": "NOT_RECONCILED_IN_CURRENT_RUN",
                "message": "Transaction exists but has no reconciliation result in the current run."
            }
            
        details = {
            "found": True,
            "payment": p.model_dump(),
            "reconciliation_result": res.model_dump(),
            "status": res.result_type,
            "matching_evidence": res.explanation
        }
        
        if res.matched_record_id:
            s = self.session.exec(select(Settlement).where(Settlement.id == res.matched_record_id)).first()
            details["settlement"] = s.model_dump() if s else None
            
        if res.bank_transaction_id:
            b = self.session.exec(select(BankTransaction).where(BankTransaction.id == res.bank_transaction_id)).first()
            details["bank_transaction"] = b.model_dump() if b else None
            
        return details

    def search_transactions(self, transaction_id: str = None, merchant_id: str = None, status: str = None, min_amount: float = None, max_amount: float = None, start_date: str = None, end_date: str = None, limit: int = 10) -> dict:
        \"\"\"Search/filter transactions for the current/latest run.\"\"\"
        try:
            limit = max(1, min(int(limit), 50))
        except (ValueError, TypeError):
            limit = 10
            
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            return {"error": "min_amount cannot be greater than max_amount"}
            
        sd, ed = None, None
        try:
            if start_date: sd = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date: ed = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            return {"error": "Invalid date format. Use ISO format."}
            
        latest_run = self.session.exec(select(ReconciliationRun).order_by(ReconciliationRun.created_at.desc()).limit(1)).first()
        if not latest_run:
            return {"count": 0, "transactions": []}
            
        query = select(ReconciliationResult, Payment).join(Payment, ReconciliationResult.source_record_id == Payment.id).where(ReconciliationResult.run_id == latest_run.id)
        
        if transaction_id and isinstance(transaction_id, str):
            query = query.where(ReconciliationResult.source_record_id.contains(transaction_id.strip()[:100]))
        if merchant_id and isinstance(merchant_id, str):
            query = query.where(Payment.merchant_id == merchant_id.strip()[:100])
        if status and isinstance(status, str):
            query = query.where(ReconciliationResult.result_type == status.strip()[:50])
        if min_amount is not None:
            query = query.where(Payment.amount >= Decimal(str(min_amount)))
        if max_amount is not None:
            query = query.where(Payment.amount <= Decimal(str(max_amount)))
        if sd:
            query = query.where(Payment.payment_time >= sd)
        if ed:
            query = query.where(Payment.payment_time <= ed)
            
        results = self.session.exec(query.limit(limit)).all()
        
        txs = []
        for r, p in results:
            txs.append({
                "payment_id": r.source_record_id,
                "status": r.result_type,
                "amount": float(p.amount),
                "explanation": r.explanation
            })
            
        return {"count": len(txs), "transactions": txs}

    def get_exception_summary(self) -> dict:
        \"\"\"Return summary of exceptions for the current run.\"\"\"
        latest_run = self.session.exec(select(ReconciliationRun).order_by(ReconciliationRun.created_at.desc()).limit(1)).first()
        if not latest_run:
            return {"total_exceptions": 0}
            
        exceptions = self.session.exec(select(ExceptionRecord).where(ExceptionRecord.run_id == latest_run.id)).all()
        
        breakdown = {}
        for exc in exceptions:
            breakdown[exc.exception_type] = breakdown.get(exc.exception_type, 0) + 1
            
        return {
            "total_exceptions": len(exceptions),
            "exception_counts_by_type": breakdown,
            "unresolved_exceptions": sum(1 for e in exceptions if e.status == "OPEN"),
            "recent_exceptions": [e.model_dump() for e in exceptions[:5]]
        }

    def get_exception_details(self, exception_id: str) -> dict:
        \"\"\"Return detailed information about a specific exception.\"\"\"
        if not isinstance(exception_id, str) or not exception_id.strip():
            return {"error": "Invalid exception_id"}
        exception_id = exception_id.strip()[:100]
        
        exc = self.session.exec(select(ExceptionRecord).where(ExceptionRecord.id == exception_id)).first()
        if not exc:
            latest_run = self.session.exec(select(ReconciliationRun).order_by(ReconciliationRun.created_at.desc()).limit(1)).first()
            if latest_run:
                res = self.session.exec(select(ReconciliationResult).where(
                    ReconciliationResult.source_record_id == exception_id,
                    ReconciliationResult.run_id == latest_run.id
                )).first()
                if res:
                    exc = self.session.exec(select(ExceptionRecord).where(ExceptionRecord.result_id == res.id)).first()
                    
        if not exc:
            return {"found": False, "message": "Exception not found"}
            
        details = {
            "found": True,
            "exception_id": exc.id,
            "exception_type": exc.exception_type,
            "status": exc.status,
            "severity": exc.severity,
            "description": exc.description,
            "reviewer_information": {
                "reviewed_by": exc.reviewed_by,
                "reviewed_at": exc.reviewed_at.isoformat() if exc.reviewed_at else None,
                "notes": exc.notes
            }
        }
        
        if exc.result_id:
            res = self.session.exec(select(ReconciliationResult).where(ReconciliationResult.id == exc.result_id)).first()
            if res:
                details["reconciliation_result"] = res.model_dump()
                details["payment_id"] = res.source_record_id
                
                p = self.session.exec(select(Payment).where(Payment.id == res.source_record_id)).first()
                if p: details["payment"] = p.model_dump()
                
                if res.matched_record_id:
                    s = self.session.exec(select(Settlement).where(Settlement.id == res.matched_record_id)).first()
                    if s: details["settlement"] = s.model_dump()
                    
                if res.bank_transaction_id:
                    b = self.session.exec(select(BankTransaction).where(BankTransaction.id == res.bank_transaction_id)).first()
                    if b: details["bank_transaction"] = b.model_dump()
                    
        return details

    def get_policy_explanation(self, transaction_id: str) -> dict:
        \"\"\"Return actual deterministic policy evaluation for a transaction.\"\"\"
        if not isinstance(transaction_id, str) or not transaction_id.strip():
            return {"error": "Invalid transaction_id"}
        transaction_id = transaction_id.strip()[:100]
        
        p = self.session.exec(select(Payment).where(Payment.id == transaction_id)).first()
        if not p:
            return {"found": False, "message": "Transaction not found"}
            
        latest_run = self.session.exec(select(ReconciliationRun).order_by(ReconciliationRun.created_at.desc()).limit(1)).first()
        if not latest_run:
            return {"found": False, "message": "No run found"}
            
        res = self.session.exec(select(ReconciliationResult).where(
            ReconciliationResult.source_record_id == p.id,
            ReconciliationResult.run_id == latest_run.id
        )).first()
        
        if not res:
            return {"found": False, "message": "No reconciliation result found"}
            
        b = self.session.exec(select(BankTransaction).where(BankTransaction.id == res.bank_transaction_id)).first() if res.bank_transaction_id else None
        s = self.session.exec(select(Settlement).where(Settlement.id == res.matched_record_id)).first() if res.matched_record_id else None
        
        passed, failed, blocking, decision = PolicyEngine.evaluate_match(p, s, b)
        
        return {
            "found": True,
            "transaction_id": transaction_id,
            "decision": res.result_type,
            "reason": res.explanation,
            "passed_checks": passed,
            "failed_checks": failed,
            "blocking_checks": blocking
        }

    def get_audit_trail(self, transaction_id: str, limit: int = 10) -> dict:
        \"\"\"Return chronological audit history for a transaction.\"\"\"
        if not isinstance(transaction_id, str) or not transaction_id.strip():
            return {"error": "Invalid transaction_id"}
        transaction_id = transaction_id.strip()[:100]
        
        try:
            limit = max(1, min(int(limit), 50))
        except (ValueError, TypeError):
            limit = 10
            
        # Precise relationship-based query: look for events tied to the payment, or tied to its results/exceptions
        # We will collect IDs related to this transaction to get all relevant events
        entity_ids = [transaction_id]
        
        # Add result IDs and exception IDs for this payment
        results = self.session.exec(select(ReconciliationResult).where(ReconciliationResult.source_record_id == transaction_id)).all()
        for r in results:
            entity_ids.append(r.id)
            if r.matched_record_id: entity_ids.append(r.matched_record_id)
            if r.bank_transaction_id: entity_ids.append(r.bank_transaction_id)
            
        exceptions = self.session.exec(select(ExceptionRecord).where(ExceptionRecord.result_id.in_([r.id for r in results]))).all()
        for exc in exceptions:
            entity_ids.append(exc.id)
            
        events = self.session.exec(select(AuditEvent).where(AuditEvent.entity_id.in_(entity_ids)).order_by(AuditEvent.created_at.desc()).limit(limit)).all()
            
        return {
            "transaction_id": transaction_id,
            "events": [e.model_dump() for e in events]
        }

def get_copilot_tool_declarations():
    return [
        {
            "name": "get_reconciliation_metrics",
            "description": "Retrieve live metrics for the current/latest reconciliation run.",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "get_transaction_details",
            "description": "Retrieve verified structured information about a specific transaction ID.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "transaction_id": {"type": "string", "description": "The ID of the transaction (e.g. pay_batch1_0001)"}
                },
                "required": ["transaction_id"]
            }
        },
        {
            "name": "search_transactions",
            "description": "Search/filter transactions for the current/latest run.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "transaction_id": {"type": "string", "description": "Filter by transaction ID"},
                    "merchant_id": {"type": "string", "description": "Filter by merchant ID"},
                    "status": {"type": "string", "description": "Filter by status, e.g. MATCHED_3_WAY, MATCHED_2_WAY, UNRESOLVED"},
                    "min_amount": {"type": "number", "description": "Filter by minimum amount"},
                    "max_amount": {"type": "number", "description": "Filter by maximum amount"},
                    "start_date": {"type": "string", "description": "Filter by start date (ISO format)"},
                    "end_date": {"type": "string", "description": "Filter by end date (ISO format)"},
                    "limit": {"type": "integer", "description": "Max number of results to return (up to 50)"}
                }
            }
        },
        {
            "name": "get_exception_summary",
            "description": "Return summary of exceptions for the current run.",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "get_exception_details",
            "description": "Return detailed information about a specific exception or transaction ID.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "exception_id": {"type": "string", "description": "The ID of the exception or transaction"}
                },
                "required": ["exception_id"]
            }
        },
        {
            "name": "get_policy_explanation",
            "description": "Return actual deterministic policy information explaining why a decision was made.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "transaction_id": {"type": "string", "description": "The ID of the transaction"}
                },
                "required": ["transaction_id"]
            }
        },
        {
            "name": "get_audit_trail",
            "description": "Return chronological audit history for a transaction.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "transaction_id": {"type": "string", "description": "The ID of the transaction"},
                    "limit": {"type": "integer", "description": "Limit of events (max 50)"}
                },
                "required": ["transaction_id"]
            }
        }
    ]

class FinanceCopilot:
    def __init__(self, session: Session):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.session = session
        self.tools = CopilotTools(session)
        self.ALLOWED_TOOLS = {
            "get_reconciliation_metrics": self.tools.get_reconciliation_metrics,
            "get_transaction_details": self.tools.get_transaction_details,
            "search_transactions": self.tools.search_transactions,
            "get_exception_summary": self.tools.get_exception_summary,
            "get_exception_details": self.tools.get_exception_details,
            "get_policy_explanation": self.tools.get_policy_explanation,
            "get_audit_trail": self.tools.get_audit_trail
        }
        
    def answer_query(self, query: str) -> dict:
        if not self.api_key or os.environ.get("AI_PROVIDER", "mock").lower() != "gemini":
            return {
                "answer": "Mock Mode: AI explanation is temporarily unavailable. The underlying reconciliation system and verified data remain available.",
                "tools_used": []
            }
            
        import google.genai as genai
        from google.genai import types
        
        client = genai.Client(api_key=self.api_key)
        
        system_instruction = \"\"\"You are RazorRecon Finance Copilot.
You help users understand verified reconciliation data.
You must base factual financial claims on data returned by approved tools.
Never invent transaction amounts, statuses, counts, policy decisions, or audit events.
If verified information is unavailable, say so clearly.
If a transaction does not exist, say it was not found.
You are READ-ONLY. You cannot modify financial records or override the PolicyEngine.
When answering:
1. State verified facts.
2. Explain matching evidence.
3. Explain deterministic policy results.
4. Clearly distinguish facts from interpretation.
5. Clearly state uncertainty where applicable.
Never expose API keys, environment variables, or database credentials.
Do not provide legal, tax, investment, or accounting advice.\"\"\"

        tools_used = []
        MAX_TOOL_CALLS = 5
        
        chat = client.chats.create(
            model='gemini-2.5-flash',
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[{"function_declarations": get_copilot_tool_declarations()}],
                temperature=0.1
            )
        )
        
        try:
            response = chat.send_message(query)
            
            call_count = 0
            called_signatures = set()
            
            while response.function_calls and call_count < MAX_TOOL_CALLS:
                function_responses = []
                for function_call in response.function_calls:
                    tool_name = function_call.name
                    args = function_call.args or {}
                    
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
                        
                    # Protect against infinite identical calls
                    call_sig = f"{tool_name}:{str(args)}"
                    if call_sig in called_signatures:
                        result = {"error": "Duplicate tool call detected. Use the information already provided."}
                    elif tool_name not in self.ALLOWED_TOOLS:
                        result = {"error": f"Unknown tool requested: {tool_name}"}
                    else:
                        called_signatures.add(call_sig)
                        try:
                            func = self.ALLOWED_TOOLS[tool_name]
                            result = func(**args)
                        except Exception as e:
                            result = {"error": str(e)}
                            
                    function_responses.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response=result
                        )
                    )
                
                response = chat.send_message(function_responses)
                call_count += 1
                
            return {
                "answer": response.text,
                "tools_used": tools_used
            }
            
        except Exception as e:
            print(f"Copilot Error: {e}")
            return {
                "answer": "AI explanation is temporarily unavailable. The underlying reconciliation system and verified data remain available.",
                "tools_used": tools_used
            }
"""

with open("app/copilot.py", "w") as f:
    f.write(code)
