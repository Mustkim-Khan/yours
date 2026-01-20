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
        
        # Prepare storage data - strict schema
        storage_data = {
            "userId": user_id,  # Critical for security/filtering
            "orderId": order_id,
            "medicine": order_data.get("items", [{}])[0].get("medicine_name", "Unknown"),
            "dosage": order_data.get("items", [{}])[0].get("strength", "Unknown"),
            "quantity": int(order_data.get("items", [{}])[0].get("quantity", 1)),
            "supplyDays": int(order_data.get("items", [{}])[0].get("quantity", 30)), # Simplified
            "orderedAt": firestore.SERVER_TIMESTAMP, # Server time for truth
            "prescriptionRequired": order_data.get("requires_prescription", False),
            "status": "CONFIRMED",
            "metadata": order_data # Store full blob just in case, but rely on top-level fields for query
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
