"""
Test Script - Check if AI Model is Responding
Sends a test message to PharmacistAgent to verify OpenAI API connection.
"""

import asyncio
import os
import sys
import warnings
warnings.filterwarnings('ignore')

# Suppress verbose output
os.environ['LANGCHAIN_VERBOSE'] = 'false'

sys.path.insert(0, '.')

print("=" * 60)
print("AI MODEL RESPONSE TEST")
print("=" * 60)

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Check API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ OPENAI_API_KEY not set in .env file!")
    sys.exit(1)
print(f"✓ OpenAI API Key: {api_key[:15]}...")

# Import and test
print("\n[1] Importing PharmacistAgent...")
try:
    from agents import PharmacistAgent
    from services.data_services import data_service
    print("   ✓ Import successful")
except Exception as e:
    print(f"   ✗ Import error: {e}")
    sys.exit(1)

# Create agent with verbose=False
print("\n[2] Creating PharmacistAgent (quiet mode)...")

# Monkey-patch to disable verbose
original_init = PharmacistAgent.__init__
def quiet_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    self.agent_executor.verbose = False
PharmacistAgent.__init__ = quiet_init

try:
    agent = PharmacistAgent()
    print("   ✓ Agent created (gpt-5-mini)")
except Exception as e:
    print(f"   ✗ Agent creation error: {e}")
    sys.exit(1)

# Test message
test_message = "I want ice cream"
print(f"\n[3] Sending: \"{test_message}\"")
print("   Waiting for AI response...")

async def test_agent():
    try:
        result = await agent.process_message(
            test_message,
            session_id="test-session",
            patient_id=None
        )
        return result
    except Exception as e:
        return f"Error: {e}"

# Run the test
try:
    result = asyncio.run(test_agent())
    
    print("\n" + "=" * 60)
    print("AI RESPONSE")
    print("=" * 60)
    
    if hasattr(result, 'agent'):
        print(f"\n✅ Model responded successfully!\n")
        print(f"Agent:    {result.agent}")
        print(f"Decision: {result.decision.value}")
        print(f"Reason:   {result.reason}")
        print(f"\nMessage to user:")
        print(f"  \"{result.message}\"")
        if result.evidence:
            print(f"\nEvidence: {result.evidence}")
        if result.next_agent:
            print(f"Next Agent: {result.next_agent}")
    else:
        print(f"\n❌ Error: {result}")
        
except Exception as e:
    print(f"\n❌ Test failed with error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
