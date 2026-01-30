"""
Cart Service
============
Handles persistent shopping cart operations in Firestore.
Path: /users/{user_id}/cart/active
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import firebase_admin
from firebase_admin import firestore

def get_db():
    try:
        return firestore.client()
    except ValueError:
        return None

class CartService:
    def __init__(self):
        pass

    def get_cart(self, user_id: str) -> Dict[str, Any]:
        """
        Get active cart for user.
        Returns dict with 'items' (list) and 'updatedAt'.
        """
        db = get_db()
        if not db or not user_id:
            return {"items": []}

        try:
            doc_ref = db.collection("users").document(user_id).collection("cart").document("active")
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return {"items": []}
        except Exception as e:
            print(f"❌ Error fetching cart: {e}")
            return {"items": []}

    def add_item(self, user_id: str, item: Dict[str, Any]) -> bool:
        """
        Add item to cart. Merges quantity if item exists.
        Item must have: medicine_id (or medicineName to generate one), quantity.
        """
        db = get_db()
        if not db or not user_id:
            return False

        try:
            doc_ref = db.collection("users").document(user_id).collection("cart").document("active")
            
            # Run in transaction to ensure atomic read-modify-write
            transaction = db.transaction()
            
            @firestore.transactional
            def update_in_transaction(transaction, doc_ref):
                snapshot = doc_ref.get(transaction=transaction)
                current_data = snapshot.to_dict() if snapshot.exists else {"items": []}
                items = current_data.get("items", [])
                
                # Check if item exists
                found = False
                target_med_id = item.get("medicine_id")
                target_med_name = item.get("medicine_name")
                
                new_items = []
                for existing in items:
                    # Match by ID or Name (fallback)
                    match = False
                    if target_med_id and existing.get("medicine_id") == target_med_id:
                        match = True
                    elif target_med_name and existing.get("medicine_name") == target_med_name:
                        match = True
                        
                    if match:
                        # Update quantity
                        existing["quantity"] = int(existing.get("quantity", 0)) + int(item.get("quantity", 1))
                        found = True
                    new_items.append(existing)
                
                if not found:
                    # Ensure minimal fields
                    new_item = {
                        "medicine_id": item.get("medicine_id") or f"MED-{uuid_hash(item.get('medicine_name', 'UNK'))}",
                        "medicine_name": item.get("medicine_name"),
                        "quantity": int(item.get("quantity", 1)),
                        "strength": item.get("strength", ""),
                        "form": item.get("form", "Tablet"),
                        "unit_price": float(item.get("unit_price", 5.00)),
                        "addedAt": datetime.now().isoformat()
                    }
                    new_items.append(new_item)
                
                transaction.set(doc_ref, {
                    "items": new_items,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                }, merge=True)
                
            update_in_transaction(transaction, doc_ref)
            print(f"✅ Added item to cart for {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding to cart: {e}")
            return False

    def remove_item(self, user_id: str, medicine_id: str) -> bool:
        """Remove item from cart by medicine_id"""
        db = get_db()
        if not db or not user_id:
            return False
            
        try:
            doc_ref = db.collection("users").document(user_id).collection("cart").document("active")
            
            doc = doc_ref.get()
            if not doc.exists:
                return False
                
            items = doc.to_dict().get("items", [])
            new_items = [i for i in items if i.get("medicine_id") != medicine_id]
            
            doc_ref.update({
                "items": new_items,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            print(f"❌ Error removing item: {e}")
            return False

    def clear_cart(self, user_id: str) -> bool:
        """Clear active cart"""
        db = get_db()
        if not db or not user_id:
            return False
            
        try:
            doc_ref = db.collection("users").document(user_id).collection("cart").document("active")
            doc_ref.delete()
            return True
        except Exception as e:
            print(f"❌ Error clearing cart: {e}")
            return False

def uuid_hash(s):
    import hashlib
    return hashlib.md5(s.encode()).hexdigest()[:8].upper()

cart_service = CartService()
