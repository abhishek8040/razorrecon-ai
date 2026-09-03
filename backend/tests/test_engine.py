import pytest
from sqlmodel import Session
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from app.engine import ReconciliationEngine
from app.models import Payment, Settlement, BankTransaction, ReconciliationResult, ExceptionRecord

def test_engine_exact_match(session: Session):
    # Setup 3-way exact match
    p_id = "pay_1"
    s_id = "setl_1"
    b_id = "bank_1"
    
    now = datetime.utcnow()
    
    session.add(Payment(id=p_id, external_id=p_id, merchant_id="m1", amount=Decimal("100.0"), payment_time=now, status="captured"))
    session.add(Settlement(id=s_id, external_id=s_id, merchant_id="m1", settlement_amount=Decimal("100.0"), settlement_time=now + timedelta(days=1), reference=p_id, status="processed"))
    session.add(BankTransaction(id=b_id, external_id=b_id, merchant_id="m1", amount=Decimal("100.0"), transaction_time=now + timedelta(days=1, hours=2), bank_reference=s_id, type="CREDIT"))
    session.commit()
    
    engine = ReconciliationEngine(session, "run_1")
    engine.run()
    
    res = session.query(ReconciliationResult).filter(ReconciliationResult.source_record_id == p_id).first()
    assert res is not None
    assert res.result_type == "MATCHED_EXACT"
    assert res.decision_source == "DETERMINISTIC"
    assert res.explanation == "Exact 3-way match on reference and amount."

def test_engine_fee_adjustment(session: Session):
    p_id = "pay_2"
    s_id = "setl_2"
    now = datetime.utcnow()
    
    session.add(Payment(id=p_id, external_id=p_id, merchant_id="m1", amount=Decimal("100.0"), payment_time=now, status="captured"))
    # 2% fee
    session.add(Settlement(id=s_id, external_id=s_id, merchant_id="m1", settlement_amount=Decimal("98.0"), settlement_time=now + timedelta(days=1), reference=p_id, status="processed"))
    session.commit()
    
    engine = ReconciliationEngine(session, "run_2")
    engine.run()
    
    res = session.query(ReconciliationResult).filter(ReconciliationResult.source_record_id == p_id).first()
    assert res is not None
    assert res.result_type == "MATCHED_AFTER_FEE_ADJUSTMENT"
    
def test_engine_idempotency(session: Session):
    p_id = "pay_3"
    s_id = "setl_3"
    now = datetime.utcnow()
    
    session.add(Payment(id=p_id, external_id=p_id, merchant_id="m1", amount=Decimal("100.0"), payment_time=now, status="captured"))
    session.add(Settlement(id=s_id, external_id=s_id, merchant_id="m1", settlement_amount=Decimal("100.0"), settlement_time=now + timedelta(days=1), reference=p_id, status="processed"))
    session.commit()
    
    engine1 = ReconciliationEngine(session, "run_3")
    engine1.run()
    
    engine2 = ReconciliationEngine(session, "run_4")
    engine2.run()
    
    results = session.query(ReconciliationResult).filter(ReconciliationResult.source_record_id == p_id).all()
    # Should only have 1 result despite two runs
    assert len(results) == 1
    assert results[0].run_id == "run_4"
    
def test_engine_missing_settlement(session: Session):
    p_id = "pay_4"
    now = datetime.utcnow()
    session.add(Payment(id=p_id, external_id=p_id, merchant_id="m1", amount=Decimal("100.0"), payment_time=now, status="captured"))
    session.commit()
    
    engine = ReconciliationEngine(session, "run_5")
    engine.run()
    
    res = session.query(ReconciliationResult).filter(ReconciliationResult.source_record_id == p_id).first()
    assert res.result_type == "UNRESOLVED"
    
    exc = session.query(ExceptionRecord).filter(ExceptionRecord.result_id == res.id).first()
    assert exc.exception_type == "MISSING_SETTLEMENT"
