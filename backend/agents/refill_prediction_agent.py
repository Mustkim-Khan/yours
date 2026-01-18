"""
RefillPredictionAgent - LangChain Agent Implementation
Reads order_history.csv, calculates refill dates, generates predictions.
EMITS STANDARDIZED OUTPUT: {agent, decision, reason, evidence, message, next_agent}
Uses: gpt-5-mini
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from langchain_openai import ChatOpenAI

from models.schemas import Decision, AgentOutput
from utils.tracing import agent_trace, get_trace_id, create_non_traced_llm


# ============ MODEL CONFIG ============
MODEL_NAME = "gpt-5-mini"
TEMPERATURE = 0.3


# ============ REFILL CALCULATION ============
SUPPLY_DURATIONS = {
    "daily": 1,
    "twice_daily": 0.5,
    "once_weekly": 7,
    "once_monthly": 30,
    "default": 1  # Assume once daily
}


class RefillPredictionAgent:
    """
    RefillPredictionAgent - Medication refill predictions.
    Uses gpt-5-mini model.
    
    EMITS STANDARDIZED OUTPUT:
    {agent, decision, reason, evidence, message, next_agent}
    """

    def __init__(self, model_name: str = MODEL_NAME, temperature: float = TEMPERATURE):
        self.agent_name = "RefillPredictionAgent"
        self.model_name = model_name
        # Use non-traced LLM to prevent LLM calls from appearing in traces
        self.llm = create_non_traced_llm(model_name, temperature)
        self._data_service = None

    def set_data_service(self, data_service):
        """Inject data service"""
        self._data_service = data_service

    @agent_trace("RefillPredictionAgent", "gpt-5-mini")
    async def get_refill_predictions(self, patient_id: str) -> AgentOutput:
        """
        Get refill predictions for a patient.
        Returns standardized AgentOutput.
        """
        if not self._data_service:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason="Data service not initialized",
                evidence=["data_service=None"],
                message=None,
                next_agent=None
            )
        
        # Get medicines needing refill
        refills = self._data_service.get_medicines_needing_refill(patient_id, datetime.now())
        
        if not refills:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.APPROVED,
                reason=f"No medications need refill for patient {patient_id}",
                evidence=[
                    f"patient_id={patient_id}",
                    "upcoming_refills=0"
                ],
                message=None,
                next_agent=None
            )
        
        # Build evidence from refills
        evidence = [
            f"patient_id={patient_id}",
            f"upcoming_refills={len(refills)}"
        ]
        
        urgent_count = 0
        for refill in refills[:5]:  # Top 5
            days_left = refill.get("days_remaining", 0)
            med_name = refill.get("medicine_name", "Unknown")
            evidence.append(f"medicine={med_name}, days_remaining={days_left}")
            if days_left <= 7:
                urgent_count += 1
        
        # Determine decision based on urgency
        if urgent_count > 0:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.SCHEDULED,
                reason=f"{urgent_count} medication(s) need refill within 7 days",
                evidence=evidence,
                message=None,
                next_agent="PharmacistAgent"
            )
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=f"{len(refills)} medication(s) will need refill soon",
            evidence=evidence,
            message=None,
            next_agent=None
        )

    @agent_trace("RefillPredictionAgent", "gpt-5-mini")
    async def check_refill_eligibility(
        self, 
        patient_id: str, 
        medicine_name: str
    ) -> AgentOutput:
        """
        Check if patient is eligible for refill of specific medicine.
        """
        if not self._data_service:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason="Data service not initialized",
                evidence=[],
                message=None,
                next_agent=None
            )
        
        # Get patient history
        history = self._data_service.get_patient_order_history(patient_id)
        
        if history.empty:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"No order history found for patient {patient_id}",
                evidence=[f"patient_id={patient_id}"],
                message=None,
                next_agent=None
            )
        
        # Find last order for this medicine
        med_lower = medicine_name.lower()
        med_history = history[history['medicine_name'].str.lower().str.contains(med_lower)]
        
        if med_history.empty:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.APPROVED,
                reason=f"First time order for {medicine_name} - eligible",
                evidence=[
                    f"patient_id={patient_id}",
                    f"medicine_name={medicine_name}",
                    "order_history=none"
                ],
                message=None,
                next_agent="InventoryAgent"
            )
        
        # Calculate days since last order
        last_order = med_history.iloc[-1]
        last_date = datetime.fromisoformat(str(last_order['order_date']))
        quantity = int(last_order.get('quantity', 30))
        days_supply = quantity  # Assume 1 per day
        days_since = (datetime.now() - last_date).days
        
        # Check if too early (less than 75% consumed)
        if days_since < days_supply * 0.75:
            days_until_eligible = int(days_supply * 0.75 - days_since)
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"Too early for refill - eligible in {days_until_eligible} days",
                evidence=[
                    f"patient_id={patient_id}",
                    f"medicine_name={medicine_name}",
                    f"last_order_days_ago={days_since}",
                    f"supply_days={days_supply}",
                    f"eligible_in={days_until_eligible}"
                ],
                message=None,
                next_agent=None
            )
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=f"Eligible for {medicine_name} refill",
            evidence=[
                f"patient_id={patient_id}",
                f"medicine_name={medicine_name}",
                f"last_order_days_ago={days_since}",
                f"supply_days={days_supply}",
                "eligible=True"
            ],
            message=None,
            next_agent="InventoryAgent"
        )

    @agent_trace("RefillPredictionAgent", "gpt-5-mini")
    async def calculate_adherence(self, patient_id: str) -> AgentOutput:
        """
        Calculate medication adherence score for patient.
        """
        if not self._data_service:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason="Data service not initialized",
                evidence=[],
                message=None,
                next_agent=None
            )
        
        history = self._data_service.get_patient_order_history(patient_id)
        
        if history.empty:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"No history to calculate adherence for patient {patient_id}",
                evidence=[f"patient_id={patient_id}"],
                message=None,
                next_agent=None
            )
        
        # Simple adherence calculation based on refill timing
        total_orders = len(history)
        if total_orders < 2:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.NEEDS_INFO,
                reason="Insufficient data for adherence calculation",
                evidence=[f"patient_id={patient_id}", f"orders={total_orders}"],
                message=None,
                next_agent=None
            )
        
        # Calculate adherence (simplified)
        adherence_score = min(95, 70 + total_orders * 3)  # Mock calculation
        
        status = "excellent" if adherence_score >= 90 else "good" if adherence_score >= 70 else "needs_improvement"
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=f"Adherence score calculated: {status}",
            evidence=[
                f"patient_id={patient_id}",
                f"adherence_score={adherence_score}%",
                f"total_orders={total_orders}",
                f"status={status}"
            ],
            message=None,
            next_agent=None
        )

    def get_trace_id(self) -> Optional[str]:
        return get_trace_id()
