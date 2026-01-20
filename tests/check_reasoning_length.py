
import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from agents.inventory_agent import InventoryAgent
from agents.policy_agent import PolicyAgent
from agents.fulfillment_agent import FulfillmentAgent
from agents.pharmacist_agent import PharmacistAgent
# from services.firestore_service import FirestoreService

async def main():
    print("🧪 Verifying Agent Reasoning Lengths...\n")

    # 1. InventoryAgent
    print("1️⃣ Testing InventoryAgent (Limit: 15 words)...")
    inventory = InventoryAgent()
    # Mock data service for speed
    class MockDataService:
        def search_medicine(self, query):
            from models.schemas import Medicine
            return [Medicine(
                medicine_id="123", medicine_name="Paracetamol", strength="500mg", 
                form="Tablet", stock_level=100, prescription_required=False, 
                category="Pain", discontinued=False
            )]
    inventory.set_data_service(MockDataService())
    
    result = await inventory.check_stock("Paracetamol")
    word_count = len(result.reason.split())
    print(f"   Reason: \"{result.reason}\"")
    print(f"   Word Count: {word_count}")
    if word_count <= 15:
        print("   ✅ PASS")
    else:
        print("   ❌ FAIL")
    print("-" * 50)

    # 2. PolicyAgent
    print("2️⃣ Testing PolicyAgent (Limit: 15 words)...")
    policy = PolicyAgent()
    result = await policy.check_prescription_required("Paracetamol")
    word_count = len(result.reason.split())
    print(f"   Reason: \"{result.reason}\"")
    print(f"   Word Count: {word_count}")
    if word_count <= 15:
        print("   ✅ PASS")
    else:
        print("   ❌ FAIL")
    print("-" * 50)

    # 3. FulfillmentAgent
    print("3️⃣ Testing FulfillmentAgent (Limit: 15 words)...")
    fulfillment = FulfillmentAgent()
    # Mock order creation
    items = [{"medicine_name": "Paracetamol", "quantity": 1, "unit_price": 5.0}]
    result = await fulfillment.create_order("patient-123", items)
    word_count = len(result.reason.split())
    print(f"   Reason: \"{result.reason}\"")
    print(f"   Word Count: {word_count}")
    if word_count <= 15:
        print("   ✅ PASS")
    else:
        print("   ❌ FAIL")
    print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
