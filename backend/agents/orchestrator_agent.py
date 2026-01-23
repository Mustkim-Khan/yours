"""
Orchestrator Agent - LangChain Agent Coordinator
Routes user requests to appropriate agents and aggregates responses.
All agents emit standardized output: {agent, decision, reason, evidence, message, next_agent}
"""

import os
import json
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
from utils.tracing import (
    orchestrator_span, child_agent_span, get_trace_id,
    set_session_trace, get_session_trace, clear_session_trace
)

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
    - PharmacistAgent: gpt-5.2
    - InventoryAgent: gpt-5-mini
    - PolicyAgent: gpt-5.2 (precision)
    - FulfillmentAgent: gpt-5-mini
    - RefillPredictionAgent: gpt-5-mini
    """

    def __init__(self):
        self.agent_name = "OrchestratorAgent"
        
        # Initialize all sub-agents
        self.pharmacist = PharmacistAgent()       
        self.inventory = InventoryAgent()        
        self.policy = PolicyAgent()          
        self.fulfillment = FulfillmentAgent()     
        self.refill = RefillPredictionAgent()     
        
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

    # ============ PRESCRIPTION FLOW SESSION STATE ============
    
    def _save_pending_prescription(
        self, 
        session_id: str, 
        order_info: Dict[str, str],
        evidence: List[str],
        patient_id: str,
        user_name: Optional[str] = None  # Firestore user name for deterministic injection
    ):
        """Save pending prescription order to session for later resume."""
        state = self._get_session_state(session_id)
        state['pending_prescription'] = {
            'order_info': order_info,
            'evidence': evidence,
            'patient_id': patient_id,
            'user_name': user_name,  # Store for deterministic use in resume
            'requires_prescription': True,
            'prescription_uploaded': False,
            'prescription_verified': False
        }
    
    def _get_pending_prescription(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get pending prescription order from session."""
        state = self._get_session_state(session_id)
        return state.get('pending_prescription')
    
    def _mark_prescription_uploaded(self, session_id: str):
        """Mark prescription as uploaded and verified."""
        state = self._get_session_state(session_id)
        if 'pending_prescription' in state:
            state['pending_prescription']['prescription_uploaded'] = True
            state['pending_prescription']['prescription_verified'] = True
    
    def _clear_pending_prescription(self, session_id: str):
        """Clear pending prescription from session."""
        state = self._get_session_state(session_id)
        state.pop('pending_prescription', None)

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
                
                # Get phone number from user profile if available
                patient_phone = None
                patient_name = request.user_name
                
                if self._data_service and request.user_id:
                    contact = self._data_service.get_user_contact(request.user_id)
                    patient_phone = contact.get("phone")
                    # Prefer Firestore name if available
                    if contact.get("name"):
                        patient_name = contact.get("name")
                
                # Delegate to FulfillmentAgent to confirm order
                agent_output, order_confirmation_data, summary = await self.fulfillment.confirm_order(
                    saved_preview,
                    patient_name or saved_preview.patient_name,
                    request.user_id,
                    patient_phone  # NEW: Pass phone for WhatsApp
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
            request.patient_id,
            request.user_name,  # Pass user_name from Firestore
            request.user_id,    # Pass user_id for persistence
            request.conversation_id  # Pass Firestore conversation ID for history
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
                    # Extract order details
                    order_info = self._extract_order_info(all_evidence)
                    medicine_name = order_info.get("medicine_name", "This medication")
                    medicine_id = order_info.get("medicine_id", "")
                    dosage = order_info.get("strength") or order_info.get("dosage", "")
                    
                    # 1. CHECK FOR EXISTING VALID PRESCRIPTION IN FIRESTORE
                    has_valid_rx = False
                    if self._data_service and request.user_id:
                        has_valid_rx = self._data_service.has_valid_prescription(
                            request.user_id,
                            medicine_name,
                            dosage
                        )
                    
                    if has_valid_rx:
                        # BYPASS UPLOAD -> GO STRAIGHT TO PREVIEW
                        print(f"✅ Reusing existing prescription for {medicine_name}")
                        
                        # Generate Order Preview Immediately
                        quantity = int(order_info.get("quantity", 1))
                        unit_price = 5.00
                        if self._data_service:
                            meds = self._data_service.search_medicine(medicine_name)
                            if meds:
                                unit_price = getattr(meds[0], 'price', 5.00) or 5.00
                        
                        ui_card_type = UICardType.ORDER_PREVIEW
                        
                        # Use strictly defined message
                        final_message = f"Thank you for confirming. Our records indicate you already have a valid prescription for {medicine_name} {dosage}. Please review the details below and confirm to proceed."
                        
                        # Build Preview Data
                        order_preview_data = OrderPreviewData(
                            preview_id=f"PRV-{request.session_id[:8].upper()}",
                            patient_id=request.patient_id or "GUEST",
                            patient_name=request.user_name or "Guest Customer",
                            items=[OrderPreviewItem(
                                medicine_id=medicine_id,
                                medicine_name=medicine_name,
                                strength=dosage,
                                quantity=quantity,
                                prescription_required=True,
                                unit_price=unit_price,
                                supply_days=quantity
                            )],
                            total_amount=(unit_price * quantity) * 1.05 + 2.00,
                            safety_decision="APPROVE",
                            safety_reasons=[],
                            requires_prescription=True
                        )
                        
                        # Save state so "confirm" works
                        self._save_order_preview(request.session_id, order_preview_data)
                        
                        # Break loop to return immediatley
                        decisions_made.append(self._to_agent_decision(current_output))
                        break

                    else:
                        # ORIGINAL FLOW: Request Upload
                        self._save_pending_prescription(
                            request.session_id,
                            order_info,
                            all_evidence.copy(),
                            request.patient_id or "GUEST",
                            request.user_name
                        )
                        # Set UI card type to show PrescriptionUploadCard
                        ui_card_type = UICardType.PRESCRIPTION_UPLOAD
                        is_controlled = any("controlled_substance=True" in ev for ev in all_evidence)
                        prescription_upload_data = PrescriptionUploadData(
                            medicine_name=medicine_name,
                            medicine_id=medicine_id,
                            requires_prescription=True,
                            is_controlled=is_controlled,
                            message=f"{medicine_name} requires a valid prescription. Please upload your prescription to continue."
                        )
                        # Break the chain - wait for prescription upload
                        decisions_made.append(self._to_agent_decision(current_output))
                        all_evidence.extend(current_output.evidence)
                        final_message = f"{medicine_name} requires a valid prescription. Please upload your prescription to proceed with the order."
                        break
                
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
                    request.patient_id or "",
                    request.user_id
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
            # Check for prescription requirement in evidence
            for ev in current_output.evidence:
                if "requires_prescription=True" in ev or "prescription_required=True" in ev:
                    requires_prescription = True
                
                # Check inside structured item_data
                if ev.startswith("item_data="):
                    try:
                        import json
                        item_data = json.loads(ev.split("=", 1)[1])
                        if item_data.get("prescription_required") is True:
                            requires_prescription = True
                    except:
                        pass
                        
                if "controlled_substance=True" in ev:
                    requires_prescription = True
                    safety_warnings.append("Controlled substance requires special handling")
        
        # Extract order details from evidence
        order_info = self._extract_order_info(all_evidence)
        
        # Build final response - use reason if no message available
        if not final_message or "Let me check" in final_message:
            # Generate user-friendly message based on final decision
            final_message = self._build_response_message(current_output, all_evidence, requires_prescription)
        
        # Generate order preview card if we have items
        if (current_output.decision == Decision.APPROVED and 
            order_info.get("items")):
            
            ui_card_type = UICardType.ORDER_PREVIEW
            
            # Build items for order preview from extracted order_info
            preview_items = []
            total_subtotal = 0.0
            any_requires_prescription = requires_prescription
            
            for item_data in order_info["items"]:
                # Get price from data service if available
                unit_price = 5.00  # Default price
                if self._data_service:
                    med = self._data_service.get_medicine_by_id(item_data.get("medicine_id", ""))
                    if not med:
                        meds = self._data_service.search_medicine(item_data["medicine_name"])
                        if meds:
                            med = meds[0]
                    if med:
                        unit_price = getattr(med, 'price', 5.00) or 5.00
                        # Check per-item prescription requirement
                        if med.prescription_required:
                            any_requires_prescription = True
                
                quantity = int(item_data.get("quantity", 1))
                item_subtotal = unit_price * quantity
                total_subtotal += item_subtotal
                
                preview_items.append(OrderPreviewItem(
                    medicine_id=item_data.get("medicine_id", ""),
                    medicine_name=item_data["medicine_name"],
                    strength=item_data.get("strength", ""),
                    quantity=quantity,
                    prescription_required=requires_prescription,
                    unit_price=unit_price,
                    supply_days=quantity
                ))
            
            # DETERMINISTIC: Use Firestore user_name, never infer from demo CSV
            patient_name = request.user_name or "Guest Customer"
            
            # Calculate total: subtotal + 5% tax + $2 delivery
            total_amount = total_subtotal * 1.05 + 2.00
            
            order_preview_data = OrderPreviewData(
                preview_id=f"PRV-{request.session_id[:8].upper()}",
                patient_id=request.patient_id or "GUEST",
                patient_name=patient_name,
                items=preview_items,
                total_amount=total_amount,
                safety_decision="APPROVE" if not any_requires_prescription else "NEEDS_PRESCRIPTION",
                safety_reasons=safety_warnings,
                requires_prescription=any_requires_prescription
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
    
    def _extract_order_info(self, evidence: List[str]) -> Dict[str, Any]:
        """
        Extract order information from evidence list.
        Returns dict with 'items' list for multi-item support.
        Single-item fields (medicine_name, etc) are kept for backward compatibility.
        """
        info = {"items": []}
        legacy_info = {}
        
        # Deduplication map: med_name_lower -> List[item_dict]
        # We use a list to handle multiple variants (e.g. 500mg and 650mg) of the same medicine
        items_map = {}
        
        for ev in evidence:
            # NEW: Parse structured item data (preferred)
            if ev.startswith("item_data="):
                try:
                    item_json = ev.split("=", 1)[1]
                    item_data = json.loads(item_json)
                    
                    # Generate key details
                    med = item_data.get("medicine_name", "").strip().lower()
                    new_strength = item_data.get("strength", "").strip().lower()
                    
                    if med:
                        if med not in items_map:
                            items_map[med] = [item_data]
                        else:
                            # Try to find compatible item to merge
                            merged = False
                            for existing_item in items_map[med]:
                                existing_strength = existing_item.get("strength", "").strip().lower()
                                
                                # Merge if strengths match OR one is missing (refinement)
                                if existing_strength == new_strength or not existing_strength or not new_strength:
                                    existing_item.update(item_data)
                                    merged = True
                                    break
                            
                            if not merged:
                                items_map[med].append(item_data)
                            
                except Exception as e:
                    print(f"Failed to parse item_data: {e}")
            
            # LEGACY: Parse individual fields (fallback)
            elif ev.startswith("medicine_name="):
                legacy_info["medicine_name"] = ev.split("=")[1]
            elif ev.startswith("medicine_id="):
                legacy_info["medicine_id"] = ev.split("=")[1]
            elif ev.startswith("quantity=") or ev.startswith("qty="):
                legacy_info["quantity"] = ev.split("=")[1]
            elif ev.startswith("strength="):
                legacy_info["strength"] = ev.split("=")[1]
            elif ev.startswith("form="):
                legacy_info["form"] = ev.split("=")[1]
        
        # Populate items from map values (exclude None/Empty)
        info["items"] = []
        for item_list in items_map.values():
            info["items"].extend(item_list)
        
        # If no structured items found, build from legacy fields
        if not info["items"] and legacy_info.get("medicine_name"):
            info["items"].append({
                "medicine_id": legacy_info.get("medicine_id", ""),
                "medicine_name": legacy_info["medicine_name"],
                "strength": legacy_info.get("strength", ""),
                "quantity": legacy_info.get("quantity", "1"),
                "form": legacy_info.get("form", "")
            })
            
        # Ensure root backward-compatibility fields are set from first item
        if info["items"]:
            first_item = info["items"][0]
            info["medicine_name"] = first_item.get("medicine_name", "")
            info["quantity"] = str(first_item.get("quantity", 1))
            info["medicine_id"] = first_item.get("medicine_id", "")
            info["strength"] = first_item.get("strength", "")
            info["form"] = first_item.get("form", "")
            
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
                msg = f"Yes, we have {medicine_full} available in our store."
                if requires_prescription:
                    msg += " Please note that this medication requires a valid prescription."
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

    # ============ PRESCRIPTION RESUME FLOW ============
    
    # NOTE: NO @orchestrator_span here - this is a continuation, not a new root
    async def resume_with_prescription(
        self,
        session_id: str,
        medicine_id: str,
        prescription_verified: bool = True
    ) -> OrchestratorResponse:
        """
        Resume order flow after prescription upload.
        Returns ORDER_PREVIEW (not ORDER_CONFIRMATION).
        FulfillmentAgent is called when user confirms the preview.
        
        Flow:
        1. Prescription upload → ORDER_PREVIEW
        2. User clicks Confirm Order → FulfillmentAgent → ORDER_CONFIRMATION
        """
        # Get pending prescription from session
        pending = self._get_pending_prescription(session_id)
        
        if not pending:
            # Check if we already have a saved order preview (double-click prevention)
            saved_preview = self._get_order_preview(session_id)
            if saved_preview:
                # Return the existing preview - don't create error message
                medicine_name = saved_preview.items[0].medicine_name if saved_preview.items else "your medicine"
                return OrchestratorResponse(
                    session_id=session_id,
                    response_text=f"Prescription verified! Your order for {medicine_name} is ready for confirmation.",
                    agent_chain=[self.agent_name, "PolicyAgent:prescription_verified"],
                    decisions_made=[],
                    final_action=AgentAction.ANSWER_QUERY,
                    order_created=None,
                    requires_prescription=True,
                    safety_warnings=[],
                    trace_id=get_trace_id(),
                    ui_card_type=UICardType.ORDER_PREVIEW,
                    order_preview_data=saved_preview,
                    order_confirmation_data=None,
                    prescription_upload_data=None
                )
            # No pending prescription and no saved preview - show error
            return OrchestratorResponse(
                session_id=session_id,
                response_text="Please start a new order to continue.",
                agent_chain=[self.agent_name],
                decisions_made=[],
                final_action=AgentAction.ANSWER_QUERY,
                order_created=None,
                requires_prescription=True,
                safety_warnings=[],
                trace_id=get_trace_id(),
                ui_card_type=UICardType.NONE,
                order_preview_data=None,
                order_confirmation_data=None,
                prescription_upload_data=None
            )
        
        # Mark prescription as uploaded and verified
        self._mark_prescription_uploaded(session_id)
        
        order_info = pending['order_info']
        patient_id = pending['patient_id']
        
        # Build agent chain - showing prescription verified
        agent_chain = [self.agent_name, "PolicyAgent:prescription_verified"]
        
        medicine_name = order_info.get("medicine_name", "your medicine")
        
        # DETERMINISTIC: Use stored user_name from session, never lookup demo CSV
        # Note: For prescription flow, name comes from pending prescription or fallback
        patient_name = pending.get('user_name') or "Guest Customer"
        
        # Get price and build order preview
        quantity = int(order_info.get("quantity", 1))
        unit_price = 5.00  # Default
        if self._data_service:
            meds = self._data_service.search_medicine(medicine_name)
            if meds:
                unit_price = getattr(meds[0], 'price', 5.00) or 5.00
        
        # Calculate totals ONCE - this is the single source of truth
        subtotal = unit_price * quantity
        tax = subtotal * 0.05
        delivery_fee = 2.00
        total_amount = subtotal + tax + delivery_fee
        
        # Build ORDER PREVIEW (NOT confirmation)
        order_preview_data = OrderPreviewData(
            preview_id=f"PRV-{session_id[:8].upper()}",
            patient_id=patient_id,
            patient_name=patient_name,
            items=[OrderPreviewItem(
                medicine_id=order_info.get("medicine_id", ""),
                medicine_name=medicine_name,
                strength=order_info.get("strength", ""),
                quantity=quantity,
                prescription_required=True,
                unit_price=unit_price,
                supply_days=quantity
            )],
            total_amount=total_amount,  # Use consistent total
            safety_decision="APPROVE",
            safety_reasons=[],
            requires_prescription=True
        )
        
        # Save order preview for later confirmation
        self._save_order_preview(session_id, order_preview_data)
        
        # Clear pending prescription (it's now been converted to order preview)
        self._clear_pending_prescription(session_id)
        
        final_message = f"Prescription verified! Your order for {medicine_name} is ready for confirmation."
        
        return OrchestratorResponse(
            session_id=session_id,
            response_text=final_message,
            agent_chain=agent_chain,
            decisions_made=[],
            final_action=AgentAction.ANSWER_QUERY,
            order_created=None,
            requires_prescription=True,
            safety_warnings=[],
            trace_id=get_trace_id(),
            ui_card_type=UICardType.ORDER_PREVIEW,
            order_preview_data=order_preview_data,
            order_confirmation_data=None,
            prescription_upload_data=None
        )

    def _build_order_confirmation(
        self,
        order_id: str,
        order_info: Dict[str, str],
        patient_id: str,
        user_name: Optional[str] = None  # Firestore user name (deterministic)
    ) -> OrderConfirmationData:
        """Build order confirmation data from order info."""
        from datetime import datetime
        
        # DETERMINISTIC: Use Firestore user_name, never lookup demo CSV
        patient_name = user_name or "Guest Customer"
        
        quantity = int(order_info.get("quantity", 1))
        unit_price = 5.00  # Default
        
        # Try to get actual price
        if self._data_service:
            meds = self._data_service.search_medicine(order_info.get("medicine_name", ""))
            if meds:
                unit_price = getattr(meds[0], 'price', 5.00) or 5.00
        
        subtotal = unit_price * quantity
        tax = subtotal * 0.05
        delivery_fee = 2.00
        total = subtotal + tax + delivery_fee
        
        return OrderConfirmationData(
            order_id=order_id,
            preview_id=None,
            patient_id=patient_id,
            patient_name=patient_name,
            items=[OrderPreviewItem(
                medicine_id=order_info.get("medicine_id", ""),
                medicine_name=order_info.get("medicine_name", ""),
                strength=order_info.get("strength", ""),
                quantity=quantity,
                prescription_required=True,
                unit_price=unit_price,
                supply_days=quantity
            )],
            subtotal=subtotal,
            tax=tax,
            delivery_fee=delivery_fee,
            total_amount=total,
            safety_decision="APPROVE",
            safety_reasons=[],
            requires_prescription=True,
            status="CONFIRMED",
            created_at=datetime.now().isoformat(),
            estimated_delivery="Ready in 2 hours"
        )

    async def _delegate_to_pharmacist(
        self,
        message: str,
        session_id: str,
        patient_id: Optional[str],
        user_name: Optional[str] = None,  # User name from Firestore (priority)
        user_id: Optional[str] = None,    # User ID for persistence
        conversation_id: Optional[str] = None  # Firestore conversation ID for history
    ) -> AgentOutput:
        """Delegate to PharmacistAgent"""
        # Use user_name from Firestore if provided, otherwise fallback to demo patient lookup
        patient_name = user_name
        if not patient_name and patient_id and self._data_service:
            patients = self._data_service.get_all_patients()
            patient = next((p for p in patients if p.patient_id == patient_id), None)
            if patient:
                patient_name = patient.patient_name
        
        return await self.pharmacist.process_message(
            message, session_id, patient_id, patient_name, user_id, conversation_id
        )


    async def _delegate_to_inventory(
        self, 
        evidence: List[str]
    ) -> AgentOutput:
        """Delegate to InventoryAgent"""
        # Extract medicine name from evidence
        medicine_name = ""
        dosage = None
        form = None
        items = []
        
        for ev in evidence:
            if ev.startswith("item_data="):
                try:
                    import json
                    item_json = ev.split("=", 1)[1]
                    items.append(json.loads(item_json))
                except Exception as e:
                    print(f"Failed to parse item_data in delegation: {e}")
            elif ev.startswith("medicine_name="):
                medicine_name = ev.split("=")[1]
            elif ev.startswith("dosage="):
                dosage = ev.split("=")[1]
            elif ev.startswith("form="):
                form = ev.split("=")[1]
        
        return await self.inventory.check_stock(medicine_name, form, dosage, items=items)

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
            if ev.startswith("item_data="):
                try:
                    import json
                    item_json = ev.split("=", 1)[1]
                    item_data = json.loads(item_json)
                    # Mapping to Fulfillment item structure if needed
                    # Fulfillment expects: medicine_id, medicine_name, quantity, unit_price
                    # Inventory item_data has these (except unit_price might need default)
                    if "unit_price" not in item_data:
                        item_data["unit_price"] = 5.00
                    items.append(item_data)
                except:
                    pass
            elif ev.startswith("medicine_id="):
                medicine_id = ev.split("=")[1]
            elif ev.startswith("medicine_name="):
                medicine_name = ev.split("=")[1]
            elif ev.startswith("quantity=") or ev.startswith("qty="):
                try:
                    quantity = int(ev.split("=")[1])
                except ValueError:
                    pass
        
        # Fallback to legacy single item if no structured items found
        if not items and medicine_name:
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
        patient_id: str,
        user_id: Optional[str] = None
    ) -> AgentOutput:
        """Delegate to RefillPredictionAgent"""
        return await self.refill.get_refill_predictions(patient_id, user_id)

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
