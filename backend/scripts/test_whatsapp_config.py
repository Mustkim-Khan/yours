"""
Test Script: Verify WhatsApp Configuration
===========================================
"""

import os
import sys

# Add parent directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

# Load env vars
from dotenv import load_dotenv
load_dotenv()

print("Checking Twilio Configuration...")
acc_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")

print(f"SID: {'✅ Found' if acc_sid else '❌ Missing'}")
print(f"Token: {'✅ Found' if auth_token else '❌ Missing'}")
print(f"From: {whatsapp_from if whatsapp_from else '❌ Missing'}")

if not (acc_sid and auth_token and whatsapp_from):
    print("❌ Configuration incomplete. Please check .env")
    sys.exit(1)

from services.whatsapp_service import send_order_confirmation_whatsapp

print("\nSending test message...")
# Replace with a real number if known, or ask user input
test_phone = input("Enter phone number to test (e.g. +919876543210): ").strip()

if not test_phone:
    print("Skipping send test.")
else:
    mock_order = {
        "order_id": "TEST-123",
        "items": [{"medicine_name": "Test Medicine", "quantity": 1}],
        "delivery_estimate": "Today"
    }
    
    result = send_order_confirmation_whatsapp(test_phone, "Test User", mock_order)
    
    if result:
        print("✅ SUCCESS: WhatsApp message sent!")
    else:
        print("❌ FAILURE: Failed to send message. Check credentials/sandbox status.")
