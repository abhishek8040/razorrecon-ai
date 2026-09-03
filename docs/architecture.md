# RazorRecon AI — Architecture

## System Overview

```
┌─────────────┐     REST API      ┌──────────────────────────────────────────────────┐
│  Next.js UI  │ ◄──────────────► │              FastAPI Backend                      │
│  (Port 3000) │                  │              (Port 8000)                          │
└─────────────┘                  │                                                    │
                                  │  ┌────────────────────────────────────────────┐   │
                                  │  │         Reconciliation Engine              │   │
                                  │  │                                            │   │
                                  │  │  Input → Validate → Exact Match            │   │
                                  │  │  → Fee Tolerance → Candidate Scoring       │   │
                                  │  │  → Exception Detection → Audit Log         │   │
                                  │  └────────────────────────────────────────────┘   │
                                  │                                                    │
                                  │  ┌──────────────┐  ┌───────────────────────────┐  │
                                  │  │ Policy Engine │  │    AI Investigator        │  │
                                  │  │  (Configurable│  │  (Gemini 2.5 Flash)      │  │
                                  │  │   thresholds) │  │  Structured JSON output   │  │
                                  │  └──────────────┘  │  MockAI fallback          │  │
                                  │                     └───────────────────────────┘  │
                                  │                                                    │
                                  │  ┌────────────────────────────────────────────┐   │
                                  │  │            SQLite Database                 │   │
                                  │  │  Payment | Settlement | BankTransaction   │   │
                                  │  │  ReconciliationRun | ReconciliationResult │   │
                                  │  │  ExceptionRecord | AuditEvent             │   │
                                  │  │  EvaluationRun                            │   │
                                  │  └────────────────────────────────────────────┘   │
                                  └──────────────────────────────────────────────────┘
```

## Data Flow

1. **Ingestion**: CSV upload or CLI seed creates Payment, Settlement, BankTransaction records
2. **Reconciliation**: Engine processes all records through deterministic pipeline
3. **AI Investigation**: Only called for ambiguous exceptions (not every record)
4. **Evaluation**: Compares results against ground-truth CSV data
5. **Human Review**: Operators resolve/reject flagged exceptions
6. **Audit**: Every action logged immutably

## AI Safety Architecture

```
Payment with no clear match
        │
        ▼
┌─────────────────────┐
│ Deterministic Engine │ ── Exact match found? ──► AUTO-RESOLVE ──► Audit
│ (always runs first)  │                                              
│                      │ ── Fee within 2%? ──────► AUTO-RESOLVE ──► Audit
│                      │
│                      │ ── No clear match ──────► Create Exception
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│   AI Investigator    │ ── Returns structured JSON with decision + confidence
│   (on-demand only)   │
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│   Policy Engine      │ ── Confidence >= 90%? No competing candidates?
│   (always enforced)  │    Amount within tolerance? ──► May auto-resolve
│                      │    Otherwise ──────────────────► HUMAN REVIEW
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│   Human Review       │ ── Operator inspects evidence ──► Resolve/Reject
└─────────────────────┘
        │
        ▼
    Audit Event Created
```

**Key principle**: AI NEVER directly modifies financial records. It provides recommendations that are filtered through the policy engine. The deterministic engine is always authoritative.
