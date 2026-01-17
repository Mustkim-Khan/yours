"""
Test Script - Verify LangSmith Tracing is Working
Tests tracing configuration and makes a sample traced call.
"""

import asyncio
import os
import sys

sys.path.insert(0, '.')

print("=" * 60)
print("LANGSMITH TRACING TEST")
print("=" * 60)

# Test 1: Check environment variables
print("\n[1] Checking environment variables...")
from dotenv import load_dotenv
load_dotenv()

env_vars = {
    "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2"),
    "LANGCHAIN_API_KEY": os.getenv("LANGCHAIN_API_KEY"),
    "LANGCHAIN_PROJECT": os.getenv("LANGCHAIN_PROJECT"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")
}

all_set = True
for var, value in env_vars.items():
    if value:
        masked = value[:8] + "..." if len(value) > 8 else value
        print(f"   ✓ {var} = {masked}")
    else:
        print(f"   ✗ {var} = NOT SET")
        if var != "LANGCHAIN_PROJECT":  # Project is optional
            all_set = False

if not all_set:
    print("\n   ⚠️  Some required environment variables are missing!")
    print("   Create a .env file with:")
    print("   LANGCHAIN_TRACING_V2=true")
    print("   LANGCHAIN_API_KEY=your_key")
    print("   OPENAI_API_KEY=your_key")

# Test 2: Import tracing utilities
print("\n[2] Importing tracing utilities...")
try:
    from utils.tracing import (
        init_langsmith,
        get_trace_id,
        agent_span,
        tool_span,
        delegation_span,
        decision_span
    )
    print("   ✓ All tracing utilities imported")
except Exception as e:
    print(f"   ✗ Import error: {e}")
    sys.exit(1)

# Test 3: Initialize LangSmith
print("\n[3] Initializing LangSmith...")
try:
    init_langsmith()
    print("   ✓ LangSmith initialized")
except Exception as e:
    print(f"   ✗ Initialization error: {e}")

# Test 4: Test traced function
print("\n[4] Testing traced function...")
try:
    from langsmith import traceable
    
    @traceable(name="test_trace_function", run_type="chain")
    def test_traced_function(input_text: str) -> dict:
        """A simple traced function for testing"""
        return {
            "input": input_text,
            "output": f"Processed: {input_text}",
            "status": "success"
        }
    
    result = test_traced_function("Hello LangSmith!")
    print(f"   ✓ Traced function executed")
    print(f"   Result: {result}")
except Exception as e:
    print(f"   ✗ Traced function error: {e}")

# Test 5: Test agent with tracing
print("\n[5] Testing InventoryAgent with tracing...")
try:
    from agents import InventoryAgent
    from services.data_services import data_service
    
    inventory = InventoryAgent()
    inventory.set_data_service(data_service)
    
    async def test_inventory_trace():
        result = await inventory.check_stock("paracetamol")
        return result
    
    result = asyncio.run(test_inventory_trace())
    print(f"   ✓ InventoryAgent traced call completed")
    print(f"   Agent: {result.agent}")
    print(f"   Decision: {result.decision.value}")
    print(f"   Reason: {result.reason}")
    
    # Try to get trace ID
    trace_id = get_trace_id()
    if trace_id:
        print(f"   Trace ID: {trace_id}")
    else:
        print("   Note: Trace ID available only during active trace")
        
except Exception as e:
    print(f"   ✗ Agent trace error: {e}")

# Test 6: Verify LangSmith connection
print("\n[6] Verifying LangSmith connection...")
api_key = os.getenv("LANGCHAIN_API_KEY")
if api_key and api_key.startswith("lsv2_"):
    print("   ✓ LangSmith API key format is valid")
    print("   ✓ Traces should appear at: https://smith.langchain.com")
    project = os.getenv("LANGCHAIN_PROJECT", "default")
    print(f"   Project: {project}")
else:
    print("   ⚠️  LangSmith API key may not be configured correctly")

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)

if os.getenv("LANGCHAIN_TRACING_V2") == "true" and os.getenv("LANGCHAIN_API_KEY"):
    print("""
✅ LangSmith tracing is CONFIGURED!

Traces will be sent to: https://smith.langchain.com

Each agent call will show:
- OrchestratorAgent.process_request
  └─ PharmacistAgent.process
     └─ InventoryAgent.check_stock
     └─ PolicyAgent.check_prescription
     └─ FulfillmentAgent.create_order

To view traces:
1. Go to https://smith.langchain.com
2. Select your project
3. View runs with full agent chain
""")
else:
    print("""
⚠️  LangSmith tracing is NOT fully configured!

To enable tracing, add to your .env file:
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your_key_here
LANGCHAIN_PROJECT=agentic-pharmacy

Get your API key at: https://smith.langchain.com/settings
""")
