"""
Data Services - Firestore Data Access Layer
Provides access to Firestore 'medicines' and 'orders' collections.
Replaces legacy CSV implementation.
"""

import os
import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from models.schemas import Medicine, Patient
from utils.auth import init_firebase


class DataService:
    """
    Data service for accessing pharmacy data from Firestore.
    """
    
    def __init__(self):
        # Ensure Firebase is initialized
        if not firebase_admin._apps:
            init_firebase()
        
        try:
            self.db = firestore.client()
            print("✅ DataService connected to Firestore")
        except Exception as e:
            print(f"❌ DataService failed to connect to Firestore: {e}")
            self.db = None
    
    def search_medicine(self, query: str) -> List[Medicine]:
        """Search medicines by name in Firestore"""
        if not self.db:
            return []
        
        medicines = []
        try:
            # Firestore doesn't have native full-text search, so we do client-side filtering 
            # for this MVP or simple prefix matching if possible.
            # For scale, would use Algolia/Elasticsearch.
            # Fetching all for now since dataset is small < 100 items.
            docs = self.db.collection('medicines').stream()
            
            query_lower = query.lower()
            
            for doc in docs:
                data = doc.to_dict()
                name = data.get('medicine_name', '').lower()
                med_id = data.get('medicine_id', '').lower()
                
                if query_lower in name or query_lower in med_id:
                    medicines.append(self._map_firestore_to_medicine(data))
                    
        except Exception as e:
            print(f"Error searching medicines: {e}")
            
        return medicines
    
    def get_medicine_by_id(self, medicine_id: str) -> Optional[Medicine]:
        """Get medicine by ID"""
        if not self.db:
            return None
        
        try:
            doc_ref = self.db.collection('medicines').document(medicine_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return self._map_firestore_to_medicine(doc.to_dict())
            return None
            
        except Exception as e:
            print(f"Error getting medicine {medicine_id}: {e}")
            return None

    def _map_firestore_to_medicine(self, data: Dict[str, Any]) -> Medicine:
        """Helper to map Firestore dict to Pydantic model"""
        return Medicine(
            medicine_id=str(data.get('medicine_id', '')),
            medicine_name=str(data.get('medicine_name', '')),
            strength=str(data.get('strength', '')),
            form=str(data.get('form', 'Tablet')),
            stock_level=int(data.get('stock_level', 0)),
            prescription_required=bool(data.get('prescription_required', False)),
            category=str(data.get('category', 'General')),
            discontinued=bool(data.get('discontinued', False)),
            max_quantity_per_order=int(data.get('max_quantity_per_order', 30)),
            controlled_substance=bool(data.get('controlled_substance', False))
        )
    
    def get_patient_order_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get order history for a patient from Firestore"""
        if not self.db:
            return []
        
        try:
            # Query 'orders' collection where patient_id matches
            # Note: We support 'userId' (auth uid) and 'patient_id' (legacy/business id)
            # This searches by the explicit patient_id field first
            orders_ref = self.db.collection('orders')
            query = orders_ref.where(filter=FieldFilter("patient_id", "==", patient_id))
            
            docs = query.stream()
            orders = []
            
            for doc in docs:
                data = doc.to_dict()
                # Convert timestamps
                if 'orderedAt' in data and hasattr(data['orderedAt'], 'isoformat'):
                    data['orderedAt'] = data['orderedAt'].isoformat()
                orders.append(data)
            
            # Since we promised to return DataFrame-like list of dicts for now (or just list of dicts)
            # The original return type hint said pd.DataFrame but code returned it for some callers.
            # Converting to standard list of dicts is safer for API.
            # Let's check usages. It was returning pd.DataFrame in legacy.
            # We should probably return a DataFrame if we want minimal breakage, 
            # OR update call sites. 
            # Updating logic to return list, converting to DF at edge if needed by existing code.
            # Looking at main.py:502: history = data_service.get_patient_order_history(patient_id)
            # Then main.py:504: if history.empty: ...
            # So main.py EXPECTS a DataFrame.
            
            import pandas as pd
            if not orders:
                return pd.DataFrame()
            return pd.DataFrame(orders)
            
        except Exception as e:
            print(f"Error fetching history: {e}")
            import pandas as pd
            return pd.DataFrame()

    def has_valid_prescription(self, user_id: str, medicine_name: str, dosage: str) -> bool:
        """
        Check if user has a valid valid prescription for this specific medicine/dosage 
        from a previous confirmed order.
        
        Criteria:
        - Same User ID
        - Medicine Name matches (case-insensitive)
        - Dosage matches exactly
        - Order was successfully confirmed (implies prescription was verified)
        - Prescription was required for that order
        """
        if not self.db or not user_id:
            return False
            
        try:
            from services.firestore_service import get_orders
            # reuse existing strict user-scoped query
            orders = get_orders(user_id, limit=20) 
            
            target_med = medicine_name.lower().strip()
            target_dosage = dosage.strip()
            
            for order in orders:
                # 1. Check Status (Must be a completed/confirmed order)
                status = order.get("status", "").upper()
                if status not in ["CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED"]:
                    continue
                    
                # 2. Check Medicine Name
                order_med = order.get("medicine", "").lower().strip()
                if not order_med or target_med not in order_med: 
                    # use containment for safety (e.g. "Paracetamol" vs "Paracetamol 500mg")
                    # But strict match is better if data is clean. Let's try containment for now to be robust.
                    if order_med != target_med:
                         continue

                # 3. Check Dosage (Strict Match)
                order_dosage = str(order.get("dosage", "")).strip()
                if order_dosage != target_dosage:
                    continue
                    
                # 4. Check if it WAS a prescription order
                # If it didn't require prescription, it doesn't prove we have one.
                if not order.get("prescriptionRequired", False):
                    continue
                    
                # If satisfied, we found a valid historical prescription
                print(f"✅ Found valid prescription from Order {order.get('orderId')}")
                return True
                
            return False
            
        except Exception as e:
            print(f"❌ Error checking prescription history: {e}")
            return False
    
    def get_medicines_needing_refill(
        self, 
        patient_id: str, 
        current_date: datetime,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Get medicines that need refill soon based on history"""
        # Reuse history fetch (returns DataFrame)
        history_df = self.get_patient_order_history(patient_id)
        
        if history_df.empty:
            return []
        
        refills = []
        
        # Logic remains similar but operating on the DF we just built from Firestore data
        if 'medicine' in history_df.columns:
             med_col = 'medicine'
        elif 'medicine_name' in history_df.columns:
            med_col = 'medicine_name'
        else:
            return []

        for medicine in history_df[med_col].unique():
            med_history = history_df[history_df[med_col] == medicine]
            last_order = med_history.iloc[-1]
            
            try:
                # Firestore timestamp string or object handling
                order_date_val = last_order.get('orderedAt', last_order.get('order_date'))
                if isinstance(order_date_val, str):
                    order_date = datetime.fromisoformat(order_date_val.replace('Z', '+00:00'))
                elif isinstance(order_date_val, datetime):
                    order_date = order_date_val
                else:
                    continue
            except:
                continue
            
            quantity = int(last_order.get('quantity', 30))
            days_supply = quantity  # Assume 1 per day
            
            if order_date.tzinfo:
                order_date = order_date.replace(tzinfo=None) # Naive comparison for simplicity
                
            refill_date = order_date + timedelta(days=days_supply)
            days_remaining = (refill_date - current_date).days
            
            if days_remaining <= days_ahead:
                refills.append({
                    "medicine_name": medicine,
                    "last_order_date": order_date.isoformat(),
                    "quantity": quantity,
                    "refill_date": refill_date.isoformat(),
                    "days_remaining": max(0, days_remaining)
                })
        
        return sorted(refills, key=lambda x: x["days_remaining"])
    
    def get_inventory_stats(self) -> Dict[str, Any]:
        """Get inventory statistics"""
        if not self.db:
            return {}
            
        try:
            # For large datasets, use aggregation queries. 
            # For <1000 items, client side counting is fine.
            docs = self.db.collection('medicines').stream()
            
            total = 0
            out_of_stock = 0
            low_stock = 0
            prescription_required = 0
            
            for doc in docs:
                data = doc.to_dict()
                total += 1
                stock = int(data.get('stock_level', 0))
                
                if stock == 0:
                    out_of_stock += 1
                elif stock <= 20:
                    low_stock += 1
                    
                if data.get('prescription_required'):
                    prescription_required += 1
                    
            return {
                "total_skus": total,
                "unique_medicines": total,
                "out_of_stock": out_of_stock,
                "low_stock": low_stock,
                "prescription_required": prescription_required,
                "discontinued": 0 # Not tracking yet
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def get_all_medicines(self) -> List[Medicine]:
        """Get all medicines in inventory"""
        if not self.db:
            return []
            
        medicines = []
        try:
            docs = self.db.collection('medicines').stream()
            for doc in docs:
                medicines.append(self._map_firestore_to_medicine(doc.to_dict()))
        except Exception as e:
            print(f"Error getting all medicines: {e}")
            
        return medicines
    
    def decrease_stock(self, medicine_name: str, quantity: int) -> bool:
        """
        Decrease stock level for a medicine.
        Uses Firestore Transaction for atomicity.
        """
        if not self.db:
            return False
            
        transaction = self.db.transaction()
        
        try:
            # 1. Find the document ID by name
            # Ideally we should pass ID, but legacy code passes name.
            # We search for it.
            medicines_ref = self.db.collection('medicines')
            query = medicines_ref.where(filter=FieldFilter("medicine_name", "==", medicine_name)).limit(1)
            docs = list(query.stream())
            
            if not docs:
                # Try case insensitive match if precise match failed? 
                # Firestore doesn't support case-insensitive query easily. 
                # Fail for now to enforce exact names, or fetch all (expensive).
                print(f"Medicine not found for stock update: {medicine_name}")
                return False
                
            doc_ref = docs[0].reference
            
            @firestore.transactional
            def update_in_transaction(transaction, doc_ref):
                snapshot = doc_ref.get(transaction=transaction)
                current_stock = snapshot.get('stock_level')
                
                if current_stock < quantity:
                    raise ValueError(f"Insufficient stock: {current_stock} < {quantity}")
                
                transaction.update(doc_ref, {
                    'stock_level': current_stock - quantity,
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
                return True

            update_in_transaction(transaction, doc_ref)
            print(f"✅ Stock updated for {medicine_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update stock: {e}")
            return False
    
    def get_all_patients(self) -> List[Patient]:
        """Get all unique patients from orders"""
        if not self.db:
            return []
            
        try:
            # Aggregation manually
            docs = self.db.collection('orders').stream()
            patients_map = {}
            
            for doc in docs:
                data = doc.to_dict()
                pid = str(data.get('patient_id', ''))
                if pid and pid not in patients_map:
                    patients_map[pid] = Patient(
                        patient_id=pid,
                        patient_name=str(data.get('patient_name', f'Patient {pid}')),
                        patient_email=str(data.get('patient_email', '')),
                        patient_phone=str(data.get('patient_phone', ''))
                    )
            return list(patients_map.values())
            
        except Exception as e:
            print(f"Error getting patients: {e}")
            return []

    def get_user_contact(self, user_id: str) -> Dict[str, Optional[str]]:
        """
        Get user contact details (phone, name) from Firestore users collection.
        Used for notifications.
        """
        if not self.db or not user_id:
            return {"name": None, "phone": None}
            
        try:
            doc_ref = self.db.collection('users').document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return {
                    "name": data.get("name"),
                    "phone": data.get("phone")
                }
            return {"name": None, "phone": None}
            
        except Exception as e:
            print(f"Error getting user contact for {user_id}: {e}")
            return {"name": None, "phone": None}


# Global instance
data_service = DataService()
