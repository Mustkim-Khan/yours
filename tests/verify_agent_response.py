import asyncio
import os
import sys
from dotenv import load_dotenv

# Setup path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Load environment
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import OrchestratorRequest

async def verify_agent():
    print("🧪 Verifying Agent Response Logic...")
    
    orchestrator = OrchestratorAgent()
    
    # Simulate a request
    request = OrchestratorRequest(
        session_id="test-session-123",
        user_message="Hello, do you have Paracetamol?",
        patient_id="msg-test-id",
        user_name="Test User",
        user_id="TEST_UID_123"
    )
    
    print(f"📩 Sending message: '{request.user_message}'")
    
    try:
        response = await orchestrator.process_request(request)
        print("\n✅ Agent Responded Successfully!")
        print(f"🤖 Response: {response.response_text}")
        print(f"🔗 Chain: {response.agent_chain}")
        print(f"🛡️ Safety Warnings: {response.safety_warnings}")
    except Exception as e:
        print(f"\n❌ Agent Failed to Respond:")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_agent())
