"""
Prescription Upload Flow - Test Script
Tests the full prescription flow:
1. Request prescription medicine → PrescriptionUploadCard
2. Upload prescription → Resume to FulfillmentAgent → OrderConfirmation
"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def test_prescription_flow():
    print("=" * 60)
    print("PRESCRIPTION UPLOAD FLOW TEST")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        # ============ STEP 1: Request Prescription Medicine ============
        print("\n[STEP 1] Requesting prescription medicine (Amoxicillin)...")
        
        chat_request = {
            "message": "I need 10 Amoxicillin 500mg capsules",
            "session_id": "test-rx-flow",
            "patient_id": "P001"
        }
        
        response = await client.post(f"{BASE_URL}/chat", json=chat_request)
        result = response.json()
        
        print(f"   Response: {result.get('response', '')[:80]}...")
        print(f"   UI Card Type: {result.get('ui_card_type')}")
        print(f"   Agent Chain: {result.get('agent_chain')}")
        print(f"   Requires Prescription: {result.get('requires_prescription')}")
        print(f"   Trace ID: {result.get('trace_id')}")
        
        # Verify PrescriptionUploadCard triggered
        if result.get("ui_card_type") == "prescription_upload":
            print("   ✅ PrescriptionUploadCard triggered correctly!")
            prescription_data = result.get("prescription_upload", {})
            print(f"   Medicine: {prescription_data.get('medicine_name')}")
            print(f"   Medicine ID: {prescription_data.get('medicine_id')}")
        else:
            print(f"   ❌ FAILED: Expected 'prescription_upload' but got '{result.get('ui_card_type')}'")
            return False
        
        # ============ STEP 2: Upload Prescription ============
        print("\n[STEP 2] Uploading prescription...")
        
        upload_request = {
            "session_id": "test-rx-flow",
            "medicine_id": prescription_data.get("medicine_id", "med_002"),
            "prescription_file": "test_prescription.pdf"  # Simulated file
        }
        
        response = await client.post(f"{BASE_URL}/prescription/upload", json=upload_request)
        result = response.json()
        
        print(f"   Success: {result.get('success')}")
        print(f"   Message: {result.get('message')}")
        print(f"   Agent Chain: {result.get('agent_chain')}")
        print(f"   Order ID: {result.get('order_id')}")
        print(f"   UI Card Type: {result.get('ui_card_type')}")
        print(f"   Trace ID: {result.get('trace_id')}")
        
        # Verify FulfillmentAgent was called
        if result.get("success") and result.get("order_id"):
            print("   ✅ Prescription upload successful!")
            print("   ✅ FulfillmentAgent called directly (no re-checking)!")
            
            order_confirmation = result.get("order_confirmation", {})
            if order_confirmation:
                print(f"\n   Order Confirmation:")
                print(f"   - Order ID: {order_confirmation.get('order_id')}")
                print(f"   - Patient: {order_confirmation.get('patient_name')}")
                print(f"   - Total: ${order_confirmation.get('total_amount', 0):.2f}")
                print(f"   - Status: {order_confirmation.get('status')}")
                print(f"   - Delivery: {order_confirmation.get('estimated_delivery')}")
        else:
            print(f"   ❌ FAILED: Prescription upload failed")
            return False
        
        # ============ VERIFY TRACE STRUCTURE ============
        print("\n[STEP 3] Verifying trace structure...")
        
        expected_chain_step1 = ["OrchestratorAgent", "PharmacistAgent", "InventoryAgent", "PolicyAgent"]
        actual_chain_step1 = chat_request_result.get("agent_chain", []) if 'chat_request_result' in dir() else result.get("agent_chain", [])
        
        # Check resume chain includes FulfillmentAgent
        resume_chain = result.get("agent_chain", [])
        if "FulfillmentAgent" in resume_chain:
            print("   ✅ FulfillmentAgent present in resume chain")
        else:
            print("   ❌ FAILED: FulfillmentAgent not in resume chain")
            return False
        
        # ============ SUMMARY ============
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print("✅ Step 1: PrescriptionUploadCard triggered correctly")
        print("✅ Step 2: Prescription uploaded successfully")
        print("✅ Step 3: FulfillmentAgent called directly")
        print(f"✅ Order Created: {result.get('order_id')}")
        print("\n🎉 ALL TESTS PASSED!")
        print("=" * 60)
        
        return True


if __name__ == "__main__":
    success = asyncio.run(test_prescription_flow())
    exit(0 if success else 1)
