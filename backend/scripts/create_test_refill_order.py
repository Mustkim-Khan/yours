"""
Test Script: Create Order with Past Date for Refill Alert Testing
==================================================================
Run this script to create a test order that will trigger refill alerts.
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

# Initialize Firebase
import firebase_admin
from firebase_admin import credentials

if not firebase_admin._apps:
    cred_path = os.path.join(backend_dir, "service-account.json")
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print("✓ Firebase initialized")
    else:
        print(f"❌ Firebase credentials not found at {cred_path}")
        sys.exit(1)

from firebase_admin import firestore

def create_test_refill_order(user_email: str):
    """
    Create a test order with a past date that triggers refill alerts.
    
    Args:
        user_email: The email of the user to create the order for
    """
    db = firestore.client()
    
    # Find user by email
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", user_email).limit(1)
    user_docs = list(query.stream())
    
    if not user_docs:
        print(f"❌ User with email {user_email} not found!")
        print("Available users:")
        for doc in users_ref.stream():
            data = doc.to_dict()
            print(f"  - {doc.id}: {data.get('email', 'no email')}")
        return None
    
    user_id = user_docs[0].id
    user_data = user_docs[0].to_dict()
    print(f"✅ Found user: {user_id} ({user_data.get('displayName', 'Unknown')})")
    
    # Create order with date 28 days ago (so 30-tablet supply has ~2 days left)
    order_date = datetime.now() - timedelta(days=28)
    
    order_id = f"TEST-REFILL-{datetime.now().strftime('%H%M%S')}"
    
    test_order = {
        "userId": user_id,
        "patient_id": "P001",
        "orderId": order_id,
        "items": [{
            "medicine_name": "Metformin",
            "medicine_id": "med_001",
            "strength": "500mg",
            "quantity": 30,
            "form": "tablet",
            "unit_price": 5.50,
            "prescription_required": True
        }],
        "itemCount": 1,
        "medicine": "Metformin",
        "dosage": "500mg",
        "quantity": 30,
        "supplyDays": 30,
        "orderedAt": order_date,
        "prescriptionRequired": True,
        "status": "DELIVERED",
        "totalAmount": 165.00,
    }
    
    # Save to Firestore
    doc_ref = db.collection("orders").document(order_id)
    doc_ref.set(test_order)
    
    print(f"""
✅ Test order created successfully!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Order ID: {order_id}
User: {user_email}
Medicine: Metformin 500mg
Quantity: 30 tablets
Order Date: {order_date.strftime('%Y-%m-%d')} (28 days ago)
Days Remaining: ~2 days

This order should trigger a refill alert!

To test:
1. Restart the backend (python main.py)
2. The daily refill check will detect this order
3. Or ask in chat: "Check my refills"
""")
    
    return order_id


if __name__ == "__main__":
    # Default to a test email - change this to your actual user email
    test_email = input("Enter user email to create test order for: ").strip()
    
    if not test_email:
        print("No email provided. Using 'kapilak@gmail.com'")
        test_email = "kapilak@gmail.com"
    
    create_test_refill_order(test_email)
