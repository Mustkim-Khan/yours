"""
Data Services - CSV Data Access Layer
Provides access to medicine_master.csv and order_history.csv
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from models.schemas import Medicine, Patient


class DataService:
    """
    Data service for accessing pharmacy data from CSV files.
    """
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.data_dir = data_dir
        self._medicines_df = None
        self._orders_df = None
        self._load_data()
    
    def _load_data(self):
        """Load CSV data files"""
        try:
            medicine_path = os.path.join(self.data_dir, "medicine_master.csv")
            orders_path = os.path.join(self.data_dir, "order_history.csv")
            
            if os.path.exists(medicine_path):
                self._medicines_df = pd.read_csv(medicine_path)
            else:
                self._medicines_df = pd.DataFrame()
            
            if os.path.exists(orders_path):
                self._orders_df = pd.read_csv(orders_path)
            else:
                self._orders_df = pd.DataFrame()
                
        except Exception as e:
            print(f"Error loading data: {e}")
            self._medicines_df = pd.DataFrame()
            self._orders_df = pd.DataFrame()
    
    def search_medicine(self, query: str) -> List[Medicine]:
        """Search medicines by name"""
        if self._medicines_df.empty:
            return []
        
        query_lower = query.lower()
        # Support both 'name' and 'medicine_name' columns
        name_col = 'name' if 'name' in self._medicines_df.columns else 'medicine_name'
        matches = self._medicines_df[
            self._medicines_df[name_col].str.lower().str.contains(query_lower, na=False)
        ]
        
        medicines = []
        for _, row in matches.iterrows():
            try:
                med = Medicine(
                    medicine_id=str(row.get('medicine_id', '')),
                    medicine_name=str(row.get('name', row.get('medicine_name', ''))),
                    strength=str(row.get('strength', '')),
                    form=str(row.get('form', 'Tablet')),
                    stock_level=int(row.get('stock_level', 0)),
                    prescription_required=self._parse_bool(row.get('prescription_required', False)),
                    category=str(row.get('category', 'General')),
                    discontinued=self._parse_bool(row.get('discontinued', False)),
                    max_quantity_per_order=int(row.get('max_quantity_per_order', 30)),
                    controlled_substance=self._parse_bool(row.get('controlled_substance', False))
                )
                medicines.append(med)
            except Exception:
                pass
        
        return medicines
    
    def _parse_bool(self, value) -> bool:
        """Parse boolean from string or bool"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1')
        return bool(value)
    
    def get_medicine_by_id(self, medicine_id: str) -> Optional[Medicine]:
        """Get medicine by ID"""
        if self._medicines_df.empty:
            return None
        
        matches = self._medicines_df[self._medicines_df['medicine_id'] == medicine_id]
        if matches.empty:
            return None
        
        row = matches.iloc[0]
        return Medicine(
            medicine_id=str(row.get('medicine_id', '')),
            medicine_name=str(row.get('name', row.get('medicine_name', ''))),
            strength=str(row.get('strength', '')),
            form=str(row.get('form', 'Tablet')),
            stock_level=int(row.get('stock_level', 0)),
            prescription_required=self._parse_bool(row.get('prescription_required', False)),
            category=str(row.get('category', 'General')),
            discontinued=self._parse_bool(row.get('discontinued', False)),
            max_quantity_per_order=int(row.get('max_quantity_per_order', 30)),
            controlled_substance=self._parse_bool(row.get('controlled_substance', False))
        )
    
    def get_patient_order_history(self, patient_id: str) -> pd.DataFrame:
        """Get order history for a patient"""
        if self._orders_df.empty:
            return pd.DataFrame()
        
        return self._orders_df[self._orders_df['patient_id'] == patient_id]
    
    def get_medicines_needing_refill(
        self, 
        patient_id: str, 
        current_date: datetime,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Get medicines that need refill soon"""
        history = self.get_patient_order_history(patient_id)
        
        if history.empty:
            return []
        
        refills = []
        
        # Group by medicine
        for medicine in history['medicine_name'].unique():
            med_history = history[history['medicine_name'] == medicine]
            last_order = med_history.iloc[-1]
            
            try:
                order_date = datetime.fromisoformat(str(last_order['order_date']))
            except:
                continue
            
            quantity = int(last_order.get('quantity', 30))
            days_supply = quantity  # Assume 1 per day
            
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
        if self._medicines_df.empty:
            return {
                "total_skus": 0, 
                "unique_medicines": 0, 
                "out_of_stock": 0, 
                "low_stock": 0,
                "prescription_required": 0,
                "discontinued": 0
            }
        
        total = len(self._medicines_df)
        out_of_stock = len(self._medicines_df[self._medicines_df['stock_level'] == 0])
        low_stock = len(self._medicines_df[
            (self._medicines_df['stock_level'] > 0) & 
            (self._medicines_df['stock_level'] <= 20)
        ])
        
        # Count prescription required
        prescription_required = 0
        if 'prescription_required' in self._medicines_df.columns:
            prescription_required = len(self._medicines_df[
                self._medicines_df['prescription_required'].apply(lambda x: str(x).lower() in ('true', 'yes', '1'))
            ])
        
        return {
            "total_skus": total,
            "unique_medicines": total,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "prescription_required": prescription_required,
            "discontinued": 0
        }
    
    def get_all_medicines(self) -> List[Medicine]:
        """Get all medicines in inventory"""
        if self._medicines_df.empty:
            return []
        
        medicines = []
        name_col = 'name' if 'name' in self._medicines_df.columns else 'medicine_name'
        
        for _, row in self._medicines_df.iterrows():
            try:
                med = Medicine(
                    medicine_id=str(row.get('medicine_id', '')),
                    medicine_name=str(row.get('name', row.get('medicine_name', ''))),
                    strength=str(row.get('strength', '')),
                    form=str(row.get('form', 'Tablet')),
                    stock_level=int(row.get('stock_level', 0)),
                    prescription_required=self._parse_bool(row.get('prescription_required', False)),
                    category=str(row.get('category', 'General')),
                    discontinued=self._parse_bool(row.get('discontinued', False)),
                    max_quantity_per_order=int(row.get('max_quantity_per_order', 30)),
                    controlled_substance=self._parse_bool(row.get('controlled_substance', False))
                )
                medicines.append(med)
            except Exception:
                pass
        
        return medicines
    
    def decrease_stock(self, medicine_name: str, quantity: int) -> bool:
        """
        Decrease stock level for a medicine when an order is placed.
        Returns True if successful, False if insufficient stock.
        """
        if self._medicines_df.empty:
            return False
        
        # Find the medicine by name (case-insensitive)
        name_col = 'name' if 'name' in self._medicines_df.columns else 'medicine_name'
        mask = self._medicines_df[name_col].str.lower() == medicine_name.lower()
        
        if not mask.any():
            # Try partial match
            mask = self._medicines_df[name_col].str.lower().str.contains(medicine_name.lower(), na=False)
        
        if not mask.any():
            print(f"Medicine not found: {medicine_name}")
            return False
        
        # Get current stock
        idx = self._medicines_df[mask].index[0]
        current_stock = self._medicines_df.loc[idx, 'stock_level']
        
        if current_stock < quantity:
            print(f"Insufficient stock for {medicine_name}: {current_stock} < {quantity}")
            return False
        
        # Decrease stock
        new_stock = current_stock - quantity
        self._medicines_df.loc[idx, 'stock_level'] = new_stock
        
        # Save to CSV
        try:
            medicine_path = os.path.join(self.data_dir, "medicine_master.csv")
            self._medicines_df.to_csv(medicine_path, index=False)
            print(f"Stock updated: {medicine_name} {current_stock} -> {new_stock}")
            return True
        except Exception as e:
            print(f"Error saving stock update: {e}")
            return False
    
    def get_all_patients(self) -> List[Patient]:
        """Get all unique patients from order history"""
        if self._orders_df.empty:
            return []
        
        patients = []
        seen = set()
        
        for _, row in self._orders_df.iterrows():
            pid = str(row.get('patient_id', ''))
            if pid and pid not in seen:
                seen.add(pid)
                patients.append(Patient(
                    patient_id=pid,
                    patient_name=str(row.get('patient_name', f'Patient {pid}')),
                    patient_email=str(row.get('patient_email', f'{pid}@example.com')),
                    patient_phone=str(row.get('patient_phone', '000-000-0000'))
                ))
        
        return patients


# Global instance
data_service = DataService()