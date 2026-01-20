import asyncio
import os
import sys
from dotenv import load_dotenv

# Setup path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Load environment
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import OrchestratorRequest
import firebase_admin
from firebase_admin import credentials, firestore

from services.firestore_service import get_orders
from services.data_services import DataService  # Import DataService class

async def verify_flow():
    print("🧪 Verifying Full Order Flow (Order -> Confirm -> Persist -> Recall)...")
    
    # Initialize Firebase
    try:
        cred = credentials.Certificate('backend/service-account.json')
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized")
    except Exception as e:
        print(f"❌ Firebase init failed: {e}")
        return

    # Initialize DataService
    data_service = DataService()
    
    orchestrator = OrchestratorAgent()
    orchestrator.set_data_service(data_service) # Inject Dependencies
    
    user_id = "TEST_USER_FLOW_V1"
    session_id = "sess-flow-1"
    
    # 1. Place Order Request
    print("\n1️⃣ Asking for Aspirin...")
    req1 = OrchestratorRequest(
        session_id=session_id,
        user_message="I want 10 Paracetamol",
        patient_id="msg-test-id",
        user_name="Flow Tester",
        user_id=user_id
    )
    res1 = await orchestrator.process_request(req1)
    print(f"🤖 Response: {res1.response_text}")
    print(f"🃏 UI Card: {res1.ui_card_type}")
    
    if res1.ui_card_type != "order_preview":
        print("❌ Failed to get order preview")
        return

    # 2. Confirm Order
    print("\n2️⃣ Confirming Order...")
    req2 = OrchestratorRequest(
        session_id=session_id,
        user_message="confirm",
        patient_id="msg-test-id",
        user_name="Flow Tester",
        user_id=user_id
    )
    res2 = await orchestrator.process_request(req2)
    print(f"🤖 Response: {res2.response_text}")
    print(f"📦 Order Created: {res2.order_created}")
    
    if not res2.order_created:
        print("❌ Failed to create order")
        return

    # 3. Verify Firestore
    print("\n3️⃣ Checking Firestore...")
    orders = get_orders(user_id)
    found = False
    for o in orders:
        if o['orderId'] == res2.order_created:
            print(f"✅ Order {o['orderId']} found in Firestore!")
            print(f"   Item: {o.get('medicine')} x{o.get('quantity')}")
            found = True
            break
    
    if not found:
        print("❌ Order NOT found in Firestore")
        return

    # 4. Ask History
    print("\n4️⃣ Asking 'What did I order?'...")
    req3 = OrchestratorRequest(
        session_id=session_id,
        user_message="what did I order recently?",
        patient_id="msg-test-id",
        user_name="Flow Tester",
        user_id=user_id
    )
    res3 = await orchestrator.process_request(req3)
    print(f"🤖 Response: {res3.response_text}")
    
    if "aspirin" in res3.response_text.lower():
        print("✅ Agent correctly recalled the order!")
    else:
        print("⚠️ Agent might not have recalled correctly. Check response.")

if __name__ == "__main__":
    asyncio.run(verify_flow())
