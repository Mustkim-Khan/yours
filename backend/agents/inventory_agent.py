"""
InventoryAgent - LangChain Agent Implementation
Reads medicine_master.csv, validates medicine existence, checks stock, returns pricing.
EMITS STANDARDIZED OUTPUT: {agent, decision, reason, evidence, message, next_agent}
Uses: gpt-5-mini (fast for inventory lookups)
"""

import os
import json
from typing import Optional, Dict, Any, List

from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from models.schemas import Decision, AgentOutput, Medicine
from utils.tracing import agent_trace, get_trace_id, create_non_traced_llm


# ============ MODEL CONFIG ============
MODEL_NAME = "gpt-5-mini"  # Fast model for inventory lookups
TEMPERATURE = 0.3


class InventoryAgent:
    """
    InventoryAgent - Medicine inventory management.
    Uses gpt-5-mini for fast inventory responses.
    
    EMITS STANDARDIZED OUTPUT:
    {agent, decision, reason, evidence, message, next_agent}
    """

    def __init__(self, model_name: str = MODEL_NAME, temperature: float = TEMPERATURE):
        self.agent_name = "InventoryAgent"
        self.model_name = model_name
        self.temperature = temperature
        # Direct OpenAI client for LLM calls
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Legacy LangChain LLM (for compatibility)
        self.llm = create_non_traced_llm(model_name, temperature)
        self._data_service = None

    def set_data_service(self, data_service):
        """Inject data service"""
        self._data_service = data_service

    async def _generate_reasoning(self, context: str, decision: str) -> str:
        """
        Generate a concise, logical reasoning string using the LLM.
        This provides 'Chain of Thought' visibility in traces.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a pharmacy inventory expert. Verify the decision logic. Output a concise justification (max 15 words)."
                    },
                    {
                        "role": "user",
                        "content": f"Context: {context}\nDecision: {decision}\nReasoning:"
                    }
                ],
                # temperature=0.1,  # Removed to avoid "unsupported value" error
                # max_tokens=200 # Removed to avoid "unsupported_parameter" error
                # max_completion_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"InventoryAgent Reasoning Error: {e}")
            return f"{decision} based on inventory data (Fallback: {str(e)})"


    @agent_trace("InventoryAgent", "gpt-5-mini")
    async def check_stock(
        self, 
        medicine_name: str = "", 
        form: Optional[str] = None,
        dosage: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None
    ) -> AgentOutput:
        """
        Check stock availability for a medicine or list of medicines.
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
        
        # Normalize input to list of items
        check_items = []
        if items:
            check_items = items
        elif medicine_name:
            check_items = [{"medicine_name": medicine_name, "form": form, "dosage": dosage}]
            
        if not check_items:
             return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason="No medicines provided for stock check",
                evidence=[],
                message="I couldn't identify which medicine you'd like to check.",
                next_agent=None
            )

        results = []
        all_in_stock = True
        any_discontinued = False
        discontinued_names = []
        out_of_stock_names = []
        
        evidence = []
        
        for item in check_items:
            med_name = item.get("medicine_name", "")
            item_form = item.get("form")
            item_dosage = item.get("dosage")
            
            # Search for medicine
            medicines = self._data_service.search_medicine(med_name)
            
            if not medicines:
                out_of_stock_names.append(med_name)
                all_in_stock = False
                continue
            
            # Get best match
            match = medicines[0]
            for med in medicines:
                if item_form and med.form.lower() == item_form.lower():
                    match = med
                    break
                if item_dosage and med.strength.lower() == item_dosage.lower():
                    match = med
            
            # Check stock status
            if match.discontinued:
                any_discontinued = True
                discontinued_names.append(match.medicine_name)
                all_in_stock = False
            elif match.stock_level == 0:
                out_of_stock_names.append(match.medicine_name)
                all_in_stock = False
            
            # Add to evidence if successful or failed
            stock_status = "out_of_stock" if match.stock_level == 0 else "in_stock"
            if match.discontinued: stock_status = "discontinued"
            
            # Append item-specific evidence for Orchestrator to parse later
            item_evidence = {
                "medicine_id": match.medicine_id,
                "medicine_name": match.medicine_name,
                "strength": match.strength,
                "form": match.form,
                "stock_status": stock_status,
                "prescription_required": match.prescription_required,
                "max_quantity": match.max_quantity_per_order
            }
            evidence.append(f"item_data={json.dumps(item_evidence)}")
            
            # Also add legacy evidence for first item
            if not results:
                evidence.append(f"medicine_id={match.medicine_id}")
                evidence.append(f"medicine_name={match.medicine_name}")
                evidence.append(f"strength={match.strength}")
                evidence.append(f"form={match.form}")
                evidence.append(f"stock_status={stock_status}")
                evidence.append(f"prescription_required={match.prescription_required}")
            
            results.append(match)

        # Decision Logic
        if any_discontinued:
            names = ", ".join(discontinued_names)
            context = f"{names} checked. Discontinued. Cannot fulfill."
            reason = await self._generate_reasoning(context, "REJECTED")
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=reason,
                evidence=evidence,
                message=f"I'm sorry, but {names} has been discontinued.",
                next_agent=None
            )
            
        if not all_in_stock:
            names = ", ".join(out_of_stock_names)
            context = f"{names} out of stock. Cannot fulfill complete order."
            reason = await self._generate_reasoning(context, "REJECTED")
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=reason,
                evidence=evidence,
                message=f"I'm sorry, but {names} is currently out of stock.",
                next_agent=None
            )
            
        # All items valid
        med_names = ", ".join([m.medicine_name for m in results])
        context = f"Stock verified for {len(results)} items: {med_names}. All available."
        reason = await self._generate_reasoning(context, "APPROVED")
        
        # Generate dynamic message
        llm_message = await self._generate_message(
            context=f"Medicines: {med_names}, Status: All In Stock",
            task="Confirm availability for multi-item order"
        )
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=reason,
            evidence=evidence,
            message=llm_message,
            next_agent="PolicyAgent"
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
            context = f"Search query '{query}' yielded 0 results in inventory."
            reason = await self._generate_reasoning(context, "REJECTED")
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=reason,
                evidence=[f"query={query}", "results=0"],
                message=None,
                next_agent=None
            )
        
        match = medicines[0]
        alternatives = [m.medicine_name for m in medicines[1:4]]
        
        context = f"Found {len(medicines)} results for '{query}'. Top match: {match.medicine_name}."
        reason = await self._generate_reasoning(context, "APPROVED")
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=reason,
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
            context = f"Medicine ID {medicine_id} not found in database for pricing."
            reason = await self._generate_reasoning(context, "REJECTED")
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=reason,
                evidence=[f"medicine_id={medicine_id}"],
                message=None,
                next_agent=None
            )
        
        # Mock pricing
        base_prices = {"Tablet": 5.00, "Capsule": 7.00, "Syrup": 12.00, "Injection": 25.00, "Inhaler": 35.00}
        unit_price = base_prices.get(medicine.form, 5.00)
        
        context = f"Pricing found for {medicine.medicine_name} ({medicine.form}): ${unit_price}."
        reason = await self._generate_reasoning(context, "APPROVED")
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=reason,
            evidence=[
                f"medicine_id={medicine_id}",
                f"unit_price=${unit_price:.2f}",
                f"form={medicine.form}"
            ],
            message=None,
            next_agent=None
        )

    async def _generate_message(self, context: str, task: str) -> str:
        """
        Generate a professional message using gpt-5-mini.
        Used for creating natural language responses for inventory queries.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful pharmacy inventory assistant. Generate concise, professional responses. Keep responses under 50 words."
                    },
                    {
                        "role": "user",
                        "content": f"Context: {context}\nTask: {task}\nGenerate a brief response:"
                    }
                ],
                temperature=self.temperature,
                max_completion_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            # Fallback to simple message on error
            return f"Inventory check complete. {task}"

    def get_trace_id(self) -> Optional[str]:
        return get_trace_id()

