import asyncio
import requests
import json
import sys
import os

# Add backend directory to path to import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.cart_service import cart_service
from services.data_services import data_service

BASE_URL = "http://127.0.0.1:8000"
TEST_USER_ID = "test_user_123"
TEST_SESSION_ID = "session_test_123"

def test_add_to_cart():
    print(f"🧪 Starting Cart Flow Test...")
    
    # 1. Clear existing cart
    print(f"🧹 Clearing cart for user {TEST_USER_ID}...")
    cart_service.clear_cart(TEST_USER_ID)
    
    # 2. Send Chat Request
    payload = {
        "message": "Add 2 Paracetamol to my cart",
        "session_id": TEST_SESSION_ID,
        "patient_id": "P001",
        "user_name": "Test User",
        # Simulate authenticated user via direct injection if needed, 
        # but for main.py check, we might need a workaround if auth is strict.
        # Looking at main.py, user_id comes from token.
        # BUT orchestrator uses request.user_id if passed in orchestrator request.
        # The /chat endpoint extracts it from current_user.
        # For this test to work with the running server, we need to bypass auth or use a token.
        # OR we can test the Orchestrator directly?
        # User asked for a script, likely "run against server".
        # Let's try sending a header if auth is enabled, or mock it.
        # If firestore is real, we can just check the db results.
    }
    
    # We can't easily mock auth middleware from outside without a token.
    # However, for the purpose of this test script running IN the backend env,
    # we can instantiate the orchestrator directly to test the LOGIC.
    pass

async def test_logic_directly():
    print(f"\n🧪 Testing Orchestrator Logic Directly...")
    
    # 1. Clear Cart
    print(f"🧹 Clearing cart for {TEST_USER_ID}...")
    cart_service.clear_cart(TEST_USER_ID)
    
    # 2. Instantiate Orchestrator
    from agents.orchestrator_agent import OrchestratorAgent
    from models.schemas import OrchestratorRequest
    
    orchestrator = OrchestratorAgent()
    orchestrator.set_data_service(data_service)
    
    # 3. Process Request
    req = OrchestratorRequest(
        session_id=TEST_SESSION_ID,
        user_message="Add 2 Paracetamol to my cart",
        patient_id="P001",
        user_name="Test User",
        user_id=TEST_USER_ID,
        conversation_id="test_conv_123"
    )
    
    print(f"📤 Sending request: '{req.user_message}'")
    response = await orchestrator.process_request(req)
    
    print(f"📥 Agent Response: {response.response_text}")
    print(f"🔗 Agent Chain: {response.agent_chain}")
    
    # 4. Verify Cart
    cart = cart_service.get_cart(TEST_USER_ID)
    items = cart.get("items", [])
    
    print(f"\n🛒 Cart Content Check:")
    if not items:
        print("❌ Cart is empty!")
    else:
        print(f"✅ Found {len(items)} items in cart:")
        for item in items:
            print(f"   - {item.get('medicine_name')} x{item.get('quantity')}")
            
        # Assertion
        has_paracetamol = any(i['medicine_name'].lower() == 'paracetamol' and i['quantity'] == 2 for i in items)
        if has_paracetamol:
            print("\n🎉 SUCCESS: Paracetamol x2 found in cart!")
        else:
            print("\n❌ FAILURE: Paracetamol x2 NOT found in cart.")

if __name__ == "__main__":
    asyncio.run(test_logic_directly())
