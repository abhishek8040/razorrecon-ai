import os
import json
from decimal import Decimal
from typing import List, Dict, Any

class MockAIProvider:
    def investigate(self, payment, candidates, bank_candidates) -> dict:
        """ Returns a mock structured AI decision """
        # Very simple deterministic fallback logic pretending to be AI
        best_candidate = candidates[0] if candidates else None
        
        if not best_candidate:
            return {
                "decision": "UNRESOLVED",
                "confidence": 0.0,
                "reason_codes": ["NO_CANDIDATES"],
                "explanation": "No suitable candidate settlements found.",
                "recommended_action": "Manually verify payment gateway status"
            }
            
        diff = abs(payment.amount - best_candidate.settlement_amount)
        if diff > 0 and diff < payment.amount * Decimal("0.05"):
            return {
                "decision": "MATCH",
                "confidence": 0.92,
                "reason_codes": ["FEE_DISCREPANCY"],
                "explanation": "Amount discrepancy appears to be standard payment gateway fees.",
                "recommended_action": "Auto-resolve with fee adjustment"
            }
            
        return {
            "decision": "REVIEW",
            "confidence": 0.45,
            "reason_codes": ["AMOUNT_MISMATCH_TOO_HIGH"],
            "explanation": "The amount difference is too large to confidently attribute to fees.",
            "recommended_action": "Human review required"
        }

class LLMProvider:
    def __init__(self, provider_name: str, api_key: str):
        self.provider_name = provider_name
        self.api_key = api_key
        
    def investigate(self, payment, candidates, bank_candidates) -> dict:
        import google.genai as genai
        from google.genai import types
        from pydantic import BaseModel, Field
        
        class AIDecision(BaseModel):
            decision: str = Field(description="Must be exactly MATCH, REVIEW, or UNRESOLVED")
            confidence: float = Field(description="Confidence score between 0.0 and 1.0")
            reason_codes: List[str] = Field(description="List of reason codes explaining the discrepancy")
            explanation: str = Field(description="Detailed human-readable explanation of the reasoning")
            recommended_action: str = Field(description="Recommended action for the operator")

        client = genai.Client(api_key=self.api_key)
        
        prompt = f"""
        You are a highly analytical AI Financial Controller. 
        Your task is to investigate an ambiguous payment that the deterministic matching engine could not resolve.
        
        Payment Details:
        ID: {payment.id}
        Amount: {payment.amount} {payment.currency}
        Time: {payment.payment_time}
        Customer Ref: {payment.customer_reference}
        
        Candidate Settlements:
        """
        for i, s in enumerate(candidates):
            prompt += f"\n[{i+1}] ID: {s.id}, Amount: {s.settlement_amount}, Time: {s.settlement_time}, Ref: {s.reference}"
            
        prompt += "\n\nCandidate Bank Transactions:"
        for i, b in enumerate(bank_candidates):
            prompt += f"\n[{i+1}] ID: {b.id}, Amount: {b.amount}, Time: {b.transaction_time}, Ref: {b.bank_reference}"
            
        prompt += "\n\nAnalyze the data and return a JSON object with your decision and reasoning."

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIDecision,
                temperature=0.1
            ),
        )
        return json.loads(response.text)

def get_ai_provider():
    provider_name = os.environ.get("AI_PROVIDER", "mock").lower()
    if provider_name == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            return LLMProvider("gemini", api_key)
        else:
            print("WARNING: AI_PROVIDER is gemini but GEMINI_API_KEY is missing. Falling back to mock.")
    return MockAIProvider()

class AIInvestigator:
    def __init__(self):
        self.provider = get_ai_provider()
        
    def investigate_exception(self, payment, candidates, bank_candidates) -> dict:
        return self.provider.investigate(payment, candidates, bank_candidates)

class FinancialAssistant:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        
    def answer_query(self, query: str, context: dict) -> str:
        if not self.api_key or os.environ.get("AI_PROVIDER", "mock").lower() != "gemini":
            return "Mock Mode: Based on the metrics provided, the system is performing nominally. Connect a real GEMINI_API_KEY to enable full conversational Q&A."
            
        import google.genai as genai
        client = genai.Client(api_key=self.api_key)
        
        prompt = f"""
        You are a helpful AI Finance Assistant for RazorRecon AI.
        Answer the user's question accurately using ONLY the context provided.
        
        --- Context ---
        Total Payments: {context.get('total_payments')}
        Total Value: {context.get('total_value')}
        Open Exceptions: {context.get('open_exceptions')}
        Accuracy: {context.get('accuracy')}%
        Recent Exceptions: {json.dumps(context.get('recent_exceptions', []), default=str)}
        ---------------
        
        User Query: {query}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
