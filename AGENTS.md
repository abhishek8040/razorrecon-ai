# AGENTS.md

## Agent Instructions for RazorRecon AI

**Context:**
This is an AI-assisted financial reconciliation controller for a hackathon. The product must work realistically with synthetic data.

**Architecture:**
- **Frontend**: Next.js (TypeScript, App Router), Tailwind CSS.
- **Backend**: Python 3, FastAPI, SQLModel.
- **Database**: SQLite (dev) / PostgreSQL (prod).

**Key Rules:**
1. **Never use AI to determine truth.** The deterministic matching engine is authoritative. AI is only used to investigate ambiguous cases (e.g. fee mismatches) and its decisions are verified by a policy engine before auto-resolution.
2. **Do not hardcode metrics.** The UI must show calculated metrics (accuracy, match rate) from actual data in the `EvaluationRun` and `ReconciliationRun` tables.
3. **Graceful Fallback:** If the LLM key is missing or the API fails, the backend must use a deterministic fallback (MockAIProvider) that routes ambiguous cases to HUMAN_REVIEW.
4. **Data:** Use the synthetic data generator (`backend/app/cli.py`) to create at least 1,000 records.
5. **Simplicity:** Keep the system as a monolithic backend and single Next.js app. Do not add microservices, queues, or unnecessary abstractions.
