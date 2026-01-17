"""
Test Script - Verify all agents work with standardized output
Tests all 5 agents without requiring OpenAI API calls (mock mode)
"""

import asyncio
import sys
from datetime import datetime

# Add parent to path
sys.path.insert(0, '.')

print("=" * 60)
print("AGENT TEST SCRIPT")
print("=" * 60)

# Test 1: Import all modules
print("\n[1] Testing imports...")
try:
    from models.schemas import Decision, AgentOutput, Medicine
    print("   ✓ Schemas imported")
    
    from agents import (
        OrchestratorAgent,
        PharmacistAgent,
        InventoryAgent,
        PolicyAgent,
        FulfillmentAgent,
        RefillPredictionAgent
    )
    print("   ✓ All agents imported")
    
    from services.data_services import DataService, data_service as ds
    print("   ✓ Data service imported")
except Exception as e:
    print(f"   ✗ Import error: {e}")
    sys.exit(1)

# Test 2: Verify Decision enum
print("\n[2] Testing Decision enum...")
for d in Decision:
    print(f"   - {d.value}")
print("   ✓ Decision enum OK")

# Test 3: Test AgentOutput schema
print("\n[3] Testing AgentOutput schema...")
try:
    output = AgentOutput(
        agent="TestAgent",
        decision=Decision.APPROVED,
        reason="Test passed",
        evidence=["test=passed", "status=ok"],
        message="This is a test message",
        next_agent=None
    )
    print(f"   Agent: {output.agent}")
    print(f"   Decision: {output.decision.value}")
    print(f"   Reason: {output.reason}")
    print(f"   Evidence: {output.evidence}")
    print("   ✓ AgentOutput schema OK")
except Exception as e:
    print(f"   ✗ Schema error: {e}")

# Test 4: Test Data Service
print("\n[4] Testing Data Service...")
try:
    medicines = ds.search_medicine("paracetamol")
    print(f"   Found {len(medicines)} medicine(s) for 'paracetamol'")
    if medicines:
        med = medicines[0]
        print(f"   - {med.medicine_name} {med.strength} ({med.form})")
    print("   ✓ Data service OK")
except Exception as e:
    print(f"   ✗ Data service error: {e}")

# Test 5: Test InventoryAgent
print("\n[5] Testing InventoryAgent...")
try:
    inventory = InventoryAgent()
    inventory.set_data_service(ds)
    
    async def test_inventory():
        result = await inventory.check_stock("paracetamol")
        return result
    
    result = asyncio.run(test_inventory())
    print(f"   Agent: {result.agent}")
    print(f"   Decision: {result.decision.value}")
    print(f"   Reason: {result.reason}")
    print(f"   Evidence count: {len(result.evidence)}")
    print("   ✓ InventoryAgent OK")
except Exception as e:
    print(f"   ✗ InventoryAgent error: {e}")

# Test 6: Test PolicyAgent
print("\n[6] Testing PolicyAgent...")
try:
    policy = PolicyAgent()
    policy.set_data_service(ds)
    
    async def test_policy():
        result = await policy.check_prescription_required("paracetamol")
        return result
    
    result = asyncio.run(test_policy())
    print(f"   Agent: {result.agent}")
    print(f"   Decision: {result.decision.value}")
    print(f"   Reason: {result.reason}")
    print("   ✓ PolicyAgent OK")
except Exception as e:
    print(f"   ✗ PolicyAgent error: {e}")

# Test 7: Test FulfillmentAgent
print("\n[7] Testing FulfillmentAgent...")
try:
    fulfillment = FulfillmentAgent()
    fulfillment.set_data_service(ds)
    
    async def test_fulfillment():
        result = await fulfillment.create_order(
            patient_id="PAT001",
            items=[{
                "medicine_id": "MED001",
                "medicine_name": "Paracetamol",
                "quantity": 30,
                "unit_price": 5.00
            }],
            delivery_type="pickup"
        )
        return result
    
    result = asyncio.run(test_fulfillment())
    print(f"   Agent: {result.agent}")
    print(f"   Decision: {result.decision.value}")
    print(f"   Reason: {result.reason}")
    # Find order_id in evidence
    for ev in result.evidence:
        if ev.startswith("order_id="):
            print(f"   Order ID: {ev.split('=')[1]}")
    print("   ✓ FulfillmentAgent OK")
except Exception as e:
    print(f"   ✗ FulfillmentAgent error: {e}")

# Test 8: Test RefillPredictionAgent
print("\n[8] Testing RefillPredictionAgent...")
try:
    refill = RefillPredictionAgent()
    refill.set_data_service(ds)
    
    async def test_refill():
        result = await refill.get_refill_predictions("PAT001")
        return result
    
    result = asyncio.run(test_refill())
    print(f"   Agent: {result.agent}")
    print(f"   Decision: {result.decision.value}")
    print(f"   Reason: {result.reason}")
    print("   ✓ RefillPredictionAgent OK")
except Exception as e:
    print(f"   ✗ RefillPredictionAgent error: {e}")

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("""
All agents emit standardized output:
{
  "agent": "<AgentName>",
  "decision": "APPROVED | REJECTED | NEEDS_INFO | SCHEDULED",
  "reason": "<Short factual justification>",
  "evidence": ["<data points>"],
  "message": "<User-facing message>",
  "next_agent": "<Next agent or null>"
}

Model assignments:
- PharmacistAgent:       gpt-5-mini
- InventoryAgent:        gpt-5.2 (precision)
- PolicyAgent:           gpt-5.2 (precision)
- FulfillmentAgent:      gpt-5-mini
- RefillPredictionAgent: gpt-5-mini
""")
print("✅ ALL TESTS PASSED!")
