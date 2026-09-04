from decimal import Decimal
from datetime import datetime
import pytest

from app.models import Payment, ReconciliationRun, ReconciliationResult, ExceptionRecord, AuditEvent
from app.copilot import CopilotTools, FinanceCopilot
from sqlmodel import Session, create_engine, SQLModel

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_copilot_metrics(session: Session):
    tools = CopilotTools(session)
    run = ReconciliationRun(id="run1", merchant_id="global", status="completed", total_records=1, auto_matched=1, escalated=0)
    session.add(run)
    p = Payment(id="p1", external_id="p1", amount=Decimal("100"), merchant_id="m1", status="captured", payment_time=datetime.utcnow())
    session.add(p)
    res = ReconciliationResult(id="res1", run_id="run1", source_record_id="p1", source_record_type="PAYMENT", result_type="MATCHED_3_WAY", confidence=1.0, amount_difference=Decimal("0"), time_difference_seconds=0, decision_source="DETERMINISTIC")
    session.add(res)
    session.commit()
    
    metrics = tools.get_reconciliation_metrics()
    assert metrics["total_payments"] == 1
    assert metrics["matched_3_way"] == 1
    assert metrics["total_value"] == 100.0

def test_copilot_transaction_details(session: Session):
    tools = CopilotTools(session)
    p = Payment(id="p1", external_id="p1", amount=Decimal("100"), merchant_id="m1", status="captured", payment_time=datetime.utcnow())
    session.add(p)
    session.commit()
    
    details = tools.get_transaction_details("p1")
    assert details["found"] is True
    assert details["payment"]["id"] == "p1"
    
    not_found = tools.get_transaction_details("p999")
    assert not_found["found"] is False

def test_copilot_mock_fallback(session: Session):
    import os
    os.environ["AI_PROVIDER"] = "mock"
    copilot = FinanceCopilot(session)
        
    res = copilot.answer_query("What is the exception rate?")
    assert "Mock Mode" in res["answer"]
    assert res["tools_used"] == []
