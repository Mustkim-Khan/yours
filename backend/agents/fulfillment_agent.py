"""
FulfillmentAgent - LangChain Agent Implementation
Creates orders, updates inventory, triggers warehouse webhooks, generates receipts.
EMITS STANDARDIZED OUTPUT: {agent, decision, reason, evidence, message, next_agent}
Uses: gpt-5-mini
"""

import os
import uuid
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI

from models.schemas import (
    Decision, AgentOutput, OrderStatus, 
    OrderConfirmationData, OrderPreviewData, OrderPreviewItem
)
from utils.tracing import agent_trace, get_trace_id, create_non_traced_llm


# ============ MODEL CONFIG ============
MODEL_NAME = "gpt-5-mini"
TEMPERATURE = 0.3


class FulfillmentAgent:
    """
    FulfillmentAgent - Order processing and fulfillment.
    Uses gpt-5-mini model for fast order processing.
    
    EMITS STANDARDIZED OUTPUT:
    {agent, decision, reason, evidence, message, next_agent}
    """

    def __init__(self, model_name: str = MODEL_NAME, temperature: float = TEMPERATURE):
        self.agent_name = "FulfillmentAgent"
        self.model_name = model_name
        self.temperature = temperature
        # Direct OpenAI client for LLM calls
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Legacy LangChain LLM (for compatibility)
        self.llm = create_non_traced_llm(model_name, temperature)
        self._data_service = None
        self._orders: Dict[str, dict] = {}

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
                        "content": "You are a pharmacy fulfillment expert. Verify the decision logic. Output a concise justification (max 15 words)."
                    },
                    {
                        "role": "user",
                        "content": f"Context: {context}\nDecision: {decision}\nReasoning:"
                    }
                ],
                # temperature=0.1,  
                # max_tokens=200
                max_completion_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"FulfillmentAgent Reasoning Error: {e}")
            return f"{decision} based on order data (Fallback: {str(e)})"


    @agent_trace("FulfillmentAgent", "gpt-5-mini")
    async def create_order(
        self, 
        patient_id: str, 
        items: List[Dict[str, Any]],
        delivery_type: str = "pickup"
    ) -> AgentOutput:
        """
        Create a new order.
        Returns standardized AgentOutput.
        """
        if not items:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason="Cannot create order without items",
                evidence=["items_count=0"],
                message=None,
                next_agent=None
            )
        
        # Generate order ID
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate total
        total_amount = 0.0
        processed_items = []
        for item in items:
            quantity = item.get("quantity", 1)
            unit_price = item.get("unit_price", 5.00)
            item_total = quantity * unit_price
            total_amount += item_total
            processed_items.append({
                **item,
                "total_price": item_total
            })
        
        # Estimate delivery
        if delivery_type == "delivery":
            delivery_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            delivery_estimate = f"Tomorrow by 9:00 PM"
        else:
            delivery_time = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
            delivery_estimate = f"Ready for pickup in 2 hours"
        
        # Store order
        order_data = {
            "order_id": order_id,
            "patient_id": patient_id,
            "items": processed_items,
            "total_amount": total_amount,
            "status": OrderStatus.CONFIRMED.value,
            "delivery_type": delivery_type,
            "created_at": datetime.now().isoformat(),
            "delivery_estimate": delivery_estimate
        }
        self._orders[order_id] = order_data
        
        # Try to trigger warehouse webhook
        webhook_status = await self._trigger_webhook(order_data)
        
        item_names = [i.get("medicine_name", "item") for i in items]
        
        # Build detailed reason (2 lines as required)
        reason_line1 = f"Order {order_id} created successfully for {len(items)} item(s)."
        reason_line2 = f"Total: ${total_amount:.2f}. {delivery_estimate}. Warehouse notified."
        context = f"{reason_line1} {reason_line2}"
        reason = await self._generate_reasoning(context, "APPROVED")
        
        # Generate dynamic confirmation message using LLM
        llm_message = await self._generate_message(
            context=f"Order {order_id} for {', '.join(item_names)}, Total: ${total_amount:.2f}, Delivery: {delivery_estimate}",
            task="Generate a friendly order confirmation message"
        )
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=reason,
            evidence=[
                f"order_id={order_id}",
                f"patient_id={patient_id}",
                f"items_count={len(items)}",
                f"total_amount=${total_amount:.2f}",
                f"status=CONFIRMED",
                f"delivery_type={delivery_type}",
                f"delivery_estimate={delivery_estimate}",
                f"webhook_status={webhook_status}"
            ],
            message=llm_message,
            next_agent=None
        )

    async def _trigger_webhook(self, order_data: dict) -> str:
        """Trigger warehouse webhook"""
        webhook_url = os.getenv("WAREHOUSE_WEBHOOK_URL", "https://httpbin.org/post")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                payload = {
                    "event": "order_created",
                    "order_id": order_data["order_id"],
                    "items": order_data["items"],
                    "priority": "normal"
                }
                print(f"🚀 Triggering Webhook to {webhook_url}...")
                print(f"📦 Payload: {payload}")
                
                response = await client.post(webhook_url, json=payload)
                print(f"✅ Webhook Response: {response.status_code}")
                
                return "success" if response.status_code == 200 else "failed"
        except Exception:
            return "skipped"

    @agent_trace("FulfillmentAgent", "gpt-5-mini")
    async def get_order_status(self, order_id: str) -> AgentOutput:
        """
        Get status of an order.
        """
        order = self._orders.get(order_id)
        
        if not order:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"Order {order_id} not found",
                evidence=[f"order_id={order_id}"],
                message=None,
                next_agent=None
            )
        
        context = f"Order {order_id} is {order['status']}. Delivery: {order['delivery_estimate']}."
        reason = await self._generate_reasoning(context, "APPROVED")
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=reason,
            evidence=[
                f"order_id={order_id}",
                f"status={order['status']}",
                f"delivery_type={order['delivery_type']}",
                f"delivery_estimate={order['delivery_estimate']}"
            ],
            message=None,
            next_agent=None
        )

    @agent_trace("FulfillmentAgent", "gpt-5-mini")
    async def cancel_order(self, order_id: str, reason: str = "") -> AgentOutput:
        """
        Cancel an order.
        """
        order = self._orders.get(order_id)
        
        if not order:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"Order {order_id} not found",
                evidence=[f"order_id={order_id}"],
                message=None,
                next_agent=None
            )
        
        # Check if cancellable
        if order["status"] in [OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value]:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"Order {order_id} cannot be cancelled (status: {order['status']})",
                evidence=[f"order_id={order_id}", f"status={order['status']}"],
                message=None,
                next_agent=None
            )
        
        # Cancel order
        order["status"] = OrderStatus.CANCELLED.value
        order["cancelled_at"] = datetime.now().isoformat()
        order["cancel_reason"] = reason
        
        context = f"Order {order_id} cancelled. Reason: {reason}."
        reason = await self._generate_reasoning(context, "APPROVED")
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=reason,
            evidence=[
                f"order_id={order_id}",
                f"status=CANCELLED",
                f"reason={reason}"
            ],
            message=None,
            next_agent=None
        )

    @agent_trace("FulfillmentAgent", "gpt-5-mini")
    async def generate_receipt(self, order_id: str) -> AgentOutput:
        """
        Generate receipt for an order.
        """
        order = self._orders.get(order_id)
        
        if not order:
            return AgentOutput(
                agent=self.agent_name,
                decision=Decision.REJECTED,
                reason=f"Order {order_id} not found",
                evidence=[f"order_id={order_id}"],
                message=None,
                next_agent=None
            )
        
        receipt_id = f"RCP-{uuid.uuid4().hex[:8].upper()}"
        
        context = f"Receipt {receipt_id} generated for order {order_id}. Amount: ${order['total_amount']:.2f}."
        reason = await self._generate_reasoning(context, "APPROVED")
        
        return AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=reason,
            evidence=[
                f"order_id={order_id}",
                f"receipt_id={receipt_id}",
                f"total_amount=${order['total_amount']:.2f}",
                f"items_count={len(order['items'])}"
            ],
            message=None,
            next_agent=None
        )

    @agent_trace("FulfillmentAgent", "gpt-5-mini")
    async def confirm_order(
        self,
        preview_data: OrderPreviewData,
        patient_name: str,
        user_id: Optional[str] = None
    ) -> tuple[AgentOutput, OrderConfirmationData, str]:
        """
        Confirm an order from preview data.
        Builds detailed order summary, decreases inventory, creates confirmation.
        
        Returns:
            Tuple of (AgentOutput, OrderConfirmationData, summary_message)
        """
        if not preview_data or not preview_data.items:
            return (
                AgentOutput(
                    agent=self.agent_name,
                    decision=Decision.REJECTED,
                    reason="Cannot confirm order without items",
                    evidence=["items_count=0"],
                    message="Sorry, there's no order to confirm.",
                    next_agent=None
                ),
                None,
                ""
            )
        
        item = preview_data.items[0]
        
        # Generate order ID
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate totals
        subtotal = item.unit_price * item.quantity
        tax = subtotal * 0.05
        delivery_fee = 2.00
        total = subtotal + tax + delivery_fee
        
        # Decrease stock in inventory
        if self._data_service:
            self._data_service.decrease_stock(item.medicine_name, item.quantity)
        
        # Build order confirmation data
        order_confirmation = OrderConfirmationData(
            order_id=order_id,
            patient_id=preview_data.patient_id,
            patient_name=patient_name,
            items=preview_data.items,
            subtotal=subtotal,
            tax=tax,
            delivery_fee=delivery_fee,
            total_amount=total,
            status="CONFIRMED",
            created_at=datetime.now().isoformat(),
            estimated_delivery="Tomorrow by 9:00 PM"
        )
        
        # Build detailed summary message
        summary = f"""📋 **Order Summary**
━━━━━━━━━━━━━━━━━━━━━━
**Order ID:** {order_id}
**Patient:** {patient_name}
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

**Items:**
• {item.medicine_name} {item.strength} x{item.quantity} @ ${item.unit_price:.2f} = ${subtotal:.2f}

**Subtotal:** ${subtotal:.2f}
**Tax (5%):** ${tax:.2f}
**Delivery:** ${delivery_fee:.2f}
━━━━━━━━━━━━━━━━━━━━━━
**Total:** ${total:.2f}

**Status:** CONFIRMED
**Estimated Delivery:** Tomorrow by 9:00 PM"""
        
        # Store order
        self._orders[order_id] = {
            "order_id": order_id,
            "patient_id": preview_data.patient_id,
            "patient_name": patient_name,
            "items": [item.model_dump() for item in preview_data.items],
            "subtotal": subtotal,
            "tax": tax,
            "delivery_fee": delivery_fee,
            "total_amount": total,
            "status": "CONFIRMED",
            "created_at": datetime.now().isoformat(),
            "delivery_estimate": "Tomorrow by 9:00 PM"
        }
        
        context = f"Order {order_id} confirmed. Total: ${total:.2f}. Delivery: Tomorrow."
        reason = await self._generate_reasoning(context, "APPROVED")
        
        agent_output = AgentOutput(
            agent=self.agent_name,
            decision=Decision.APPROVED,
            reason=reason,
            evidence=[
                f"order_id={order_id}",
                f"patient_id={preview_data.patient_id}",
                f"patient_name={patient_name}",
                f"medicine={item.medicine_name}",
                f"quantity={item.quantity}",
                f"total=${total:.2f}",
                f"status=CONFIRMED"
            ],
            message=summary,
            next_agent=None
        )
        
        # Save to Firestore if user_id provided
        if user_id:
            try:
                from services.firestore_service import save_order
                save_order(user_id, {
                    "order_id": order_id,
                    "items": [item.model_dump() for item in preview_data.items],
                    "total_amount": total,
                    "status": "CONFIRMED",
                    "requires_prescription": preview_data.requires_prescription
                })
            except Exception as e:
                print(f"Failed to persist order: {e}")
        
        return agent_output, order_confirmation, summary

    async def _generate_message(self, context: str, task: str) -> str:
        """
        Generate a professional message using gpt-5-mini.
        Used for creating natural language responses for order operations.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful pharmacy fulfillment assistant. Generate concise, professional order confirmation messages. Keep responses under 50 words."
                    },
                    {
                        "role": "user",
                        "content": f"Context: {context}\nTask: {task}\nGenerate a brief response:"
                    }
                ],
                temperature=self.temperature,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            # Fallback to simple message on error
            return f"Order processed. {task}"

    def get_trace_id(self) -> Optional[str]:
        return get_trace_id()

