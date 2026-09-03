from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import Payment, ExceptionRecord, ReconciliationResult, ReconciliationRun
from datetime import datetime
from decimal import Decimal

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_run_reconciliation_api(client: TestClient, session: Session):
    # Setup data
    now = datetime.utcnow()
    session.add(Payment(id="pay_api_1", external_id="pay_api_1", merchant_id="m1", amount=Decimal("100.0"), payment_time=now, status="captured"))
    session.commit()
    
    response = client.post("/api/reconcile")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 1
    assert data["unresolved"] == 1

def test_ai_investigate_fallback(client: TestClient, session: Session):
    # This tests that an AI failure gracefully falls back
    now = datetime.utcnow()
    session.add(Payment(id="pay_api_2", external_id="pay_api_2", merchant_id="m1", amount=Decimal("100.0"), payment_time=now, status="captured"))
    session.add(ReconciliationRun(id="run_test", merchant_id="m1", status="COMPLETED"))
    
    res = ReconciliationResult(id="res_test", run_id="run_test", source_record_type="PAYMENT", source_record_id="pay_api_2", result_type="UNRESOLVED", confidence=0.0, decision_source="DETERMINISTIC")
    session.add(res)
    
    exc = ExceptionRecord(id="exc_test", run_id="run_test", result_id="res_test", exception_type="MISSING_SETTLEMENT", severity="LOW", description="Test", status="OPEN")
    session.add(exc)
    session.commit()
    
    # We don't have a real Gemini key configured in test env, so it will fail and trigger fallback
    response = client.post(f"/api/exceptions/{exc.id}/investigate")
    print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["investigation"]["decision"] == "REVIEW"
    assert "AI_FAILURE" in data["investigation"]["reason_codes"]

def test_ai_investigate_hard_failure(client: TestClient, session: Session, monkeypatch):
    # This tests the hard exception fallback in main.py
    now = datetime.utcnow()
    session.add(Payment(id="pay_api_3", external_id="pay_api_3", merchant_id="m1", amount=Decimal("100.0"), payment_time=now, status="captured"))
    session.add(ReconciliationRun(id="run_test_2", merchant_id="m1", status="COMPLETED"))
    
    res = ReconciliationResult(id="res_test_2", run_id="run_test_2", source_record_type="PAYMENT", source_record_id="pay_api_3", result_type="UNRESOLVED", confidence=0.0, decision_source="DETERMINISTIC")
    session.add(res)
    
    exc = ExceptionRecord(id="exc_test_2", run_id="run_test_2", result_id="res_test_2", exception_type="MISSING_SETTLEMENT", severity="LOW", description="Test", status="OPEN")
    session.add(exc)
    session.commit()
    
    def mock_investigate(*args, **kwargs):
        raise ValueError("Simulated AI timeout")
        
    import app.main
    monkeypatch.setattr(app.main.AIInvestigator, "investigate_exception", mock_investigate)

    response = client.post(f"/api/exceptions/{exc.id}/investigate")
    assert response.status_code == 200
    data = response.json()
    assert data["investigation"]["decision"] == "REVIEW"
    assert data["investigation"]["reason_codes"] == ["AI_FAILURE"]
