# AI Safety in RazorRecon AI

## Core Principle

**AI must NEVER be the source of financial truth.**

The deterministic matching engine and configurable policy rules are authoritative. AI serves only as an investigation and reasoning layer for ambiguous cases.

## Safety Boundaries

### What AI CAN do:
- Investigate ambiguous exceptions where deterministic matching failed
- Provide structured recommendations (MATCH / REVIEW / UNRESOLVED)
- Explain discrepancies in natural language
- Answer questions about reconciliation data using verified metrics
- Classify exception types and suggest root causes

### What AI CANNOT do:
- Directly modify financial records
- Override policy engine decisions
- Auto-resolve transactions without policy approval
- Access external financial systems
- Move money or initiate transactions

## Failure Handling

| Scenario | Behavior |
|----------|----------|
| API key missing | MockAIProvider returns deterministic fallback |
| API timeout | Exception caught, fallback response returned |
| Malformed JSON response | Fallback to REVIEW with AI_FAILURE reason code |
| Rate limit exceeded | Fallback response, audit event logged |
| Invalid confidence score | Clamped to [0.0, 1.0] range |

## Policy Engine Constraints

Auto-resolution is only permitted when ALL conditions are met:

1. AI confidence ≥ `MIN_AUTO_RESOLUTION_CONFIDENCE` (default: 90%)
2. Amount difference ≤ `MAX_AMOUNT_TOLERANCE_PERCENT` (default: 2%)
3. No competing candidates
4. No contradictory evidence
5. Settlement within `MAX_TIME_WINDOW_DAYS` (default: 5 days)

If ANY condition fails → **HUMAN REVIEW** is required.

## Audit Trail

Every AI action is logged with:
- Timestamp
- Run ID
- Action type (AI_INVESTIGATION, AI_FAILURE)
- Entity reference
- Decision made
- Reasoning provided
- Actor (AI vs SYSTEM vs USER)

The audit trail is immutable and chronologically ordered.
