"""
PharmacistAgent - Direct LLM Implementation (No AgentExecutor)
Interprets user intent, extracts structured order data, maintains context, routes to downstream agents.
EMITS STANDARDIZED OUTPUT: {agent, decision, reason, evidence, message, next_agent}
Uses: gpt-5.2

REFACTORED: Removed AgentExecutor/ChatPromptTemplate to ensure clean agent-only traces.
"""

import os
import json
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

from openai import AsyncOpenAI

from models.schemas import Decision, AgentOutput
from utils.tracing import agent_trace, get_trace_id, create_non_traced_llm


# ============ MODEL CONFIG ============
MODEL_NAME = "gpt-5.2"
TEMPERATURE = 0.1


# ============ SYSTEM PROMPT ============
SYSTEM_PROMPT = """You are PharmacistAgent, a professional AI pharmacy assistant in an autonomous pharmacy system.

========================
RESPONSE FORMAT
========================
You MUST respond with valid JSON in this exact structure:
{
  "action": "TOOL_NAME",
  "params": { ... tool parameters ... }
}

Available actions:
- emit_decision: Respond to user queries
- check_inventory: Check medicine availability
- check_policy: Check prescription requirements
- show_order_preview: Display order preview card
- show_order_confirmation: Display order confirmation
- show_prescription_upload: Request prescription upload
- check_refills: Check refill predictions

========================
MESSY TEXT HANDLING (CRITICAL)
========================
Users often type informally. You MUST interpret their intent intelligently:

**Common Typos & Misspellings:**
- "paracetmol", "parcetamol", "paracetamoll" → Paracetamol
- "ibuprofn", "ibuprofen", "advil" → Ibuprofen
- "cetirzine", "cetirizne", "allergytab" → Cetirizine
- "metformn", "metformine", "sugar medicine" → Metformin
- Handle phonetic spelling: "asthma pump" → inhaler

**Abbreviations & Shorthand:**
- "para", "pcm", "crocin" → Paracetamol
- "ctz", "cetriz" → Cetirizine
- "amox", "amoxil" → Amoxicillin
- "met", "glucophage" → Metformin
- "tabs", "tab" → tablets
- "caps" → capsules
- "qty" → quantity
- "pls", "plz" → please
- "tmrw" → tomorrow
- "asap" → as soon as possible

**Informal Requests:**
- "gimme 10 para" → Order 10 Paracetamol tablets
- "need fever med" → Likely Paracetamol or Ibuprofen
- "headache medicine" → Pain relief category
- "want some cold tablets" → Cetirizine or similar
- "sugar tablet" → Metformin (diabetes medicine)
- "BP medicine" → Cardiovascular category (Amlodipine, Losartan, etc.)
- "acidity tablet" → Omeprazole or Pantoprazole

**Numbers & Quantities:**
- "10", "ten", "10x" → quantity: 10
- "half dozen" → 6
- "dozen" → 12
- "one strip" → typically 10 tablets
- "2 weeks supply" → calculate based on dosage

**Context Hints:**
- If user mentions symptoms, suggest appropriate OTC medicines
- "for my mom" / "for kids" → Note age-appropriate dosing
- Always ASK for quantity if not specified, don't assume

========================
CONVERSATION MEMORY (CRITICAL)
========================
- ALWAYS use the chat_history provided as context
- NEVER ask for information already mentioned
- If user says "yes", "confirm", "3 tablets" - they're referring to the MOST RECENT medicine
- **NEW REQUEST PRIORITY**: If the user mentions a specific medicine name in the CURRENT message (e.g., "I want Paracetamol"), this indicates a NEW INTENT. IGNORE the previous medicine context (e.g., Metformin) and focus ONLY on the new medicine.
- Do NOT hallucinate medicine names. Use exactly what the user typed.

========================
PATIENT CONTEXT
========================
- The patient is already authenticated
- patient_id and patient_name are provided in context
- DO NOT ask for identity verification

========================
GREETING RULES
========================
- For first interaction, greet warmly: "Hello [PATIENT_NAME]! I'm your AI pharmacy assistant. How can I help you today?"
- Do NOT repeat greetings mid-conversation

========================
DOMAIN RESTRICTION
========================
- You are a PHARMACIST only
- Handle: Medicines, OTC products, medical devices, health supplies
- REJECT: Food, beverages, groceries, household items, non-medical products

========================
INTENT CLASSIFICATION
========================
Classify user message as ONE of:
- ORDER: User wants to purchase medicine
- REFILL_CHECK: User asking about refills
- STATUS_CHECK: Checking order status
- GENERAL_INQUIRY: General health/pharmacy questions
- CONFIRM_ORDER: User confirming order preview
- CANCEL_ORDER: User canceling order

========================
ORDER FLOW (MANDATORY SEQUENCE)
========================
CRITICAL: For any medicine order, you MUST follow this EXACT sequence:
1. User requests medicine → Check if QUANTITY is provided
2. IF QUANTITY IS MISSING → Ask "How many tablets/units of [medicine] would you like to order?"
   - DO NOT proceed to check_inventory until quantity is confirmed
   - DO NOT assume a default quantity
3. Once medicine name AND quantity are confirmed → call check_inventory
4. InventoryAgent will route to PolicyAgent
5. PolicyAgent will route to FulfillmentAgent
6. Order preview/confirmation happens ONLY after full chain completes

QUANTITY IS MANDATORY: Never proceed without explicit quantity from user.
NEVER skip to show_order_preview directly. ALWAYS start with check_inventory after quantity is confirmed.

========================
CONFIRM_ORDER HANDLING (CRITICAL)
========================
When user says "confirm", "yes", "place order", "proceed", "ok":
→ IMMEDIATELY call show_order_confirmation
→ Use medicine details from conversation
→ DO NOT verify availability again
→ DO NOT ask any questions

========================
STOCK RULES
========================
- Never reveal exact stock quantities
- When user asks "do you have X?" or "is X available?":
  → If in stock: "Yes, we have [medicine] in our store. How many would you like to order?"
  → If out of stock: "I'm sorry, [medicine] is currently out of stock."
- Always ask for quantity after confirming availability

========================
HISTORY & PAST ORDERS
========================
- If user asks "what did I order?", "order history", "last purchase":
  1. CHECK 'Recent Orders' in the CONTEXT section first.
  2. If orders exist: ANSWER DIRECTLY (e.g., "You recently ordered [Medicine] on [Date].").
  3. Action: "emit_decision" (DO NOT delegate to Refill/Inventory).
  4. If no history in context: "I don't see any recent orders in your history."

========================
ACTION PARAMETERS
========================

emit_decision:
- decision: APPROVED | REJECTED | NEEDS_INFO | SCHEDULED
- reason: Short factual justification (under 20 words)
- evidence: Comma-separated data points
- message: User-facing message
- next_agent: InventoryAgent | PolicyAgent | FulfillmentAgent | RefillPredictionAgent | null

check_inventory:
- items: List of objects { "medicine_name": str, "quantity": int, "dosage": str, "form": str }
- OR single item keys (medicine_name, quantity, ...) for backward compatibility

show_order_preview:
- patient_id, patient_name, items: [{medicine_name, quantity, ...}]

show_order_confirmation:
- order_id, patient_id, patient_name, items: [{medicine_name, quantity, ...}], unit_price, delivery_type

check_policy:
- items: [{medicine_name, quantity}]

check_refills:
- patient_id

show_prescription_upload:
- medicine_name, medicine_id, is_controlled
"""


class PharmacistAgent:
    """
    PharmacistAgent - Main conversational interface.
    Uses direct OpenAI API calls to avoid AgentExecutor trace spans.
    
    EMITS STANDARDIZED OUTPUT:
    {agent, decision, reason, evidence, message, next_agent}
    """

    def __init__(self, model_name: str = MODEL_NAME, temperature: float = TEMPERATURE):
        self.agent_name = "PharmacistAgent"
        self.model_name = model_name
        self.temperature = temperature
        # Direct OpenAI client (not LangChain) - no auto-tracing
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sessions: Dict[str, List[Dict[str, str]]] = {}

    def _load_conversation_from_firestore(self, session_id: str, conversation_id: str):
        """
        Load conversation history from Firestore and populate the session cache.
        This enables the agent to remember previous messages including medicine names and quantities.
        """
        try:
            from services.firestore_service import get_conversation_history
            messages = get_conversation_history(conversation_id, limit=20)
            if messages:
                self.sessions[session_id] = messages
                print(f"✅ Loaded {len(messages)} messages from Firestore into session {session_id}")
        except Exception as e:
            print(f"❌ Failed to load conversation from Firestore: {e}")

    @agent_trace("PharmacistAgent", "gpt-5.2")
    async def process_message(
        self, 
        user_message: str, 
        session_id: str = "default",
        patient_id: Optional[str] = None,
        patient_name: Optional[str] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> AgentOutput:
        """Process user message and return structured output"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
            # If session is empty but we have a conversation_id, load history from Firestore
            if conversation_id:
                self._load_conversation_from_firestore(session_id, conversation_id)
        
        chat_history = self.sessions[session_id]
        
        # Build context with patient info
        context_parts = []
        if patient_name:
            context_parts.append(f"Patient Name: {patient_name}")
        if patient_id:
            context_parts.append(f"Patient ID: {patient_id}")
            
        # Get patient history if available
        if user_id:
            try:
                from services.firestore_service import get_orders
                orders = get_orders(user_id, limit=3)
                if orders:
                    history_text = "Recent Orders:\n"
                    for o in orders:
                        date = o.get('orderedAt', 'recent')[:10] if isinstance(o.get('orderedAt'), str) else 'recent'
                        history_text += f"- {o.get('medicine')} ({o.get('quantity')}x {o.get('dosage')}) on {date}\n"
                    context_parts.append(history_text)
            except Exception as e:
                print(f"Failed to fetch history: {e}")
        
        # Build the system prompt dynamically
        dynamic_system_prompt = SYSTEM_PROMPT
        if context_parts:
            dynamic_system_prompt += "\n\n========================\nADDITIONAL CONTEXT\n========================\n"
            dynamic_system_prompt += "\n".join(context_parts)

        # Build messages for OpenAI
        messages = [{"role": "system", "content": dynamic_system_prompt}]
        
        # Add chat history
        for msg in chat_history[-10:]:  # Last 10 messages
            if isinstance(msg, dict):
                messages.append(msg)
            else:
                # Handle LangChain message objects
                role = "user" if hasattr(msg, 'type') and msg.type == 'human' else "assistant"
                content = msg.content if hasattr(msg, 'content') else str(msg)
                messages.append({"role": role, "content": content})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Call OpenAI directly (no LangChain wrapper = no trace spans)
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content
        
        # Parse LLM response
        try:
            action_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback if LLM doesn't return valid JSON
            action_data = {
                "action": "emit_decision",
                "params": {
                    "decision": "APPROVED",
                    "reason": "Direct response",
                    "evidence": "",
                    "message": response_text,
                    "next_agent": None
                }
            }
        
        # Execute the action and get result
        agent_output = await self._execute_action(
            action_data, 
            patient_id or "GUEST", 
            patient_name or "Guest"
        )
        
        # Update history
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": agent_output.message or ""})
        
        # Keep last 20 messages
        self.sessions[session_id] = chat_history[-20:]
        
        return agent_output

    async def _execute_action(
        self, 
        action_data: dict, 
        patient_id: str,
        patient_name: str
    ) -> AgentOutput:
        """Execute the action specified by the LLM and return AgentOutput."""
        action = action_data.get("action", "emit_decision")
        params = action_data.get("params", {})
        
        if action == "emit_decision":
            return self._emit_decision(params)
        
        elif action == "check_inventory":
            return self._check_inventory(params)
        
        elif action == "check_policy":
            return self._check_policy(params)
        
        elif action == "show_order_preview":
            return self._show_order_preview(params, patient_id, patient_name)
        
        elif action == "show_order_confirmation":
            return self._show_order_confirmation(params, patient_id, patient_name)
        
        elif action == "show_prescription_upload":
            return self._show_prescription_upload(params)
        
        elif action == "check_refills":
            return self._check_refills(params, patient_id)
        
        else:
            # Default: emit as decision
            return self._emit_decision(params)

    def _emit_decision(self, params: dict) -> AgentOutput:
        """Emit a standardized decision."""
        decision_str = params.get("decision", "APPROVED")
        try:
            decision = Decision(decision_str)
        except ValueError:
            decision = Decision.APPROVED
        
        evidence_str = params.get("evidence", "")
        evidence = [e.strip() for e in evidence_str.split(",") if e.strip()] if isinstance(evidence_str, str) else evidence_str or []
        
        return AgentOutput(
            agent=self.agent_name,
            decision=decision,
            reason=params.get("reason", ""),
            evidence=evidence,
            message=params.get("message"),
            next_agent=params.get("next_agent")
        )

    def _check_inventory(self, params: dict) -> AgentOutput:
        """Request inventory check from InventoryAgent."""
        # Support multi-item 'items' list
        items = params.get("items", [])
        
        # Backward compatibility for single item params
        if not items and params.get("medicine_name"):
            items.append({
                "medicine_name": params.get("medicine_name"),
                "quantity": params.get("quantity", 0),
                "dosage": params.get("dosage", ""),
                "form": params.get("form", "")
            })
            
        evidence = []
        med_names = []
        
        for item in items:
            med = item.get("medicine_name", "")
            if med:
                med_names.append(med)
                # Serialize item data to JSON-string evidence
                # This safely packages all fields without parsing issues in Orchestrator
                item_json = json.dumps(item)
                evidence.append(f"item_data={item_json}")
        
        # Add legacy format for the first item (optional, for safety)
        if items:
            evidence.append(f"medicine_name={items[0].get('medicine_name', '')}")
            evidence.append(f"quantity={items[0].get('quantity', 0)}")
        
        meds_str = ", ".join(med_names)
        
        # Build detailed reason
        reason = f"User requested {meds_str}. Routing to InventoryAgent to check stock for {len(items)} items."
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.NEEDS_INFO,
            reason=reason,
            evidence=evidence,
            message=f"Let me check the availability for {meds_str}...",
            next_agent="InventoryAgent"
        )

    def _check_policy(self, params: dict) -> AgentOutput:
        """Request policy check from PolicyAgent."""
        medicine_name = params.get("medicine_name", "")
        quantity = params.get("quantity", 0)
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.NEEDS_INFO,
            reason=f"Need to verify prescription requirements for {medicine_name}",
            evidence=[f"medicine_name={medicine_name}", f"quantity={quantity}"],
            message=f"Let me check the requirements for {medicine_name}...",
            next_agent="PolicyAgent"
        )

    def _show_order_preview(self, params: dict, patient_id: str, patient_name: str) -> AgentOutput:
        """Display order preview card."""
        medicine_name = params.get("medicine_name", "")
        strength = params.get("strength", "")
        quantity = params.get("quantity", 1)
        unit_price = params.get("unit_price", 5.00)
        prescription_required = params.get("prescription_required", False)
        medicine_id = params.get("medicine_id", f"MED-{medicine_name[:3].upper()}")
        
        preview_id = f"PREV-{uuid.uuid4().hex[:8].upper()}"
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=f"Showing order preview for {medicine_name}",
            evidence=[
                f"medicine_name={medicine_name}",
                f"qty={quantity}",
                f"price=₹{unit_price * quantity:.2f}"
            ],
            message=f"Here's your order preview for {medicine_name}.",
            next_agent=None,
            ui_card="order_preview",
            ui_data={
                "preview_id": preview_id,
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
        )

    def _show_order_confirmation(self, params: dict, patient_id: str, patient_name: str) -> AgentOutput:
        """Display order confirmation card."""
        order_id = params.get("order_id", f"ORD-{uuid.uuid4().hex[:8].upper()}")
        medicine_name = params.get("medicine_name", "")
        strength = params.get("strength", "")
        quantity = params.get("quantity", 1)
        unit_price = params.get("unit_price", 5.00)
        delivery_type = params.get("delivery_type", "pickup")
        
        # Calculate amounts
        subtotal = unit_price * quantity
        tax = subtotal * 0.05
        delivery_fee = 40.00 if delivery_type == "delivery" else 0.00
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
• {medicine_name} {strength} x{quantity} @ ₹{unit_price:.2f} = ₹{subtotal:.2f}

**Subtotal:** ₹{subtotal:.2f}
**Tax (5%):** ₹{tax:.2f}
**Delivery:** ₹{delivery_fee:.2f}
━━━━━━━━━━━━━━━━━━━━━━
**Total:** ₹{total:.2f}

**Status:** CONFIRMED
**Estimated Delivery:** {delivery_estimate}"""
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=f"Order {order_id} confirmed successfully",
            evidence=[
                f"order_id={order_id}",
                f"patient_id={patient_id}",
                f"medicine={medicine_name}",
                f"quantity={quantity}",
                f"total=₹{total:.2f}"
            ],
            message=summary,
            next_agent=None,
            ui_card="order_confirmation",
            ui_data={
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
        )

    def _show_prescription_upload(self, params: dict) -> AgentOutput:
        """Display prescription upload card."""
        medicine_name = params.get("medicine_name", "")
        medicine_id = params.get("medicine_id", "")
        is_controlled = params.get("is_controlled", False)
        
        msg = f"{medicine_name} is a controlled substance" if is_controlled else f"{medicine_name} requires a prescription"
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.NEEDS_INFO,
            reason=f"Prescription required for {medicine_name}",
            evidence=[f"medicine={medicine_name}", f"controlled={is_controlled}"],
            message=f"{msg}. Please upload your prescription.",
            next_agent=None,
            ui_card="prescription_upload",
            ui_data={
                "medicine_name": medicine_name,
                "medicine_id": medicine_id,
                "requires_prescription": True,
                "is_controlled": is_controlled,
                "message": msg
            }
        )

    def _check_refills(self, params: dict, patient_id: str) -> AgentOutput:
        """Request refill predictions from RefillPredictionAgent."""
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.NEEDS_INFO,
            reason=f"Checking refill predictions for patient {patient_id}",
            evidence=[f"patient_id={patient_id}"],
            message="Let me check your upcoming refills...",
            next_agent="RefillPredictionAgent"
        )

    def get_ui_card_data(self, result: AgentOutput) -> tuple:
        """Extract UI card data if present."""
        if hasattr(result, 'ui_card') and result.ui_card:
            return result.ui_card, getattr(result, 'ui_data', None)
        return None, None

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def get_trace_id(self) -> Optional[str]:
        return get_trace_id()
