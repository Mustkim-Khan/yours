"""
Test Script - Verify Multi-Item Order Flow
Tests that multiple medicines in a single request are correctly handled.
"""

import asyncio
import os
import sys

sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("MULTI-ITEM ORDER FLOW TEST")
print("=" * 70)

# Initialize services
print("\n[1] Initializing services...")
from utils.tracing import init_langsmith
init_langsmith()

from services.data_services import data_service
from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import OrchestratorRequest

print("   ✓ Services initialized")


async def test_multi_item_order():
    """Test that multiple medicines are properly aggregated into one order."""
    
    orchestrator = OrchestratorAgent()
    orchestrator.set_data_service(data_service)
    
    print("\n" + "-" * 70)
    print("[2] Testing Multi-Item Order Request")
    print("-" * 70)
    
    # Step 1: Send a multi-medicine request
    request = OrchestratorRequest(
        session_id="test-multi-item-001",
        user_message="I want to order 5 paracetamol tablets and 3 cetirizine tablets",
        patient_id="PAT001",
        user_name="Test User",
        user_id="test-user-123"
    )
    
    print(f"   📝 Request: {request.user_message}")
    
    response = await orchestrator.process_request(request)
    
    print(f"\n   📊 Response:")
    print(f"      Agent Chain: {' → '.join(response.agent_chain)}")
    print(f"      Final Action: {response.final_action}")
    print(f"      Response Text: {response.response_text[:100]}..." if len(response.response_text) > 100 else f"      Response Text: {response.response_text}")
    
    # Check order preview data
    if response.order_preview_data:
        preview = response.order_preview_data
        print(f"\n   ✅ Order Preview Generated!")
        print(f"      Preview ID: {preview.preview_id}")
        print(f"      Items Count: {len(preview.items)}")
        
        for i, item in enumerate(preview.items):
            print(f"      Item {i+1}: {item.medicine_name} - Qty: {item.quantity} @ ${item.unit_price:.2f}")
        
        print(f"      Total Amount: ${preview.total_amount:.2f}")
        print(f"      Requires Prescription: {preview.requires_prescription}")
        
        if len(preview.items) >= 2:
            print("\n   🎉 MULTI-ITEM TEST PASSED!")
            return True, preview
        else:
            print(f"\n   ⚠️  Expected 2+ items, got {len(preview.items)}")
            return False, preview
    else:
        print("\n   ❌ No order preview generated")
        return False, None


async def run_tests():
    results = {}
    
    # Test 1: Multi-item order request
    passed, preview = await test_multi_item_order()
    results["multi_item_request"] = "PASS" if passed else "FAIL"
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    all_passed = all(v == "PASS" for v in results.values())
    
    for test, result in results.items():
        status = "✅" if result == "PASS" else "❌"
        print(f"   {status} {test}: {result}")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
    
    return all_passed


# Run tests
if __name__ == "__main__":
    asyncio.run(run_tests())
