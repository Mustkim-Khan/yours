import sys
import os
import asyncio

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.data_services import data_service
from services.firestore_service import save_order
from datetime import datetime

async def verify_migration():
    print("\n🔍 Verifying Firestore Integration...\n")
    
    # 1. Test Search Medicine
    print("1. Testing Search Medicine (Read)...")
    medicines = data_service.search_medicine("Amoxicillin")
    if medicines:
        med = medicines[0]
        print(f"   ✅ Found: {med.medicine_name} (Stock: {med.stock_level})")
    else:
        print("   ❌ Medicine not found (Migration might have failed)")
        return

    # 2. Test Decrease Stock (Write)
    print("\n2. Testing Decrease Stock (Write Transaction)...")
    initial_stock = med.stock_level
    success = data_service.decrease_stock("Amoxicillin", 1)
    
    if success:
        # Verify new stock
        updated_meds = data_service.search_medicine("Amoxicillin")
        new_stock = updated_meds[0].stock_level
        print(f"   ✅ Stock decreased: {initial_stock} -> {new_stock}")
    else:
        print("   ❌ Failed to decrease stock")

    # 3. Test Order History (Read Orders)
    print("\n3. Testing Order History (Read)...")
    # We need a patient ID that exists. Let's use one from the known CSV data: P001
    history = data_service.get_patient_order_history("P001")
    
    if not history.empty:
        print(f"   ✅ Found {len(history)} orders for P001")
        print(f"   Last order: {history.iloc[0].get('medicine', history.iloc[0].get('medicine_name'))}")
    else:
        print("   ⚠️ No history found for P001 (Did migration run?)")

    # 4. Test New Order Persistence (Write Order)
    print("\n4. Testing New Order Persistence (Write)...")
    test_order_id = f"TEST-{int(datetime.now().timestamp())}"
    test_user_id = "test_user_123"
    test_patient_id = "P001"
    
    order_data = {
        "items": [{
            "medicine_name": "Amoxicillin",
            "strength": "500mg",
            "quantity": 1
        }],
        "requires_prescription": False,
        "patient_id": test_patient_id # This validates our fix
    }
    
    save_result = save_order(test_user_id, {
        "order_id": test_order_id,
        "patient_id": test_patient_id,
        **order_data
    })
    
    if save_result:
        print(f"   ✅ Order {test_order_id} saved via firestore_service")
        # Verify it appears in history
        new_history = data_service.get_patient_order_history(test_patient_id)
        # Check if our new order is there
        # Note: History fetch order might depend on implementation details, check by ID if possible
        found = False
        if not new_history.empty:
            for _, row in new_history.iterrows():
                if row.get('orderId') == test_order_id:
                    found = True
                    break
        
        if found:
            print("   ✅ New order successfully retrieved via DataService!")
        else:
            print("   ❌ New order saved but NOT returned by DataService (Check patient_id field?)")
    else:
        print("   ❌ Failed to save order")

if __name__ == "__main__":
    asyncio.run(verify_migration())
