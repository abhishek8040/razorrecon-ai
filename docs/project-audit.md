# RazorRecon AI — Project Audit

## A. Existing Architecture

| Layer | Technology | Status |
|-------|-----------|--------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, Recharts, Lucide | Working |
| Backend | Python 3, FastAPI, SQLModel | Working |
| Database | SQLite (razorrecon.db, ~3.7MB) | Working |
| AI | Google GenAI SDK (gemini-2.5-flash) + MockAIProvider fallback | Working |
| Data Gen | Python CLI (cli.py) with seed-based generation | Working |

**Frontend-Backend Communication:** REST API over HTTP, CORS open to `*`. `fetchApi()` helper in `lib/api.ts`.

---

## B. What is Genuinely Working

1. ✅ Database persistence is real (SQLite with SQLModel ORM)
2. ✅ Synthetic data generator produces ~1000 records with controlled anomalies (seed=42)
3. ✅ Held-out data generator exists (seed=99, 500 records)
4. ✅ Exact matching by reference + amount works
5. ✅ Fee-tolerance matching (2% policy) works
6. ✅ Unresolved payments create ExceptionRecords
7. ✅ AI investigation endpoint calls Gemini with structured output schema
8. ✅ MockAIProvider fallback works when no API key
9. ✅ Audit events are created for match/escalate/investigate actions
10. ✅ Evaluation engine compares results against CSV ground truth
11. ✅ CSV upload ingestion works
12. ✅ Dashboard metrics come from real database queries
13. ✅ All 8 frontend pages render and connect to backend

---

## C. What is Partially Implemented

1. ⚠️ **Evaluation engine** — Runs only against "demo" CSV. Uses relative path `../data/demo/` which is fragile. Doesn't compute `processing_time_ms` or `records/second`. `accuracy` field on ReconciliationRun is always `null`.
2. ⚠️ **Exception details** — Shows exception type and description but NOT the source payment, candidate settlements, amount difference, or policy reasoning. No "why not auto-resolved?" explanation.
3. ⚠️ **Transactions page** — Shows payment + match type but no click-through to settlement details, bank transaction, or reconciliation lineage.
4. ⚠️ **Q&A context** — Sends only 5 fields to Gemini. Lacks: auto-match rate, exception breakdown, unreconciled amount, processing time. No deterministic fallback for structured queries.
5. ⚠️ **Engine statistics** — `ai_investigated` counter is always 0. `processing_time_ms` is always null.
6. ⚠️ **Human review** — No resolve/reject buttons on exceptions. No notes. No status change workflow.

---

## D. What is Fake/Hardcoded/Demo-only

1. ❌ **Exception type detection is shallow** — Only two types: `AMBIGUOUS_MATCH` (has candidates) and `MISSING_SETTLEMENT` (no candidates). No detection of: DUPLICATE, AMOUNT_MISMATCH, FEE_MISMATCH, REFERENCE_MISMATCH, DELAYED_SETTLEMENT, PARTIAL_SETTLEMENT. The data generator creates all these anomalies but the engine doesn't classify them.
2. ❌ **Bank transactions are NEVER used in reconciliation** — The engine only matches Payments↔Settlements. BankTransaction table is populated but completely ignored during matching. This is a THREE-WAY reconciliation product that only does TWO-WAY.
3. ❌ **Evaluation `dataset_type` is always "DEMO"** — Never set to "HELDOUT". No API endpoint to run held-out evaluation separately.
4. ❌ **AI investigation candidate logic is broken** — `candidates = [s for s in settlements if s.reference == p.id]` only finds settlements that already reference the payment. For MISSING_SETTLEMENT exceptions (where no settlement references the payment), this always returns empty list, so AI always gets zero candidates and says "UNRESOLVED" (which I just verified above).
5. ❌ **`accuracy` on ReconciliationRun is always null** — Never populated.
6. ❌ **`processing_time_ms`** — Never measured or stored.
7. ❌ **Multiple reconciliation runs create duplicate results** — Running reconciliation multiple times on the same data creates new results for every payment each time, inflating exception counts (currently 1183 exceptions for 1005 payments, because multiple runs accumulated).

---

## E. What is Missing

1. **No "Why not auto-resolved?" explanation** — Critical for judges
2. **No transaction detail/lineage view** — Cannot trace Payment→Settlement→Bank→Signals→Decision
3. **No human review workflow** — Cannot resolve/reject exceptions
4. **No exception filtering** — No filter by type, severity, status, run
5. **No held-out evaluation API endpoint** — Cannot trigger from UI
6. **No duplicate detection** — Data generator creates duplicates, engine ignores them
7. **No processing time measurement** — `records/second` metric missing
8. **No bank transaction reconciliation** — 3-way match never happens
9. **No Settings page** (linked in sidebar but no page exists — will 404)
10. **No tests** — `pytest` is in requirements but no test files exist
11. **No `.gitignore`** — `venv/`, `__pycache__/`, `.env`, `razorrecon.db` would be committed
12. **No Dockerfile/docker-compose**

---

## F. Critical Bugs

1. **🔴 Multiple runs accumulate duplicate results** — Each reconciliation run creates new results for ALL payments, never checking if they were already matched. Running 3 times = 3x the exceptions. This makes metrics unreliable.
2. **🔴 AI investigation always gets empty candidates for MISSING_SETTLEMENT** — The candidate filter `s.reference == p.id` defeats the purpose. For missing settlements the whole point is to find *possible* candidates by fuzzy match.
3. **🔴 Evaluation path `../data/demo/` is relative to CWD** — Breaks depending on where you start uvicorn.
4. **🔴 Settings page link in sidebar leads to 404** — `/settings` route doesn't exist.
5. **🔴 `run.dict()` is deprecated in Pydantic v2** — Should use `model_dump()`.

---

## G. UX Weaknesses

1. No active-link highlighting in sidebar
2. No loading skeletons (just "Loading..." text)
3. No empty state illustrations
4. Dashboard chart shows 0 if no run exists (just blank)
5. No error display to user (failures silently caught in console)
6. Transactions table shows `0E-10` for amount_difference (Decimal serialization)
7. No pagination on exceptions (1183 all loaded at once)
8. Exception list shows internal IDs like `exc_6fef132a2da2` — not human-readable
9. No "Demo Data" vs "Custom Data" labeling
10. No dark mode support despite CSS variables being set up for it

---

## H. AI Weaknesses

1. AI gets no actual evidence for MISSING_SETTLEMENT — always says "no candidates provided"
2. No error handling for Gemini API failures (timeout, rate limit, malformed JSON)
3. No AI confidence thresholds in policy
4. AI decision doesn't update the ReconciliationResult — only updates ExceptionRecord fields
5. Q&A context is minimal — no breakdown by exception type, match rate, unreconciled amount

---

## I. Evaluation Weaknesses

1. Only evaluates against demo dataset CSV, not held-out
2. No `processing_time_ms` or `records/second`
3. `auto_resolution_precision` is just copied from `precision` (comment: "Simplified for hackathon")
4. No way to trigger held-out evaluation from UI
5. Evaluation total_records comes from CSV row count, not from actual records processed

---

## J. Security/Reliability Weaknesses

1. CORS is `allow_origins=["*"]` — acceptable for hackathon
2. No input validation on CSV upload (malformed CSV will crash with unhelpful error)
3. API key in `.env` file (acceptable for hackathon, but `.env` not in `.gitignore`)
4. No rate limiting
5. No authentication (acceptable for hackathon demo)

---

## K. Deployment Weaknesses

1. No Dockerfile
2. No `.gitignore`
3. No production build test verification
4. SQLite database committed to repo (3.7MB)
5. `venv/` directory in repo

---

## L. Hackathon Selection Risks

1. **Bank transactions unused = 2-way not 3-way reconciliation** — Judges will notice
2. **No "Why not auto-resolved?" = missing key fintech feature**
3. **Running reconciliation multiple times breaks everything** — A curious judge will click it twice
4. **1183 exceptions for 1005 payments looks broken** — Data integrity issue visible to judges
5. **Exception investigation always says "no candidates" for missing settlements**
6. **No held-out evaluation button** — Judges can't verify accuracy claims independently

---

## Priority Table

### 🔴 CRITICAL (Must fix)

| # | Issue | Impact |
|---|-------|--------|
| C1 | Multiple runs create duplicate results — idempotency | Breaks metrics, looks broken to judge |
| C2 | AI investigation gets empty candidates for MISSING_SETTLEMENT | AI looks useless |
| C3 | Bank transactions never used in reconciliation | Product claims 3-way but does 2-way |
| C4 | Settings page 404 | Judge clicks, app breaks |
| C5 | No "Why not auto-resolved?" explanation | Missing key fintech feature |
| C6 | Exception types too shallow (only 2 types) | Doesn't match data generator's anomaly types |

### 🟠 HIGH (Strong improvement)

| # | Issue | Impact |
|---|-------|--------|
| H1 | No transaction detail/lineage view | Judge can't trace decisions |
| H2 | No human review workflow (resolve/reject) | Incomplete exception lifecycle |
| H3 | No held-out evaluation endpoint + UI | Can't demonstrate evaluation rigor |
| H4 | Processing time not measured | Missing key metric |
| H5 | AI error handling missing | Single API failure crashes investigation |
| H6 | Q&A context too thin | AI answers will be generic |
| H7 | `.gitignore` missing | DB, venv, pycache would be committed |

### 🟡 MEDIUM (Useful)

| # | Issue | Impact |
|---|-------|--------|
| M1 | No exception filtering | UX weakness |
| M2 | No active sidebar link | Minor UX |
| M3 | Decimal serialization shows `0E-10` | Visual bug |
| M4 | No tests | Technical credibility |
| M5 | No pagination on large lists | Performance for judges |

### 🟢 LOW (Cosmetic)

| # | Issue | Impact |
|---|-------|--------|
| L1 | Loading states are text only | Minor polish |
| L2 | No Dockerfile | Nice-to-have |
| L3 | Dark mode CSS variables unused | Minor |
