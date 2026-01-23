"""
WhatsApp Notification Service
=============================
Handles sending WhatsApp messages via Twilio.
Used primarily for order confirmations.
"""

import os
from twilio.rest import Client
from typing import Dict, Any, Optional

# NOTE: In sandbox mode, recipient must have joined sandbox via join code
# Recipient must send "join <sandbox-code>" to the Twilio number first.

def send_order_confirmation_whatsapp(phone: str, name: str, order: Dict[str, Any]) -> bool:
    """
    Send order confirmation via WhatsApp.
    
    Args:
        phone: Recipient phone number in E.164 format (e.g., +14155552671)
        name: Customer name
        order: Order dictionary containing 'order_id', 'items', 'total_amount'
        
    Returns:
        bool: True if successful, False otherwise.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    
    if not account_sid or not auth_token:
        print("⚠️ Twilio credentials missing. WhatsApp notification skipped.")
        return False
        
    try:
        client = Client(account_sid, auth_token)
        
        # Extract order details
        order_id = order.get("order_id", "Unknown")
        item = order.get("items", [{}])[0]
        medicine_name = item.get("medicine_name", "Medicine")
        quantity = item.get("quantity", 1)
        delivery_estimate = order.get("delivery_estimate", "Tomorrow by 9:00 PM")
        
        # Format message
        message_body = f"""✅ *Order Confirmed*

Hello {name},

Your medicine order has been successfully confirmed by Your Pharma AI.

📦 *Order ID:* {order_id}
💊 *Medicine:* {medicine_name}
📦 *Quantity:* {quantity}
🚚 *Delivery:* Home Delivery
⏰ *Expected Delivery:* {delivery_estimate}

Our system has validated your prescription, updated inventory, and initiated fulfillment.

Thank you for choosing *Your Pharma*."""

        print(f"📧 Sending WhatsApp to {phone}...")
        
        message = client.messages.create(
            from_=from_number,
            body=message_body,
            to=f"whatsapp:{phone}"
        )
        
        print(f"✅ WhatsApp sent! SID: {message.sid}")
        return True
        
    except Exception as e:
        print(f"❌ WhatsApp failed: {e}")
        return False
