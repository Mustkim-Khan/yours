import os
import sys
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Add backend to path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.auth import init_firebase

def migrate_medicines(db, csv_path):
    print(f"\n💊 Migrating Medicines from {csv_path}...")
    if not os.path.exists(csv_path):
        print("❌ File not found.")
        return

    df = pd.read_csv(csv_path)
    collection = db.collection('medicines')
    
    count = 0
    for _, row in df.iterrows():
        try:
            # Map CSV columns to Firestore schema
            # Using 'name' from CSV as 'medicine_name' in Firestore to match schema
            medicine_id = str(row['medicine_id'])
            
            # Handle boolean fields
            prescription_required = str(row.get('prescription_required', 'False')).lower() in ('true', 'yes', '1')
            
            data = {
                'medicine_id': medicine_id,
                'medicine_name': str(row['name']),
                'strength': str(row.get('strength', '')),
                'form': str(row.get('form', 'Tablet')),
                'category': str(row.get('category', 'General')),
                'stock_level': int(row.get('stock_level', 0)),
                'price': float(row.get('price', 0.0)),
                'prescription_required': prescription_required,
                'last_updated': firestore.SERVER_TIMESTAMP,
                # Default fields not in CSV
                'discontinued': False,
                'controlled_substance': False, # Safe default, manual update needed for controlled substances
                'max_quantity_per_order': 30
            }
            
            # Use medicine_id as document ID
            collection.document(medicine_id).set(data)
            print(f"   ✓ Imported {row['name']}")
            count += 1
        except Exception as e:
            print(f"   ❌ Failed to import row: {e}")
            
    print(f"✅ Migrated {count} medicines.")

def migrate_orders(db, csv_path):
    print(f"\n📦 Migrating Orders from {csv_path}...")
    if not os.path.exists(csv_path):
        print("❌ File not found.")
        return

    df = pd.read_csv(csv_path)
    collection = db.collection('orders')
    
    count = 0
    for _, row in df.iterrows():
        try:
            order_id = str(row['order_id'])
            patient_id = str(row['patient_id'])
            
            # Convert date string to timestamp
            order_date_str = str(row['order_date'])
            try:
                order_date = datetime.strptime(order_date_str, '%Y-%m-%d')
            except:
                order_date = datetime.now()

            data = {
                'orderId': order_id,
                'userId': patient_id, # Using patient_id as userId for migration
                'patient_id': patient_id,
                'patient_name': str(row.get('patient_name', '')),
                'medicine': str(row.get('medicine_name', '')),
                'quantity': int(row.get('quantity', 1)),
                'status': str(row.get('status', 'CONFIRMED')),
                'orderedAt': order_date,
                'legacy_import': True
            }
            
            collection.document(order_id).set(data)
            print(f"   ✓ Imported Order {order_id}")
            count += 1
        except Exception as e:
            print(f"   ❌ Failed to import order: {e}")
            
    print(f"✅ Migrated {count} orders.")

if __name__ == "__main__":
    print("🚀 Starting CSV to Firestore Migration...")
    
    # Initialize Firebase
    if init_firebase():
        db = firestore.client()
        
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        
        # 1. Migrate Medicines
        medicine_csv = os.path.join(data_dir, 'medicine_master.csv')
        migrate_medicines(db, medicine_csv)
        
        # 2. Migrate Orders
        orders_csv = os.path.join(data_dir, 'order_history.csv')
        migrate_orders(db, orders_csv)
        
        print("\n✨ Migration Complete!")
    else:
        print("❌ Could not initialize Firebase. Check service-account.json or env vars.")
