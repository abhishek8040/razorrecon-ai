from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from decimal import Decimal
import json

class Merchant(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Payment(SQLModel, table=True):
    id: str = Field(primary_key=True)
    external_id: str = Field(index=True)
    merchant_id: str = Field(index=True)
    amount: Decimal
    currency: str = Field(default="INR")
    payment_time: datetime = Field(index=True)
    customer_reference: Optional[str] = None
    order_reference: Optional[str] = None
    status: str
    metadata_json: Optional[str] = None
    
    @property
    def parsed_metadata(self) -> dict:
        return json.loads(self.metadata_json) if self.metadata_json else {}

class Settlement(SQLModel, table=True):
    id: str = Field(primary_key=True)
    external_id: str = Field(index=True)
    merchant_id: str = Field(index=True)
    settlement_amount: Decimal
    settlement_time: datetime = Field(index=True)
    reference: Optional[str] = None
    status: str
    metadata_json: Optional[str] = None
    
    @property
    def parsed_metadata(self) -> dict:
        return json.loads(self.metadata_json) if self.metadata_json else {}

class BankTransaction(SQLModel, table=True):
    id: str = Field(primary_key=True)
    external_id: str = Field(index=True)
    merchant_id: str = Field(index=True)
    amount: Decimal
    transaction_time: datetime = Field(index=True)
    bank_reference: Optional[str] = None
    description: Optional[str] = None
    type: str # 'CREDIT' or 'DEBIT'
    metadata_json: Optional[str] = None
    
    @property
    def parsed_metadata(self) -> dict:
        return json.loads(self.metadata_json) if self.metadata_json else {}

class ReconciliationRun(SQLModel, table=True):
    id: str = Field(primary_key=True)
    merchant_id: str = Field(index=True)
    status: str # 'RUNNING', 'COMPLETED', 'FAILED'
    total_records: int = 0
    auto_matched: int = 0
    ai_investigated: int = 0
    escalated: int = 0
    unresolved: int = 0
    accuracy: Optional[float] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReconciliationResult(SQLModel, table=True):
    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    source_record_type: str # 'PAYMENT', 'SETTLEMENT', 'BANK_TRANSACTION'
    source_record_id: str
    matched_record_id: Optional[str] = None
    result_type: str # 'MATCHED_EXACT', 'MATCHED_AFTER_FEE_ADJUSTMENT', 'AMBIGUOUS', 'UNRESOLVED', etc.
    confidence: float
    amount_difference: Decimal = Decimal("0.0")
    time_difference_seconds: Optional[int] = None
    reason_codes_json: Optional[str] = None
    explanation: Optional[str] = None
    decision_source: str # 'DETERMINISTIC', 'AI', 'HUMAN'
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def reason_codes(self) -> list:
        return json.loads(self.reason_codes_json) if self.reason_codes_json else []

class ExceptionRecord(SQLModel, table=True):
    __tablename__ = "exception"
    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    result_id: Optional[str] = Field(index=True)
    exception_type: str # 'MISSING_SETTLEMENT', 'AMOUNT_MISMATCH', etc.
    severity: str # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    description: str
    ai_analysis: Optional[str] = None
    recommended_action: Optional[str] = None
    status: str # 'OPEN', 'RESOLVED', 'REJECTED'
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AuditEvent(SQLModel, table=True):
    id: str = Field(primary_key=True)
    run_id: Optional[str] = Field(index=True)
    action: str
    entity_type: str
    entity_id: str
    actor: str # 'SYSTEM', 'AI', 'USER:xxxx'
    decision: Optional[str] = None
    reason: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def parsed_metadata(self) -> dict:
        return json.loads(self.metadata_json) if self.metadata_json else {}

class EvaluationRun(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset_name: str
    dataset_type: str # 'DEMO', 'HELDOUT'
    total_records: int
    correct_matches: int
    incorrect_matches: int
    unresolved_records: int
    precision: float
    recall: float
    accuracy: float
    auto_resolution_precision: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
