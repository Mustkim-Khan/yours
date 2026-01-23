"""
Test Script - Verify Agent Reasoning in LangSmith Traces
Tests all four agents (Policy, Inventory, Refill, Fulfillment) to ensure 
reasoning generation works after commenting out max_completion_tokens.
"""

import asyncio
import os
import sys

sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("AGENT REASONING VERIFICATION TEST")
print("=" * 70)

# Check environment
print("\n[1] Checking environment variables...")
required_vars = ["OPENAI_API_KEY", "LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2"]
for var in required_vars:
    value = os.getenv(var)
    if value:
        masked = value[:10] + "..." if len(value) > 10 else value
        print(f"   ✓ {var} = {masked}")
    else:
        print(f"   ✗ {var} = NOT SET")

# Initialize tracing
print("\n[2] Initializing LangSmith tracing...")
from utils.tracing import init_langsmith
init_langsmith()
print("   ✓ LangSmith initialized")

# Initialize data service
print("\n[3] Loading data service...")
from services.data_services import data_service
print("   ✓ Data service loaded")


async def test_agents():
    results = {}
    
    # Test 1: PolicyAgent
    print("\n" + "-" * 70)
    print("[4] Testing PolicyAgent._generate_reasoning...")
    print("-" * 70)
    try:
        from agents.policy_agent import PolicyAgent
        policy = PolicyAgent()
        policy.set_data_service(data_service)
        
        # Test prescription check (triggers reasoning)
        result = await policy.check_prescription_required("Paracetamol")
        print(f"   Agent: {result.agent}")
        print(f"   Decision: {result.decision.value}")
        print(f"   Reason: {result.reason}")
        print(f"   ✓ PolicyAgent reasoning working!")
        results["PolicyAgent"] = {"status": "✓ PASS", "reason": result.reason}
    except Exception as e:
        print(f"   ✗ PolicyAgent ERROR: {e}")
        results["PolicyAgent"] = {"status": "✗ FAIL", "error": str(e)}
    
    # Test 2: InventoryAgent
    print("\n" + "-" * 70)
    print("[5] Testing InventoryAgent._generate_reasoning...")
    print("-" * 70)
    try:
        from agents.inventory_agent import InventoryAgent
        inventory = InventoryAgent()
        inventory.set_data_service(data_service)
        
        result = await inventory.check_stock("Metformin", form="Tablet", dosage="500mg")
        print(f"   Agent: {result.agent}")
        print(f"   Decision: {result.decision.value}")
        print(f"   Reason: {result.reason}")
        print(f"   ✓ InventoryAgent reasoning working!")
        results["InventoryAgent"] = {"status": "✓ PASS", "reason": result.reason}
    except Exception as e:
        print(f"   ✗ InventoryAgent ERROR: {e}")
        results["InventoryAgent"] = {"status": "✗ FAIL", "error": str(e)}
    
    # Test 3: RefillPredictionAgent
    print("\n" + "-" * 70)
    print("[6] Testing RefillPredictionAgent._generate_reasoning...")
    print("-" * 70)
    try:
        from agents.refill_prediction_agent import RefillPredictionAgent
        refill = RefillPredictionAgent()
        refill.set_data_service(data_service)
        
        result = await refill.get_refill_predictions("PAT001")
        print(f"   Agent: {result.agent}")
        print(f"   Decision: {result.decision.value}")
        print(f"   Reason: {result.reason}")
        print(f"   ✓ RefillPredictionAgent reasoning working!")
        results["RefillPredictionAgent"] = {"status": "✓ PASS", "reason": result.reason}
    except Exception as e:
        print(f"   ✗ RefillPredictionAgent ERROR: {e}")
        results["RefillPredictionAgent"] = {"status": "✗ FAIL", "error": str(e)}
    
    # Test 4: FulfillmentAgent
    print("\n" + "-" * 70)
    print("[7] Testing FulfillmentAgent._generate_reasoning...")
    print("-" * 70)
    try:
        from agents.fulfillment_agent import FulfillmentAgent
        fulfillment = FulfillmentAgent()
        fulfillment.set_data_service(data_service)
        
        result = await fulfillment.create_order(
            patient_id="PAT001",
            items=[{"medicine_name": "Paracetamol", "quantity": 10, "unit_price": 5.00}],
            delivery_type="pickup"
        )
        print(f"   Agent: {result.agent}")
        print(f"   Decision: {result.decision.value}")
        print(f"   Reason: {result.reason}")
        print(f"   ✓ FulfillmentAgent reasoning working!")
        results["FulfillmentAgent"] = {"status": "✓ PASS", "reason": result.reason}
    except Exception as e:
        print(f"   ✗ FulfillmentAgent ERROR: {e}")
        results["FulfillmentAgent"] = {"status": "✗ FAIL", "error": str(e)}
    
    return results


# Run tests
print("\n🚀 Running agent reasoning tests...\n")
results = asyncio.run(test_agents())

# Summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)

all_passed = True
for agent, data in results.items():
    status = data["status"]
    if "FAIL" in status:
        all_passed = False
    reason_preview = data.get("reason", data.get("error", "N/A"))
    if len(str(reason_preview)) > 60:
        reason_preview = str(reason_preview)[:60] + "..."
    print(f"   {agent}: {status}")
    print(f"      Reasoning: {reason_preview}")

print("\n" + "=" * 70)
if all_passed:
    print("✅ ALL AGENTS PASSED - Reasoning is working correctly!")
    print("\n📊 Check LangSmith traces at: https://smith.langchain.com")
    project = os.getenv("LANGCHAIN_PROJECT", "default")
    print(f"   Project: {project}")
else:
    print("❌ SOME AGENTS FAILED - Check errors above")
print("=" * 70)
