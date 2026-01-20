import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys

# Setup path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

def verify_persistence():
    print("🧪 Verifying Firestore Persistence...")
    
    # 1. Initialize Firebase
    try:
        cred = credentials.Certificate('backend/service-account.json')
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized")
    except Exception as e:
        print(f"❌ Firebase init failed: {e}")
        return

    db = firestore.client()
    
    # 2. Test Write
    test_uid = "TEST_USER_VERIFY"
    test_order_id = "ORD-TEST-123"
    
    doc_ref = db.collection("orders").document(test_order_id)
    doc_ref.set({
        "userId": test_uid,
        "orderId": test_order_id,
        "medicine": "Test Medicine",
        "quantity": 1,
        "orderedAt": firestore.SERVER_TIMESTAMP,
        "status": "CONFIRMED"
    })
    print("✅ Write operation completed")
    
    # 3. Test Read (Filtered)
    orders_ref = db.collection("orders")
    query = orders_ref.where("userId", "==", test_uid).limit(1)
    results = list(query.stream())
    
    if len(results) == 1 and results[0].id == test_order_id:
        print("✅ Read verification successful: Found correct order filtered by userId")
    else:
        print(f"❌ Read verification failed. Found {len(results)} orders.")
        
    # 4. Cleanup
    doc_ref.delete()
    print("✅ Cleanup completed")

if __name__ == "__main__":
    verify_persistence()
