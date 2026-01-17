"""
PharmacistAgent - LangChain Agent Implementation
Interprets user intent, extracts structured order data, maintains context, routes to downstream agents.
EMITS STANDARDIZED OUTPUT: {agent, decision, reason, evidence, message, next_agent}
Uses: gpt-5-mini
"""

import os
import json
from typing import Optional, Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langsmith import traceable

from models.schemas import Decision, AgentOutput
from utils.tracing import agent_span, get_trace_id


# ============ MODEL CONFIG ============
MODEL_NAME = "gpt-5.2"  # Using gpt-5-mini for PharmacistAgent
TEMPERATURE = 0.1


# ============ TOOLS ============

@tool
def emit_decision(
    decision: str,
    reason: str,
    evidence: str,
    message: str,
    next_agent: str = ""
) -> dict:
    """
    Emit a standardized decision from PharmacistAgent.
    ALL responses MUST go through this function.
    
    Args:
        decision: One of APPROVED, REJECTED, NEEDS_INFO, SCHEDULED
        reason: Short factual justification
        evidence: Comma-separated list of exact data points from context
        message: User-facing message to display
        next_agent: Next agent to call (InventoryAgent, PolicyAgent, FulfillmentAgent, RefillPredictionAgent) or empty
    
    Returns:
        Standardized agent output
    """
    return {
        "agent": "PharmacistAgent",
        "decision": decision,
        "reason": reason,
        "evidence": [e.strip() for e in evidence.split(",") if e.strip()],
        "message": message,
        "next_agent": next_agent if next_agent else None
    }


@tool
def check_inventory(
    medicine_name: str,
    quantity: int = 0,
    dosage: str = "",
    form: str = ""
) -> dict:
    """
    Request inventory check from InventoryAgent.
    Use when user asks about medicine availability OR wants to order.
    
    Args:
        medicine_name: Name of the medicine
        quantity: Number of units to order (0 if just checking availability)
        dosage: Optional dosage (e.g., "500mg")
        form: Optional form (tablet, capsule, syrup)
    
    Returns:
        Routing instruction
    """
    evidence = [f"medicine_name={medicine_name}"]
    if quantity > 0:
        evidence.append(f"quantity={quantity}")
    if dosage:
        evidence.append(f"dosage={dosage}")
    if form:
        evidence.append(f"form={form}")
    
    return {
        "agent": "PharmacistAgent",
        "decision": "NEEDS_INFO",
        "reason": f"Need to verify stock for {medicine_name}",
        "evidence": evidence,
        "message": f"Let me check {medicine_name} for you...",
        "next_agent": "InventoryAgent"
    }


@tool
def check_policy(
    medicine_name: str,
    quantity: int = 0
) -> dict:
    """
    Request policy check from PolicyAgent.
    Use when checking prescription requirements or safety.
    
    Args:
        medicine_name: Name of the medicine
        quantity: Quantity requested
    
    Returns:
        Routing instruction
    """
    return {
        "agent": "PharmacistAgent",
        "decision": "NEEDS_INFO",
        "reason": f"Need to verify prescription requirements for {medicine_name}",
        "evidence": [f"medicine_name={medicine_name}", f"quantity={quantity}"],
        "message": f"Let me check the requirements for {medicine_name}...",
        "next_agent": "PolicyAgent"
    }


@tool
def create_order(
    patient_id: str,
    medicine_id: str,
    medicine_name: str,
    quantity: int,
    delivery_type: str = "pickup"
) -> dict:
    """
    Request order creation from FulfillmentAgent.
    Use ONLY after inventory and policy checks pass.
    
    Args:
        patient_id: Patient identifier
        medicine_id: Medicine ID from inventory
        medicine_name: Name of the medicine
        quantity: Number of units
        delivery_type: "pickup" or "delivery"
    
    Returns:
        Routing instruction
    """
    return {
        "agent": "PharmacistAgent",
        "decision": "APPROVED",
        "reason": f"Order validated for {medicine_name} x{quantity}",
        "evidence": [f"patient_id={patient_id}", f"medicine_id={medicine_id}", f"quantity={quantity}"],
        "message": f"Creating your order for {quantity} units of {medicine_name}...",
        "next_agent": "FulfillmentAgent"
    }


@tool
def check_refills(patient_id: str) -> dict:
    """
    Request refill predictions from RefillPredictionAgent.
    Use when user asks about refills or running low.
    
    Args:
        patient_id: Patient identifier
    
    Returns:
        Routing instruction
    """
    return {
        "agent": "PharmacistAgent",
        "decision": "NEEDS_INFO",
        "reason": f"Checking refill predictions for patient {patient_id}",
        "evidence": [f"patient_id={patient_id}"],
        "message": "Let me check your upcoming refills...",
        "next_agent": "RefillPredictionAgent"
    }


@tool
def show_order_preview(
    patient_id: str,
    patient_name: str,
    medicine_id: str,
    medicine_name: str,
    strength: str,
    quantity: int,
    prescription_required: bool = False,
    unit_price: float = 0.0
) -> dict:
    """
    Display order preview card for customer review.
    Use when customer confirms they want to order.
    
    Args:
        patient_id: Patient ID
        patient_name: Patient name
        medicine_id: Medicine ID
        medicine_name: Medicine name
        strength: Dosage/strength
        quantity: Number of units
        prescription_required: Whether Rx is needed
        unit_price: Price per unit
    """
    import uuid
    return {
        "agent": "PharmacistAgent",
        "decision": "APPROVED",
        "reason": f"Showing order preview for {medicine_name}",
        "evidence": [f"medicine={medicine_name}", f"qty={quantity}", f"price=${unit_price*quantity:.2f}"],
        "message": f"Here's your order preview for {medicine_name}.",
        "next_agent": None,
        "ui_card": "order_preview",
        "ui_data": {
            "preview_id": f"PREV-{uuid.uuid4().hex[:8].upper()}",
            "patient_id": patient_id,
            "patient_name": patient_name,
            "items": [{
                "medicine_id": medicine_id,
                "medicine_name": medicine_name,
                "strength": strength,
                "quantity": quantity,
                "prescription_required": prescription_required,
                "unit_price": unit_price,
                "supply_days": quantity
            }],
            "total_amount": unit_price * quantity,
            "requires_prescription": prescription_required
        }
    }


@tool
def show_prescription_upload(
    medicine_name: str,
    medicine_id: str,
    is_controlled: bool = False
) -> dict:
    """
    Display prescription upload card.
    Use when medicine requires prescription.
    
    Args:
        medicine_name: Name of medicine
        medicine_id: Medicine ID
        is_controlled: If controlled substance
    """
    msg = f"{medicine_name} is a controlled substance" if is_controlled else f"{medicine_name} requires a prescription"
    return {
        "agent": "PharmacistAgent",
        "decision": "NEEDS_INFO",
        "reason": f"Prescription required for {medicine_name}",
        "evidence": [f"medicine={medicine_name}", f"controlled={is_controlled}"],
        "message": f"{msg}. Please upload your prescription.",
        "next_agent": None,
        "ui_card": "prescription_upload",
        "ui_data": {
            "medicine_name": medicine_name,
            "medicine_id": medicine_id,
            "requires_prescription": True,
            "is_controlled": is_controlled,
            "message": msg
        }
    }


@tool
def show_order_confirmation(
    order_id: str,
    patient_id: str,
    patient_name: str,
    medicine_name: str,
    strength: str,
    quantity: int,
    unit_price: float,
    delivery_type: str = "pickup"
) -> dict:
    """
    Display order confirmation card AFTER order is created.
    Use ONLY after FulfillmentAgent has created the order.
    
    Args:
        order_id: The order ID from FulfillmentAgent
        patient_id: Patient ID
        patient_name: Patient name
        medicine_name: Medicine name
        strength: Medicine strength (e.g., "500mg")
        quantity: Number of units
        unit_price: Price per unit
        delivery_type: "pickup" or "delivery"
    """
    from datetime import datetime
    
    # Calculate amounts
    subtotal = unit_price * quantity
    tax = subtotal * 0.05
    delivery_fee = 2.00 if delivery_type == "delivery" else 0.00
    total = subtotal + tax + delivery_fee
    
    delivery_estimate = "Tomorrow by 9:00 PM" if delivery_type == "delivery" else "Ready in 2 hours"
    created_at = datetime.now()
    
    # Build detailed order summary message
    summary = f"""📋 **Order Summary**
━━━━━━━━━━━━━━━━━━━━━━
**Order ID:** {order_id}
**Patient:** {patient_name}
**Date:** {created_at.strftime("%Y-%m-%d %H:%M")}

**Items:**
• {medicine_name} {strength} x{quantity} @ ${unit_price:.2f} = ${subtotal:.2f}

**Subtotal:** ${subtotal:.2f}
**Tax (5%):** ${tax:.2f}
**Delivery:** ${delivery_fee:.2f}
━━━━━━━━━━━━━━━━━━━━━━
**Total:** ${total:.2f}

**Status:** CONFIRMED
**Estimated Delivery:** {delivery_estimate}"""
    
    return {
        "agent": "PharmacistAgent",
        "decision": "APPROVED",
        "reason": f"Order {order_id} confirmed successfully",
        "evidence": [
            f"order_id={order_id}",
            f"patient_id={patient_id}",
            f"medicine={medicine_name}",
            f"quantity={quantity}",
            f"total=${total:.2f}"
        ],
        "message": summary,
        "next_agent": None,
        "ui_card": "order_confirmation",
        "ui_data": {
            "order_id": order_id,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "items": [{
                "medicine_id": f"MED-{order_id[-4:]}",
                "medicine_name": medicine_name,
                "strength": strength,
                "quantity": quantity,
                "prescription_required": False,
                "unit_price": unit_price,
                "supply_days": quantity
            }],
            "subtotal": subtotal,
            "tax": tax,
            "delivery_fee": delivery_fee,
            "total_amount": total,
            "safety_decision": "APPROVE",
            "safety_reasons": [],
            "requires_prescription": False,
            "created_at": created_at.isoformat(),
            "estimated_delivery": delivery_estimate,
            "status": "CONFIRMED"
        }
    }


# ============ AGENT CLASS ============

class PharmacistAgent:
    """
    PharmacistAgent - Main conversational interface.
    Uses gpt-5-mini model.
    
    EMITS STANDARDIZED OUTPUT:
    {agent, decision, reason, evidence, message, next_agent}
    """

    def __init__(self, model_name: str = MODEL_NAME, temperature: float = TEMPERATURE):
        self.agent_name = "PharmacistAgent"
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.tools = [
            emit_decision,
            check_inventory,
            check_policy,
            create_order,
            check_refills,
            show_order_preview,
            show_prescription_upload,
            show_order_confirmation,
        ]
        
        self.sessions: Dict[str, List[Dict[str, str]]] = {}
        self.agent = self._create_agent()
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            return_intermediate_steps=True,
            handle_parsing_errors=True
        )

    def _create_agent(self):
        """Create the LangChain agent"""
        
        system_prompt = """You are PharmacistAgent, a professional AI pharmacy assistant in an autonomous pharmacy system.

========================
ABSOLUTE RESPONSE RULES
========================
1. You MUST ALWAYS respond using a tool (emit_decision or other provided tools).
2. You MUST NEVER respond with plain text.
3. You MUST NEVER respond outside valid JSON.
4. If required data is missing, respond with NEEDS_INFO — do NOT guess.
5. NEVER fabricate medicine details, dosage, strength, quantity, or prior orders.
6. ALWAYS read and use chat_history before responding.

Failure to follow these rules is a critical error.

========================
CONVERSATION MEMORY (CRITICAL)
========================
- ALWAYS use chat_history as the source of conversational context.
- NEVER ask for information that was already mentioned earlier.
- If strength, form, or medicine was mentioned previously, REUSE it.
- If the user says "yes", "confirm", "3 tablets", etc., they are referring to the MOST RECENT medicine discussed.
- NEVER reset context unless explicitly instructed.

========================
MULTILINGUAL SUPPORT
========================
- Detect the language used by the user.
- ALWAYS respond in the SAME language.
- Medicine names MUST remain in English.
- Explanations MUST be in the user's language.

========================
PATIENT CONTEXT AWARENESS
========================
- The patient is already authenticated by the system.
- The patient_id in the request is the source of truth.
- Use the patient context to personalize responses.
- DO NOT ask for identity verification — the system handles authentication.
- Focus on fulfilling the patient's pharmacy requests.

========================
GREETING RULES
========================
- For greetings or first interaction, introduce yourself warmly using the patient's name from context:
  "Hello [PATIENT_NAME]! I'm your AI pharmacy assistant. How can I help you today?"
- The patient name is provided in the request context - use it to personalize greetings.
- This rule applies ONLY to first turns — do NOT repeat greetings mid-conversation.

========================
🚫 DOMAIN RESTRICTION (CRITICAL – PHARMACY ONLY)
========================
PHARMACY DOMAIN ENFORCEMENT (NON-NEGOTIABLE):

- You are a PHARMACIST, not a general store assistant.
- You MUST ONLY handle:
  - Medicines
  - OTC pharmacy products
  - Medical devices
  - Health-related supplies

- You MUST NEVER assist with:
  - Food or beverages (e.g., ice cream, snacks, drinks)
  - Grocery items
  - Household items
  - Non-medical consumer products

- If a user asks for a NON-PHARMACY item:
  → Respond with decision = REJECTED
  → Politely clarify that you only assist with pharmacy-related products
  → Offer a pharmacy-relevant alternative if applicable

- You MUST NOT ask clarifying questions that assume non-pharmacy intent.
  (e.g., "Do you mean food ice cream?" is FORBIDDEN)

EXAMPLES:
User: "Do you have ice cream?"
Correct:
"I can help only with pharmacy and medical products. If you're looking for a cold pack or ice pack for pain relief, I can help with that."

Incorrect:
"Do you mean food ice cream or ice pack?"

========================
INTENT CLASSIFICATION (EXACTLY ONE)
========================
You MUST classify each user message as ONE of the following:

- ORDER
- REFILL_CHECK
- STATUS_CHECK
- GENERAL_INQUIRY
- CONFIRM_ORDER
- CANCEL_ORDER

========================
SMART INFORMATION GATHERING
========================
When ordering a medicine, collect ONLY what is missing.

Required fields:
1. Medicine name
2. Quantity
3. Strength (ONLY if not already known)
4. Form (tablet, syrup, capsule — ONLY if not already known)

DO NOT ASK if:
- The information exists in chat_history
- Only one strength or form exists in inventory
- The system already returned evidence (inventory / policy)

========================
AVOID REDUNDANT QUESTIONS
========================
❌ "What strength do you need?" (if already known)
❌ "Tablet or syrup?" (if only one exists)
❌ "Which medicine?" (if already discussed)

✅ "Perfect. I'll prepare 3 tablets of Paracetamol 500mg."

========================
AUTO ORDER PREVIEW RULE (CRITICAL)
========================
- If ALL required order details are known (medicine name, quantity, strength, form),
  you MUST NOT stop after an acknowledgment sentence.

- After any acknowledgment such as:
  "Perfect. I'll prepare 3 tablets of Paracetamol 500mg."

  you MUST IMMEDIATELY:
  → call show_order_preview
  → in the SAME response
  → without asking further questions
  → without waiting for user input

- The acknowledgment and order preview are a SINGLE, ATOMIC STEP.
- Failing to show the order preview when details are complete is a CRITICAL ERROR.

========================
ORDER FLOW
========================
1. User requests medicine → gather missing info (name, quantity, strength, form)
2. Show order preview with show_order_preview
3. User confirms → IMMEDIATELY show order confirmation with show_order_confirmation

DO NOT re-check inventory or policy after showing order preview.
DO NOT ask for more details after user confirms.

========================
CONFIRM_ORDER HANDLING (MOST CRITICAL)
========================
When user says "confirm", "yes", "place order", "proceed", "ok", or clicks Confirm Order button:

→ IMMEDIATELY call show_order_confirmation
→ Use the medicine details from the conversation (name, strength, quantity)
→ DO NOT verify availability again
→ DO NOT check prescription again  
→ DO NOT ask any questions
→ DO NOT say "I need to verify..." or "Before I can..."

The order preview was already shown. User confirmed. Just place the order.

Example:
User: "confirm"
Correct: Call show_order_confirmation with the order details
Wrong: "I need to verify availability first..."

========================
STOCK RULES
========================
- Say "available" or "out of stock" - never reveal exact numbers.

========================
REFILL INTELLIGENCE
========================
- Use check_refills ONLY when relevant.
- You MAY proactively suggest refills.
- If refill is scheduled → decision = SCHEDULED.

========================
DECISION TYPES
========================
Your emit_decision MUST include ONE of:
- APPROVED
- REJECTED
- NEEDS_INFO
- SCHEDULED

========================
MANDATORY OUTPUT FORMAT
========================
EVERY response MUST be valid JSON in the following structure:

{{
  "intent": "ORDER | REFILL_CHECK | STATUS_CHECK | GENERAL_INQUIRY | CONFIRM_ORDER | CANCEL_ORDER",
  "confidence": 0.0,
  "requires_extraction": true | false,
  "requires_safety_check": true | false,
  "response_draft": "Natural pharmacist response using patient's REAL name.",
  "follow_up_needed": true | false,
  "follow_up_question": ""
}}

========================
TONE & BEHAVIOR
========================
- Sound like a real, professional pharmacist.
- Be concise, polite, and safety-focused.
- Never over-ask.
- Never over-explain.
- Always guide the user clearly to the next step.

========================
FINAL ENFORCEMENT
========================
- Tool call REQUIRED
- JSON ONLY
- Context-aware
- Zero assumptions
- Zero redundancy
- If order details are complete and no preview is shown, the response is INVALID.

========================
WORKFLOW TOOLS
========================
- emit_decision: Ask clarifying questions (NEEDS_INFO) or provide responses
- check_inventory: Check medicine availability
- check_policy: Check prescription/safety requirements
- show_order_preview: Show preview card BEFORE order creation (MUST auto-call when details complete)
- show_prescription_upload: Show prescription upload if required
- create_order: Create actual order ONLY after user confirms preview
- show_order_confirmation: Show confirmation AFTER order created
- check_refills: Check refill predictions"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        return create_openai_tools_agent(self.llm, self.tools, prompt)

    @traceable(name="PharmacistAgent.process", run_type="chain")
    async def process_message(
        self, 
        user_message: str, 
        session_id: str = "default",
        patient_id: Optional[str] = None,
        patient_name: Optional[str] = None
    ) -> AgentOutput:
        """
        Process message and return standardized AgentOutput.
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        chat_history = self.sessions[session_id]
        
        # Build context with patient info
        context_parts = []
        if patient_id:
            context_parts.append(f"Patient ID: {patient_id}")
        if patient_name:
            context_parts.append(f"Patient Name: {patient_name}")
        context = f" [{', '.join(context_parts)}]" if context_parts else ""
        
        result = await self.agent_executor.ainvoke({
            "input": user_message + context,
            "chat_history": chat_history
        })
        
        # Extract standardized output from tool calls
        agent_output = self._extract_output(result)
        
        # Update history with proper LangChain message objects
        from langchain_core.messages import HumanMessage, AIMessage
        chat_history.append(HumanMessage(content=user_message))
        response_content = agent_output.message or result.get("output", "")
        chat_history.append(AIMessage(content=response_content))
        
        # Keep last 20 messages
        self.sessions[session_id] = chat_history[-20:]
        
        return agent_output

    def _extract_output(self, result: dict) -> AgentOutput:
        """Extract standardized output from agent result"""
        for step in result.get("intermediate_steps", []):
            action, observation = step
            if isinstance(observation, dict) and "agent" in observation:
                return AgentOutput(
                    agent=observation.get("agent", self.agent_name),
                    decision=Decision(observation.get("decision", "APPROVED")),
                    reason=observation.get("reason", ""),
                    evidence=observation.get("evidence", []),
                    message=observation.get("message"),
                    next_agent=observation.get("next_agent")
                )
        
        # Fallback if no tool was called
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason="Direct response to user query",
            evidence=[],
            message=result.get("output", ""),
            next_agent=None
        )

    def get_ui_card_data(self, result: dict) -> tuple:
        """Extract UI card data if present"""
        for step in result.get("intermediate_steps", []):
            action, observation = step
            if isinstance(observation, dict) and "ui_card" in observation:
                return observation.get("ui_card"), observation.get("ui_data")
        return None, None

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def get_trace_id(self) -> Optional[str]:
        return get_trace_id()
