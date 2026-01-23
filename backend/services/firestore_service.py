"""
Firestore Service
=================
Handles server-side Firestore operations for order persistence.
Strictly scopes all data access to user_id for security.
"""

from datetime import datetime
import firebase_admin
from firebase_admin import firestore
from typing import List, Optional, Dict, Any

# Initialize client (assumes firebase_admin.initialize_app() called in main.py)
def get_db():
    try:
        return firestore.client()
    except ValueError:
        # If app not initialized, return None (should be handled by caller)
        return None

def save_order(user_id: str, order_data: Dict[str, Any]) -> bool:
    """
    Save a confirmed order to Firestore.
    Path: /orders/{order_id}
    
    Args:
        user_id: Firebase UID (SECURITY CRITICAL)
        order_data: Dictionary containing order details
    """
    db = get_db()
    if not db or not user_id:
        print(f"❌ Firestore save failed: DB={bool(db)}, UserID={bool(user_id)}")
        return False
        
    try:
        # Create a document reference
        order_id = order_data.get("order_id")
        if not order_id:
            return False
            
        doc_ref = db.collection("orders").document(order_id)
        
        # Prepare storage data - strict schema with multi-item support
        items = order_data.get("items", [])
        first_item = items[0] if items else {}
        
        storage_data = {
            "userId": user_id,  # Critical for security/filtering
            "patient_id": order_data.get("patient_id"), # Required for DataService.get_patient_order_history
            "orderId": order_id,
            # Store full items array for multi-item orders
            "items": items,
            "itemCount": len(items),
            # Backward-compatible single-item fields (for existing queries/displays)
            "medicine": first_item.get("medicine_name", "Unknown"),
            "dosage": first_item.get("strength", "Unknown"),
            "quantity": int(first_item.get("quantity", 1)),
            "supplyDays": int(first_item.get("quantity", 30)), # Simplified
            "orderedAt": firestore.SERVER_TIMESTAMP, # Server time for truth
            "prescriptionRequired": order_data.get("requires_prescription", False),
            "status": "CONFIRMED",
            "totalAmount": order_data.get("total_amount", 0.0),
            "metadata": order_data # Store full blob just in case
        }
        
        doc_ref.set(storage_data)
        print(f"✅ Order {order_id} persisted for user {user_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving order to Firestore: {e}")
        return False

def get_orders(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get order history for a specific user.
    Security: STRICTLY filtered by userId == user_id.
    """
    db = get_db()
    if not db or not user_id:
        return []
        
    try:
        orders_ref = db.collection("orders")
        query = (orders_ref
                 .where("userId", "==", user_id)
                 .order_by("orderedAt", direction=firestore.Query.DESCENDING)
                 .limit(limit))
                 
        docs = query.stream()
        
        orders = []
        for doc in docs:
            data = doc.to_dict()
            # Convert timestamp to ISO string for easier JSON serialization
            if "orderedAt" in data and hasattr(data["orderedAt"], "isoformat"):
                data["orderedAt"] = data["orderedAt"].isoformat()
            orders.append(data)
            
        return orders
        
    except Exception as e:
        print(f"❌ Error fetching orders from Firestore: {e}")
        return []

def get_conversation_history(conversation_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Load recent messages from a conversation for agent context.
    Returns messages in chronological order (oldest first).
    
    Args:
        conversation_id: Firestore conversation document ID
        limit: Maximum number of messages to retrieve
    
    Returns:
        List of message dicts with 'role' (user/assistant) and 'content' keys
    """
    db = get_db()
    if not db or not conversation_id:
        return []
    
    try:
        messages_ref = db.collection("conversations").document(conversation_id).collection("messages")
        query = (messages_ref
                 .order_by("timestamp")
                 .limit(limit))
        
        docs = query.stream()
        
        messages = []
        for doc in docs:
            data = doc.to_dict()
            # Map frontend sender format to OpenAI role format
            sender = data.get("sender", "user")
            role = "user" if sender == "user" else "assistant"
            text = data.get("text", "")
            
            if text:  # Only include non-empty messages
                messages.append({
                    "role": role,
                    "content": text
                })
        
        print(f"✅ Loaded {len(messages)} messages from conversation {conversation_id}")
        return messages
        
    except Exception as e:
        print(f"❌ Error loading conversation history: {e}")
        return []

