
import asyncio
import os
import sys
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.refill_prediction_agent import RefillPredictionAgent
from services.data_services import data_service

async def test_refill_logic():
    print("🧪 Starting Refill Logic Test...")
    
    # 1. Initialize
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase_credentials.json")
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    refill_agent = RefillPredictionAgent()
    refill_agent.set_data_service(data_service)
    
    # 2. Creating Mock User & Order
    test_uid = "TEST_USER_REFILL"
    test_med = "TestCillin"
    
    # Cleanup previous
    db.collection("orders").document(f"ORD-{test_uid}-1").delete()
    db.collection("users").document(test_uid).delete()
    
    # Create User
    db.collection("users").document(test_uid).set({
        "name": "Test User",
        "email": "test@example.com",
        "phone": "+15550000000",
        "refill_alerts": []
    })
    
    # Create Order (28 days ago, 30 day supply -> 2 days left -> AUTO_REFILL)
    ordered_at = datetime.now() - timedelta(days=28)
    
    order_data = {
        "orderId": f"ORD-{test_uid}-1",
        "userId": test_uid,
        "patient_id": test_uid,
        "medicine": test_med,
        "quantity": 30,
        "orderedAt": ordered_at.isoformat(),
        "status": "DELIVERED",
        "prescriptionRequired": False
    }
    db.collection("orders").document(f"ORD-{test_uid}-1").set(order_data)
    print("✅ Mock Data Created (Order 28 days ago)")
    
    # 3. Trigger Agent Logic
    print("RUNNING evaluate_patient_refills...")
    alerts = await refill_agent.evaluate_patient_refills(test_uid)
    
    # 4. Verify Results
    print(f"📊 Alerts Generated: {len(alerts)}")
    if len(alerts) == 1:
        alert = alerts[0]
        print(f"   Medicine: {alert['medicine']}")
        print(f"   Status: {alert['status']}")
        print(f"   Days Left: {alert['days_remaining']}")
        print(f"   Reason: {alert.get('ai_reason', 'N/A')}")
        
        if alert['status'] == 'AUTO_REFILL' and alert['medicine'] == test_med:
            print("   ✅ Logic CORRECT: AUTO_REFILL triggered")
        else:
            print("   ❌ Logic STARTED but Incorrect status")
            
        # Verify Persistence & Detailed Fields
        user_doc = db.collection("users").document(test_uid).get()
        persisted_alerts = user_doc.get("refill_alerts")
        if persisted_alerts and len(persisted_alerts) == 1:
            p_alert = persisted_alerts[0]
            if p_alert.get("dosage") == "1 tablet/day": # Default if not set in order
                 print("   ✅ Persistence CORRECT: Alert saved with dosage metadata")
            else:
                 print(f"   ⚠️ Persistence Partial: Dosage missing or incorrect: {p_alert.get('dosage')}")
        else:
             print("   ❌ Persistence FAILED")
             
    else:
        print("   ❌ No alerts generated (Expected 1)")

    # Cleanup
    # db.collection("orders").document(f"ORD-{test_uid}-1").delete()
    # db.collection("users").document(test_uid).delete()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_refill_logic())
