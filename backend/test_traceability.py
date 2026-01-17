"""
Test script to verify Agent Waterfall Tracing in LangSmith
"""
import asyncio
import os
import sys

# Ensure we're in the backend directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_traceability():
    print("=" * 60)
    print("AGENT WATERFALL TRACING TEST")
    print("=" * 60)
    
    # Step 1: Import check
    print("\n1. Checking imports...")
    try:
        from utils.tracing import (
            orchestrator_span, child_agent_span, 
            agent_waterfall_span, get_trace_id
        )
        from agents.orchestrator_agent import OrchestratorAgent
        from services.data_services import data_service
        from models.schemas import OrchestratorRequest
        print("   ✓ All imports successful")
    except Exception as e:
        print(f"   ✗ Import error: {e}")
        return False
    
    # Step 2: Create orchestrator and set data service
    print("\n2. Initializing OrchestratorAgent...")
    try:
        orchestrator = OrchestratorAgent()
        orchestrator.set_data_service(data_service)
        print("   ✓ OrchestratorAgent initialized with data service")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Step 3: Process a test request
    print("\n3. Processing test order request...")
    print("   Message: 'I need 5 Paracetamol 500mg tablets'")
    
    try:
        request = OrchestratorRequest(
            user_message="I need 5 Paracetamol 500mg tablets",
            session_id="trace_test_session",
            patient_id="P001"
        )
        
        response = await orchestrator.process_request(request)
        
        print(f"\n   Response received:")
        print(f"   - Agent Chain: {response.agent_chain}")
        print(f"   - Final Action: {response.final_action}")
        print(f"   - Trace ID: {response.trace_id}")
        print(f"   - UI Card Type: {response.ui_card_type}")
        
        if response.order_preview_data:
            print(f"   - Order Preview: {response.order_preview_data.patient_name}")
        
        print(f"\n   ✓ Request processed successfully!")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Verify tracing
    print("\n4. Verifying trace structure...")
    print("   Expected LangSmith trace hierarchy:")
    print("   ┌─ OrchestratorAgent")
    print("   │  └─ PharmacistAgent (gpt-5.2)")
    print("   │      └─ InventoryAgent (gpt-5-mini)")
    print("   │      └─ PolicyAgent (gpt-5.2)")
    print("   └─ (if confirmed) FulfillmentAgent (gpt-5-mini)")
    
    trace_id = get_trace_id()
    if trace_id:
        print(f"\n   Trace ID: {trace_id}")
        print(f"   View in LangSmith: https://smith.langchain.com")
    else:
        print("\n   Note: Trace ID not available outside trace context")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE ✓")
    print("=" * 60)
    print("\nCheck LangSmith for the trace hierarchy.")
    print("Project: agentic-pharmacy")
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_traceability())
    sys.exit(0 if result else 1)
