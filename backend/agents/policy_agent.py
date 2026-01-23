"""
PolicyAgent - LangChain Agent Implementation
Enforces prescription rules, quantity limits, blocks unsafe requests.
EMITS STANDARDIZED OUTPUT: {agent, decision, reason, evidence, message, next_agent}
Uses: gpt-5.2 (precision-critical for safety)
"""

import os
from typing import Optional, Dict, Any, List

from langchain_openai import ChatOpenAI

from models.schemas import Decision, AgentOutput
from utils.tracing import agent_trace, get_trace_id, create_non_traced_llm


# ============ MODEL CONFIG ============
MODEL_NAME = "gpt-5.2"  # Precision-critical for safety
TEMPERATURE = 0.1


# ============ POLICY DATA ============
CONTROLLED_SUBSTANCES = [
    "morphine", "tramadol", "diazepam", "alprazolam", 
    "pregabalin", "hydrocodone", "oxycodone", "codeine"
]

QUANTITY_LIMITS = {
    "controlled": 30,
    "antibiotic": 21,
    "default": 90
}

DRUG_INTERACTIONS = {
    ("warfarin", "aspirin"): {"severity": "severe", "warning": "Increased bleeding risk"},
    ("metformin", "alcohol"): {"severity": "moderate", "warning": "Risk of lactic acidosis"},
    ("lisinopril", "potassium"): {"severity": "moderate", "warning": "Risk of hyperkalemia"},
}


class PolicyAgent:
    """
    PolicyAgent - Pharmacy policy enforcement.
    Uses gpt-5.2 for precision-critical safety decisions.
    
    EMITS STANDARDIZED OUTPUT:
    {agent, decision, reason, evidence, message, next_agent}
    """

    def __init__(self, model_name: str = MODEL_NAME, temperature: float = TEMPERATURE):
        self.agent_name = "PolicyAgent"
        self.model_name = model_name
        self.temperature = temperature
        # Direct OpenAI client for reasoning generation
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Use non-traced LLM to prevent LLM calls from appearing in traces
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
                        "content": "You are a pharmacy policy expert. Verify the decision logic. Output a concise justification (max 15 words)."
                    },
                    {
                        "role": "user",
                        "content": f"Context: {context}\nDecision: {decision}\nReasoning:"
                    }
                ],
                # temperature=0.1,  # Removed to avoid "unsupported value" error with reasoning models
                # max_tokens=200 # Removed to avoid "unsupported_parameter" error with reasoning models
                # max_completion_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"PolicyAgent Reasoning Error: {e}")
            return f"{decision} based on policy rules (Fallback: {str(e)})"

    @agent_trace("PolicyAgent", "gpt-5.2")
    async def check_prescription_required(self, medicine_name: str) -> AgentOutput:
        """
        Check if medicine requires prescription.
        Returns standardized AgentOutput.
        """
        medicine_lower = medicine_name.lower()
        is_controlled = any(cs in medicine_lower for cs in CONTROLLED_SUBSTANCES)
        
        # Check actual data if available
        requires_rx = is_controlled
        if self._data_service:
            medicines = self._data_service.search_medicine(medicine_name)
            if medicines:
                requires_rx = medicines[0].prescription_required
                is_controlled = medicines[0].controlled_substance
        
        if is_controlled:
            context = f"{medicine_name} is a controlled substance. Strict policy: Prescription required, max 30 days."
            reason = await self._generate_reasoning(context, "REJECTED")
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=reason,
                evidence=[
                    f"medicine_name={medicine_name}",
                    f"controlled_substance=True",
                    f"requires_prescription=True",
                    "requirement=Photo ID required",
                    "requirement=PDMP check required",
                    "max_supply_days=30"
                ],
                message=None,
                next_agent=None
            )
        
        if requires_rx:
            # Build detailed reason (2 lines as required)
            reason_line1 = f"{medicine_name} requires a valid prescription."
            reason_line2 = f"Upload prescription to proceed. Flow paused awaiting prescription."
            context = f"{reason_line1} {reason_line2}"
            reason = await self._generate_reasoning(context, "NEEDS_INFO")
            
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.NEEDS_INFO,
                reason=reason,
                evidence=[
                    f"medicine_name={medicine_name}",
                    f"requires_prescription=True",
                    f"controlled_substance=False",
                    f"policy_check=NEEDS_PRESCRIPTION"
                ],
                message=None,
                next_agent=None
            )
        
        # OTC - can proceed
        # Build detailed reason (2 lines as required)
        reason_line1 = f"{medicine_name} is available over-the-counter."
        reason_line2 = f"No prescription required. Approved for fulfillment."
        context = f"{reason_line1} {reason_line2}"
        reason = await self._generate_reasoning(context, "APPROVED")
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=reason,
            evidence=[
                f"medicine_name={medicine_name}",
                f"requires_prescription=False",
                f"controlled_substance=False",
                f"policy_check=PASSED"
            ],
            message=None,
            next_agent="FulfillmentAgent"
        )

    @agent_trace("PolicyAgent", "gpt-5.2")
    async def validate_quantity(self, medicine_name: str, quantity: int) -> AgentOutput:
        """
        Validate if quantity is within limits.
        """
        medicine_lower = medicine_name.lower()
        
        # Determine limit
        if any(cs in medicine_lower for cs in CONTROLLED_SUBSTANCES):
            max_allowed = QUANTITY_LIMITS["controlled"]
            limit_type = "controlled"
        elif "amoxicillin" in medicine_lower or "azithromycin" in medicine_lower:
            max_allowed = QUANTITY_LIMITS["antibiotic"]
            limit_type = "antibiotic"
        else:
            max_allowed = QUANTITY_LIMITS["default"]
            limit_type = "default"
        
        # Check medicine-specific limit
        if self._data_service:
            medicines = self._data_service.search_medicine(medicine_name)
            if medicines:
                max_allowed = min(max_allowed, medicines[0].max_quantity_per_order)
        
        if quantity > max_allowed:
            context = f"Quantity {quantity} exceeds limit of {max_allowed} for {limit_type} medicines."
            reason = await self._generate_reasoning(context, "REJECTED")
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=reason,
                evidence=[
                    f"medicine_name={medicine_name}",
                    f"requested_quantity={quantity}",
                    f"max_allowed={max_allowed}",
                    f"limit_type={limit_type}"
                ],
                message=None,
                next_agent=None
            )
        
        context = f"Quantity {quantity} is within allowed limit of {max_allowed}."
        reason = await self._generate_reasoning(context, "APPROVED")
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=reason,
            evidence=[
                f"medicine_name={medicine_name}",
                f"requested_quantity={quantity}",
                f"max_allowed={max_allowed}"
            ],
            message=None,
            next_agent="FulfillmentAgent"
        )

    @agent_trace("PolicyAgent", "gpt-5.2")
    async def check_drug_interactions(self, medicines: List[str]) -> AgentOutput:
        """
        Check for drug interactions between medicines.
        """
        if len(medicines) < 2:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.APPROVED,
                reason="Single medicine - no interaction check needed",
                evidence=[f"medicines_count={len(medicines)}"],
                message=None,
                next_agent="FulfillmentAgent"
            )
        
        medicine_list = [m.lower() for m in medicines]
        warnings = []
        severity = "none"
        
        for (drug1, drug2), interaction in DRUG_INTERACTIONS.items():
            if drug1 in medicine_list and drug2 in medicine_list:
                warnings.append(f"{drug1}+{drug2}: {interaction['warning']}")
                if interaction["severity"] == "severe":
                    severity = "severe"
                elif severity != "severe":
                    severity = interaction["severity"]
        
        if severity == "severe":
            context = f"Severe drug interaction detected: {warnings}."
            reason = await self._generate_reasoning(context, "REJECTED")
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=reason,
                evidence=[f"interaction={w}" for w in warnings] + [f"severity={severity}"],
                message=None,
                next_agent=None
            )
        
        if warnings:
            context = f"Drug interaction warning matched: {warnings}. Severity {severity} is acceptable."
            reason = await self._generate_reasoning(context, "APPROVED")
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.APPROVED,
                reason=reason,
                evidence=[f"interaction={w}" for w in warnings] + [f"severity={severity}"],
                message=None,
                next_agent="FulfillmentAgent"
            )
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason="No drug interactions detected",
            evidence=[f"medicines={medicines}", "interactions=0"],
            message=None,
            next_agent="FulfillmentAgent"
        )

    @agent_trace("PolicyAgent", "gpt-5.2")
    async def validate_prescription(
        self, 
        image_base64: str, 
        medicine_name: str
    ) -> AgentOutput:
        """
        Validate a prescription image using AI vision.
        Checks for doctor's name, date, medicine, and other validity criteria.
        
        Args:
            image_base64: Base64 encoded prescription image
            medicine_name: Expected medicine name to verify
            
        Returns:
            AgentOutput with APPROVED if valid, REJECTED if invalid
        """
        from services.prescription_validator import validate_prescription_image
        
        # Validate using GPT-4 Vision
        result = await validate_prescription_image(image_base64, medicine_name)
        
        if result["is_valid"]:
            # Build evidence from validation
            evidence = [
                f"prescription_valid=True",
                f"doctor_name={result.get('doctor_name', 'Verified')}",
                f"date={result.get('date', 'Present')}",
                f"confidence={result.get('confidence', 0.8):.2f}"
            ]
            
            if result.get("medicines"):
                evidence.append(f"medicines_found={','.join(result['medicines'])}")
            
            # Generate reasoning
            context = f"Prescription validated: Dr. {result.get('doctor_name', 'Unknown')}, dated {result.get('date', 'N/A')}"
            reason = await self._generate_reasoning(context, "APPROVED")
            
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.APPROVED,
                reason=reason,
                evidence=evidence,
                message=f"✅ Prescription verified! Doctor: {result.get('doctor_name', 'Verified')}, Date: {result.get('date', 'Valid')}",
                next_agent="FulfillmentAgent"
            )
        else:
            # Prescription invalid
            rejection_reason = result.get("rejection_reason", "Invalid prescription image")
            
            evidence = [
                f"prescription_valid=False",
                f"rejection_reason={rejection_reason}",
                f"confidence={result.get('confidence', 0.0):.2f}"
            ]
            
            if result.get("is_expired"):
                evidence.append("prescription_expired=True")
            
            # Generate reasoning
            context = f"Prescription rejected: {rejection_reason}"
            reason = await self._generate_reasoning(context, "REJECTED")
            
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=reason,
                evidence=evidence,
                message=f"❌ {rejection_reason}",
                next_agent=None
            )

    def get_trace_id(self) -> Optional[str]:
        return get_trace_id()
