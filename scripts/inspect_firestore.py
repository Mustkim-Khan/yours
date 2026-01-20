import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys

# Setup path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

def inspect_firestore():
    print("🔍 Inspecting Firestore Orders Collection...")
    
    # 1. Initialize Firebase
    try:
        cred = credentials.Certificate('backend/service-account.json')
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"❌ Firebase init failed: {e}")
        return

    db = firestore.client()
    
    # 2. List recent orders
    orders_ref = db.collection("orders")
    # Try multiple queries to find the user's order
    print("Searching for specific order from screenshot: ORD-B7866524...")
    doc = orders_ref.document("ORD-B7866524").get()
    
    docs = []
    if doc.exists:
        print("✅ Found specific order ORD-B7866524!")
        docs = [doc]
    else:
        print("⚠️ specific order ORD-B7866524 not found by ID lookup.")
        print("Listing last 10 orders globally...")
        docs = orders_ref.order_by("orderedAt", direction=firestore.Query.DESCENDING).limit(10).stream()
    
    count = 0
    print("\n📦 RECENT ORDERS IN FIRESTORE:")
    print("-" * 50)
    for doc in docs:
        data = doc.to_dict()
        pid = data.get('userId', 'UNKNOWN_USER')
        med = data.get('medicine', 'Unknown Med')
        qty = data.get('quantity', 0)
        date = data.get('orderedAt')
        status = data.get('status')
        print(f"Order ID: {doc.id}")
        print(f"User ID : {pid}")
        print(f"Item    : {med} (Qty: {qty})")
        print(f"Status  : {status}")
        print(f"Date    : {date}")
        print("-" * 50)
        count += 1
        
    if count == 0:
        print("No orders found in Firestore.")
    else:
        print(f"\nTotal recent orders shown: {count}")

if __name__ == "__main__":
    inspect_firestore()
