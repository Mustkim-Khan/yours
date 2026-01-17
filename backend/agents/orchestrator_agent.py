"""
Orchestrator Agent - LangChain Agent Coordinator
Routes user requests to appropriate agents and aggregates responses.
All agents emit standardized output: {agent, decision, reason, evidence, message, next_agent}
"""

import os
from typing import Optional, Dict, Any, List

from langchain_openai import ChatOpenAI
from langsmith import traceable

from models.schemas import (
    Decision,
    AgentOutput,
    OrchestratorRequest,
    OrchestratorResponse,
    AgentAction,
    AgentDecision,
    UICardType,
    OrderPreviewData,
    OrderPreviewItem,
    OrderConfirmationData,
    PrescriptionUploadData,
)
from utils.tracing import orchestrator_span, child_agent_span, get_trace_id

from .pharmacist_agent import PharmacistAgent
from .inventory_agent import InventoryAgent
from .policy_agent import PolicyAgent
from .fulfillment_agent import FulfillmentAgent
from .refill_prediction_agent import RefillPredictionAgent


class OrchestratorAgent:
    """
    OrchestratorAgent - Central coordinator for all agents.
    
    All agents emit standardized output:
    {agent, decision, reason, evidence, message, next_agent}
    
    Model assignments:
    - PharmacistAgent: gpt-5-mini
    - InventoryAgent: gpt-5.2 (precision)
    - PolicyAgent: gpt-5.2 (precision)
    - FulfillmentAgent: gpt-5-mini
    - RefillPredictionAgent: gpt-5-mini
    """

    def __init__(self):
        self.agent_name = "OrchestratorAgent"
        
        # Initialize all sub-agents
        self.pharmacist = PharmacistAgent()       # gpt-5-mini
        self.inventory = InventoryAgent()          # gpt-5.2
        self.policy = PolicyAgent()                # gpt-5.2
        self.fulfillment = FulfillmentAgent()      # gpt-5-mini
        self.refill = RefillPredictionAgent()      # gpt-5-mini
        
        self._data_service = None
        
        # Session state tracking - stores order previews per session
        self._session_states: Dict[str, Dict[str, Any]] = {}

    def set_data_service(self, data_service):
        """Inject data service into all agents"""
        self._data_service = data_service
        self.inventory.set_data_service(data_service)
        self.policy.set_data_service(data_service)
        self.fulfillment.set_data_service(data_service)
        self.refill.set_data_service(data_service)
    
    def _is_confirmation_message(self, message: str) -> bool:
        """Check if user message is a confirmation"""
        confirm_words = ['confirm', 'yes', 'proceed', 'ok', 'place order', 'place the order', 
                         'go ahead', 'continue', 'submit', 'approve', 'done', 'complete']
        msg_lower = message.lower().strip()
        return any(word in msg_lower for word in confirm_words)
    
    def _get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get or create session state"""
        if session_id not in self._session_states:
            self._session_states[session_id] = {}
        return self._session_states[session_id]
    
    def _save_order_preview(self, session_id: str, preview_data: 'OrderPreviewData'):
        """Save order preview to session state"""
        state = self._get_session_state(session_id)
        state['order_preview'] = preview_data
        state['has_preview'] = True
    
    def _get_order_preview(self, session_id: str) -> Optional['OrderPreviewData']:
        """Get order preview from session state"""
        state = self._get_session_state(session_id)
        return state.get('order_preview')
    
    def _clear_order_preview(self, session_id: str):
        """Clear order preview from session state"""
        state = self._get_session_state(session_id)
        state['order_preview'] = None
        state['has_preview'] = False

    @orchestrator_span
    async def process_request(
        self, 
        request: OrchestratorRequest
    ) -> OrchestratorResponse:
        """
        Process a user request through the agent chain.
        Each agent emits: {agent, decision, reason, evidence, message, next_agent}
        """
        agent_chain = [self.agent_name]
        decisions_made: List[AgentDecision] = []
        all_evidence: List[str] = []
        safety_warnings: List[str] = []
        order_created = None
        requires_prescription = False
        
        # UI Card data
        ui_card_type = UICardType.NONE
        order_preview_data = None
        order_confirmation_data = None
        prescription_upload_data = None
        
        # Check if user is confirming a previous order preview
        if self._is_confirmation_message(request.user_message):
            saved_preview = self._get_order_preview(request.session_id)
            if saved_preview:
                # User is confirming - delegate to FulfillmentAgent
                agent_chain.append("PharmacistAgent")
                agent_chain.append("FulfillmentAgent")
                
                # Clear the preview
                self._clear_order_preview(request.session_id)
                
                # Delegate to FulfillmentAgent to confirm order
                agent_output, order_confirmation_data, summary = await self.fulfillment.confirm_order(
                    saved_preview,
                    saved_preview.patient_name
                )
                
                if order_confirmation_data:
                    ui_card_type = UICardType.ORDER_CONFIRMATION
                    order_created = order_confirmation_data.order_id
                    
                    return OrchestratorResponse(
                        session_id=request.session_id,
                        response_text=summary,
                        agent_chain=agent_chain,
                        decisions_made=[self._to_agent_decision(agent_output)],
                        final_action=AgentAction.CREATE_ORDER,
                        order_created=order_created,
                        requires_prescription=False,
                        safety_warnings=[],
                        trace_id=get_trace_id(),
                        ui_card_type=ui_card_type,
                        order_preview_data=None,
                        order_confirmation_data=order_confirmation_data,
                        prescription_upload_data=None
                    )
        
        # Step 1: PharmacistAgent processes initial message
        pharmacist_output = await self._delegate_to_pharmacist(
            request.user_message,
            request.session_id,
            request.patient_id
        )
        
        agent_chain.append("PharmacistAgent")
        decisions_made.append(self._to_agent_decision(pharmacist_output))
        all_evidence.extend(pharmacist_output.evidence)
        
        current_output = pharmacist_output
        final_message = pharmacist_output.message or ""
        
        # Step 2: Follow next_agent chain
        max_hops = 5
        hops = 0
        
        while current_output.next_agent and hops < max_hops:
            next_agent = current_output.next_agent
            hops += 1
            
            if next_agent == "InventoryAgent":
                current_output = await self._delegate_to_inventory(all_evidence)
                agent_chain.append("InventoryAgent")
                
            elif next_agent == "PolicyAgent":
                current_output = await self._delegate_to_policy(all_evidence)
                agent_chain.append("PolicyAgent")
                if current_output.decision == Decision.NEEDS_INFO:
                    requires_prescription = True
                
            elif next_agent == "FulfillmentAgent":
                current_output = await self._delegate_to_fulfillment(
                    all_evidence, request.patient_id
                )
                agent_chain.append("FulfillmentAgent")
                if current_output.decision == Decision.APPROVED:
                    # Extract order_id from evidence
                    for ev in current_output.evidence:
                        if ev.startswith("order_id="):
                            order_created = ev.split("=")[1]
                            break
                
            elif next_agent == "RefillPredictionAgent":
                current_output = await self._delegate_to_refill(
                    request.patient_id or ""
                )
                agent_chain.append("RefillPredictionAgent")
                
            elif next_agent == "PharmacistAgent":
                # Return to PharmacistAgent with context
                break
            else:
                break
            
            decisions_made.append(self._to_agent_decision(current_output))
            all_evidence.extend(current_output.evidence)
            
            # Update final_message if agent provides one
            if current_output.message:
                final_message = current_output.message
            
            # Check for prescription requirement in evidence
            for ev in current_output.evidence:
                if "requires_prescription=True" in ev or "prescription_required=True" in ev:
                    requires_prescription = True
                if "controlled_substance=True" in ev:
                    requires_prescription = True
                    safety_warnings.append("Controlled substance requires special handling")
        
        # Extract order details from evidence
        order_info = self._extract_order_info(all_evidence)
        
        # Build final response - use reason if no message available
        if not final_message or "Let me check" in final_message:
            # Generate user-friendly message based on final decision
            final_message = self._build_response_message(current_output, all_evidence, requires_prescription)
        
        # Generate order preview card if we have medicine and quantity
        if (current_output.decision == Decision.APPROVED and 
            order_info.get("medicine_name") and 
            order_info.get("quantity")):
            
            ui_card_type = UICardType.ORDER_PREVIEW
            
            # Get price from data service if available
            unit_price = 5.00  # Default price
            if self._data_service:
                med = self._data_service.get_medicine_by_id(order_info.get("medicine_id", ""))
                if not med:
                    meds = self._data_service.search_medicine(order_info["medicine_name"])
                    if meds:
                        med = meds[0]
                if med:
                    # Use price_per_unit if available, otherwise default
                    unit_price = getattr(med, 'price', 5.00) or 5.00
            
            quantity = int(order_info["quantity"])
            
            # Look up actual patient name
            patient_name = "Guest Customer"
            if request.patient_id and self._data_service:
                patients = self._data_service.get_all_patients()
                patient = next((p for p in patients if p.patient_id == request.patient_id), None)
                if patient:
                    patient_name = patient.patient_name
            
            order_preview_data = OrderPreviewData(
                preview_id=f"PRV-{request.session_id[:8].upper()}",
                patient_id=request.patient_id or "GUEST",
                patient_name=patient_name,
                items=[OrderPreviewItem(
                    medicine_id=order_info.get("medicine_id", ""),
                    medicine_name=order_info["medicine_name"],
                    strength=order_info.get("strength", ""),
                    quantity=quantity,
                    prescription_required=requires_prescription,
                    unit_price=unit_price,
                    supply_days=quantity
                )],
                total_amount=(unit_price * quantity) * 1.05 + 2.00,  # subtotal + 5% tax + $2 delivery
                safety_decision="APPROVE" if not requires_prescription else "NEEDS_PRESCRIPTION",
                safety_reasons=safety_warnings,
                requires_prescription=requires_prescription
            )
            
            # Save order preview to session for later confirmation
            self._save_order_preview(request.session_id, order_preview_data)
        
        final_action = self._decision_to_action(current_output.decision)
        
        return OrchestratorResponse(
            session_id=request.session_id,
            response_text=final_message,
            agent_chain=agent_chain,
            decisions_made=decisions_made,
            final_action=final_action,
            order_created=order_created,
            requires_prescription=requires_prescription,
            safety_warnings=safety_warnings,
            trace_id=get_trace_id(),
            ui_card_type=ui_card_type,
            order_preview_data=order_preview_data,
            order_confirmation_data=order_confirmation_data,
            prescription_upload_data=prescription_upload_data
        )
    
    def _extract_order_info(self, evidence: List[str]) -> Dict[str, str]:
        """Extract order information from evidence list."""
        info = {}
        for ev in evidence:
            if ev.startswith("medicine_name="):
                info["medicine_name"] = ev.split("=")[1]
            elif ev.startswith("medicine_id="):
                info["medicine_id"] = ev.split("=")[1]
            elif ev.startswith("quantity=") or ev.startswith("qty="):
                info["quantity"] = ev.split("=")[1]
            elif ev.startswith("strength="):
                info["strength"] = ev.split("=")[1]
            elif ev.startswith("form="):
                info["form"] = ev.split("=")[1]
        return info
    
    def _build_response_message(
        self, 
        output: AgentOutput, 
        evidence: List[str],
        requires_prescription: bool
    ) -> str:
        """Build a user-friendly response message from agent output."""
        # Extract info from evidence
        medicine_name = ""
        strength = ""
        stock_status = ""
        quantity = ""
        form = ""
        
        for ev in evidence:
            if ev.startswith("medicine_name="):
                medicine_name = ev.split("=")[1]
            elif ev.startswith("strength="):
                strength = ev.split("=")[1]
            elif ev.startswith("stock_status="):
                stock_status = ev.split("=")[1]
            elif ev.startswith("quantity=") or ev.startswith("qty="):
                quantity = ev.split("=")[1]
            elif ev.startswith("form="):
                form = ev.split("=")[1]
        
        medicine_full = f"{medicine_name} {strength}".strip() if medicine_name else "the medicine"
        
        if output.decision == Decision.APPROVED:
            # If quantity is already provided, proceed to order preview
            if quantity:
                if requires_prescription:
                    return f"Perfect! {quantity} {form or 'units'} of {medicine_full} coming right up. This medication requires a prescription - please upload it to continue."
                else:
                    return f"Perfect! I'll prepare an order for {quantity} {form or 'units'} of {medicine_full}."
            else:
                # No quantity provided - ask for it
                msg = f"Yes, {medicine_full} is available."
                if requires_prescription:
                    msg += " This medication requires a valid prescription."
                msg += " How many would you like to order?"
                return msg
            
        elif output.decision == Decision.REJECTED:
            if "out_of_stock" in stock_status or "out of stock" in output.reason.lower():
                return f"I'm sorry, {medicine_full} is currently out of stock. Would you like me to check for alternatives or notify you when it's back?"
            elif "discontinued" in output.reason.lower():
                return f"I'm sorry, {medicine_full} has been discontinued. I can suggest some alternatives if you'd like."
            else:
                return output.reason or f"I'm sorry, {medicine_full} is not available at the moment."
        
        elif output.decision == Decision.NEEDS_INFO:
            return output.reason or f"I need some more details about {medicine_full}. Could you please provide more information?"
        
        else:
            return output.reason or "How can I help you today?"

    def _to_agent_decision(self, output: AgentOutput) -> AgentDecision:
        """Convert AgentOutput to AgentDecision for compatibility"""
        return AgentDecision(
            agent_name=output.agent,
            action=self._decision_to_action(output.decision),
            reasoning=output.reason,
            confidence=0.9 if output.decision == Decision.APPROVED else 0.7
        )

    def _decision_to_action(self, decision: Decision) -> AgentAction:
        """Map Decision to AgentAction"""
        mapping = {
            Decision.APPROVED: AgentAction.CREATE_ORDER,
            Decision.REJECTED: AgentAction.PROVIDE_SAFETY_WARNING,
            Decision.NEEDS_INFO: AgentAction.ANSWER_QUERY,
            Decision.SCHEDULED: AgentAction.PREDICT_REFILL,
        }
        return mapping.get(decision, AgentAction.ANSWER_QUERY)

    async def _delegate_to_pharmacist(
        self,
        message: str,
        session_id: str,
        patient_id: Optional[str]
    ) -> AgentOutput:
        """Delegate to PharmacistAgent"""
        # Look up patient name
        patient_name = None
        if patient_id and self._data_service:
            patients = self._data_service.get_all_patients()
            patient = next((p for p in patients if p.patient_id == patient_id), None)
            if patient:
                patient_name = patient.patient_name
        
        return await self.pharmacist.process_message(message, session_id, patient_id, patient_name)

    async def _delegate_to_inventory(
        self, 
        evidence: List[str]
    ) -> AgentOutput:
        """Delegate to InventoryAgent"""
        # Extract medicine name from evidence
        medicine_name = ""
        dosage = None
        form = None
        
        for ev in evidence:
            if ev.startswith("medicine_name="):
                medicine_name = ev.split("=")[1]
            elif ev.startswith("dosage="):
                dosage = ev.split("=")[1]
            elif ev.startswith("form="):
                form = ev.split("=")[1]
        
        return await self.inventory.check_stock(medicine_name, form, dosage)

    async def _delegate_to_policy(
        self, 
        evidence: List[str]
    ) -> AgentOutput:
        """Delegate to PolicyAgent"""
        medicine_name = ""
        for ev in evidence:
            if ev.startswith("medicine_name="):
                medicine_name = ev.split("=")[1]
                break
        
        return await self.policy.check_prescription_required(medicine_name)

    async def _delegate_to_fulfillment(
        self, 
        evidence: List[str],
        patient_id: Optional[str]
    ) -> AgentOutput:
        """Delegate to FulfillmentAgent"""
        # Build items from evidence
        items = []
        medicine_id = ""
        medicine_name = ""
        quantity = 1
        
        for ev in evidence:
            if ev.startswith("medicine_id="):
                medicine_id = ev.split("=")[1]
            elif ev.startswith("medicine_name="):
                medicine_name = ev.split("=")[1]
            elif ev.startswith("quantity=") or ev.startswith("qty="):
                try:
                    quantity = int(ev.split("=")[1])
                except ValueError:
                    pass
        
        if medicine_name:
            items.append({
                "medicine_id": medicine_id or f"MED-{medicine_name[:3].upper()}",
                "medicine_name": medicine_name,
                "quantity": quantity,
                "unit_price": 5.00
            })
        
        return await self.fulfillment.create_order(
            patient_id or "GUEST",
            items,
            "pickup"
        )

    async def _delegate_to_refill(
        self, 
        patient_id: str
    ) -> AgentOutput:
        """Delegate to RefillPredictionAgent"""
        return await self.refill.get_refill_predictions(patient_id)

    def get_trace_id(self) -> Optional[str]:
        return get_trace_id()


# Convenience function
async def process_user_message(
    message: str,
    session_id: str = "default",
    patient_id: Optional[str] = None,
    data_service = None
) -> OrchestratorResponse:
    """Process a user message through the full agent chain."""
    orchestrator = OrchestratorAgent()
    if data_service:
        orchestrator.set_data_service(data_service)
    
    request = OrchestratorRequest(
        session_id=session_id,
        user_message=message,
        patient_id=patient_id
    )
    
    return await orchestrator.process_request(request)
