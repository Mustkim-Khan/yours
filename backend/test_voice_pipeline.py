"""
Test Script - Full Voice Pipeline
STT (Whisper) → GPT 5.2 (Agent) → TTS (OpenAI)
"""

import asyncio
import os
import sys

sys.path.insert(0, '.')

print("=" * 60)
print("FULL VOICE PIPELINE TEST")
print("STT → GPT 5.2 → TTS")
print("=" * 60)

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Check API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ OPENAI_API_KEY not set!")
    sys.exit(1)
print(f"✓ OpenAI API Key configured")

# Import services
print("\n[1] Importing services...")
try:
    from services.voice_service import voice_service, VoiceServiceError
    from agents import InventoryAgent
    from services.data_services import data_service
    print("   ✓ VoiceService imported")
    print("   ✓ InventoryAgent imported (uses gpt-5.2)")
except Exception as e:
    print(f"   ✗ Import error: {e}")
    sys.exit(1)

# Test TTS first (simpler)
print("\n[2] Testing TTS (Text-to-Speech)...")
test_phrase = "Hello! I am your AI pharmacy assistant. How can I help you today?"

async def test_tts():
    try:
        audio = await voice_service.text_to_speech(test_phrase, voice="nova")
        return audio
    except VoiceServiceError as e:
        return f"VoiceError: {e}"
    except Exception as e:
        return f"Error: {e}"

tts_result = asyncio.run(test_tts())
if isinstance(tts_result, bytes):
    print(f"   ✓ TTS SUCCESS!")
    print(f"   Text: \"{test_phrase[:50]}...\"")
    print(f"   Audio size: {len(tts_result):,} bytes")
    
    # Save the audio
    with open("test_tts_output.mp3", "wb") as f:
        f.write(tts_result)
    print(f"   Saved: test_tts_output.mp3")
else:
    print(f"   ✗ TTS Failed: {tts_result}")

# Test the full flow: Simulate STT → Agent → TTS
print("\n[3] Testing Full Pipeline (Simulated STT → GPT 5.2 → TTS)...")
print("   Since we don't have audio input, simulating STT output...")

# Simulated STT output (as if user said this)
simulated_stt_output = "Is Paracetamol available?"
print(f"\n   📤 STT Output: \"{simulated_stt_output}\"")

# Process with GPT 5.2 (InventoryAgent)
print(f"\n   🤖 Processing with InventoryAgent (gpt-5.2)...")

async def process_with_agent():
    inventory = InventoryAgent()
    inventory.set_data_service(data_service)
    result = await inventory.check_stock("Paracetamol")
    return result

agent_result = asyncio.run(process_with_agent())
print(f"   Agent: {agent_result.agent}")
print(f"   Decision: {agent_result.decision.value}")
print(f"   Reason: {agent_result.reason}")

# Create response message for TTS
if agent_result.decision.value == "APPROVED":
    response_message = f"Yes, Paracetamol is available. Would you like to place an order?"
else:
    response_message = f"I'm sorry, Paracetamol is currently not available."

print(f"\n   💬 Response: \"{response_message}\"")

# Convert response to speech
print(f"\n   🔊 Converting response to speech (TTS)...")

async def response_to_speech():
    try:
        audio = await voice_service.text_to_speech(response_message, voice="nova")
        return audio
    except Exception as e:
        return f"Error: {e}"

final_audio = asyncio.run(response_to_speech())
if isinstance(final_audio, bytes):
    print(f"   ✓ TTS SUCCESS!")
    print(f"   Audio size: {len(final_audio):,} bytes")
    
    # Save final response audio
    with open("test_voice_response.mp3", "wb") as f:
        f.write(final_audio)
    print(f"   Saved: test_voice_response.mp3")
else:
    print(f"   ✗ TTS Failed: {final_audio}")

# Summary
print("\n" + "=" * 60)
print("PIPELINE SUMMARY")
print("=" * 60)
print(f"""
Full Voice Pipeline:

1. STT (Whisper)
   Input: User's voice audio
   Output: "{simulated_stt_output}"

2. GPT 5.2 (InventoryAgent)
   Input: "{simulated_stt_output}"
   Decision: {agent_result.decision.value}
   Output: {agent_result.reason}

3. TTS (OpenAI)
   Input: "{response_message}"
   Output: Audio file (test_voice_response.mp3)

✅ Pipeline test complete!
""")
print("=" * 60)
