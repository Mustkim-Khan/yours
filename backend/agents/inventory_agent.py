"""
InventoryAgent - LangChain Agent Implementation
Reads medicine_master.csv, validates medicine existence, checks stock, returns pricing.
EMITS STANDARDIZED OUTPUT: {agent, decision, reason, evidence, message, next_agent}
Uses: gpt-5.2 (precision-critical)
"""

import os
from typing import Optional, Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from models.schemas import Decision, AgentOutput, Medicine
from utils.tracing import agent_trace, get_trace_id, create_non_traced_llm


# ============ MODEL CONFIG ============
MODEL_NAME = "gpt-5.2"  # Precision-critical agent
TEMPERATURE = 0.2


class InventoryAgent:
    """
    InventoryAgent - Medicine inventory management.
    Uses gpt-5.2 for precision.
    
    EMITS STANDARDIZED OUTPUT:
    {agent, decision, reason, evidence, message, next_agent}
    """

    def __init__(self, model_name: str = MODEL_NAME, temperature: float = TEMPERATURE):
        self.agent_name = "InventoryAgent"
        self.model_name = model_name
        # Use non-traced LLM to prevent LLM calls from appearing in traces
        self.llm = create_non_traced_llm(model_name, temperature)
        self._data_service = None

    def set_data_service(self, data_service):
        """Inject data service"""
        self._data_service = data_service

    @agent_trace("InventoryAgent", "gpt-5-mini")
    async def check_stock(
        self, 
        medicine_name: str, 
        form: Optional[str] = None,
        dosage: Optional[str] = None
    ) -> AgentOutput:
        """
        Check stock availability for a medicine.
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
        
        # Search for medicine
        medicines = self._data_service.search_medicine(medicine_name)
        
        if not medicines:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"Medicine '{medicine_name}' not found in inventory",
                evidence=[f"search_query={medicine_name}", "matches=0"],
                message=None,
                next_agent=None
            )
        
        # Get best match
        match = medicines[0]
        for med in medicines:
            if form and med.form.lower() == form.lower():
                match = med
                break
            if dosage and med.strength.lower() == dosage.lower():
                match = med
        
        # Check stock status
        if match.discontinued:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"{match.medicine_name} has been discontinued",
                evidence=[
                    f"medicine_id={match.medicine_id}",
                    f"medicine_name={match.medicine_name}",
                    f"discontinued=True"
                ],
                message=None,
                next_agent=None
            )
        
        if match.stock_level == 0:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"{match.medicine_name} is out of stock",
                evidence=[
                    f"medicine_id={match.medicine_id}",
                    f"medicine_name={match.medicine_name}",
                    f"stock_status=out_of_stock"
                ],
                message=None,
                next_agent=None
            )
        
        # In stock
        stock_status = "low_stock" if match.stock_level <= 20 else "in_stock"
        
        # Build detailed reason (2 lines as required)
        reason_line1 = f"{match.medicine_name} {match.strength} is available ({stock_status})."
        reason_line2 = f"Stock verified. Routing to PolicyAgent for compliance check."
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=f"{reason_line1} {reason_line2}",
            evidence=[
                f"medicine_id={match.medicine_id}",
                f"medicine_name={match.medicine_name}",
                f"strength={match.strength}",
                f"form={match.form}",
                f"stock_status={stock_status}",
                f"prescription_required={match.prescription_required}",
                f"max_quantity={match.max_quantity_per_order}"
            ],
            message=None,
            next_agent="PolicyAgent"  # ALWAYS route to PolicyAgent
        )

    @agent_trace("InventoryAgent", "gpt-5-mini")
    async def search(self, query: str) -> AgentOutput:
        """Search medicines by name."""
        if not self._data_service:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason="Data service not initialized",
                evidence=[],
                message=None,
                next_agent=None
            )
        
        medicines = self._data_service.search_medicine(query)
        
        if not medicines:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"No medicines found matching '{query}'",
                evidence=[f"query={query}", "results=0"],
                message=None,
                next_agent=None
            )
        
        match = medicines[0]
        alternatives = [m.medicine_name for m in medicines[1:4]]
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=f"Found {len(medicines)} result(s) for '{query}'",
            evidence=[
                f"medicine_id={match.medicine_id}",
                f"medicine_name={match.medicine_name}",
                f"strength={match.strength}",
                f"alternatives={alternatives}"
            ],
            message=None,
            next_agent=None
        )

    @agent_trace("InventoryAgent", "gpt-5-mini")
    async def get_pricing(self, medicine_id: str) -> AgentOutput:
        """Get pricing for a medicine."""
        if not self._data_service:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason="Data service not initialized",
                evidence=[],
                message=None,
                next_agent=None
            )
        
        medicine = self._data_service.get_medicine_by_id(medicine_id)
        
        if not medicine:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"Medicine {medicine_id} not found",
                evidence=[f"medicine_id={medicine_id}"],
                message=None,
                next_agent=None
            )
        
        # Mock pricing
        base_prices = {"Tablet": 5.00, "Capsule": 7.00, "Syrup": 12.00, "Injection": 25.00, "Inhaler": 35.00}
        unit_price = base_prices.get(medicine.form, 5.00)
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=f"Pricing found for {medicine.medicine_name}",
            evidence=[
                f"medicine_id={medicine_id}",
                f"unit_price=${unit_price:.2f}",
                f"form={medicine.form}"
            ],
            message=None,
            next_agent=None
        )

    def get_trace_id(self) -> Optional[str]:
        return get_trace_id()
