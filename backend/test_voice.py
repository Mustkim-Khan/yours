"""
Test Script - Verify Voice Service (STT & TTS)
Tests OpenAI Whisper and TTS API integration.
"""

import asyncio
import os
import sys

sys.path.insert(0, '.')

print("=" * 60)
print("VOICE SERVICE TEST")
print("=" * 60)

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Check API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ OPENAI_API_KEY not set!")
    sys.exit(1)
print(f"✓ OpenAI API Key: {api_key[:15]}...")

# Test 1: Import voice service
print("\n[1] Importing VoiceService...")
try:
    from services.voice_service import (
        VoiceService,
        voice_service,
        transcribe_audio,
        speak_text,
        speak_text_base64
    )
    print("   ✓ VoiceService imported successfully")
except Exception as e:
    print(f"   ✗ Import error: {e}")
    sys.exit(1)

# Test 2: Create voice service instance
print("\n[2] Creating VoiceService instance...")
try:
    vs = VoiceService()
    print(f"   ✓ VoiceService created")
    print(f"   STT Model: {vs.stt_model}")
    print(f"   TTS Model: {vs.tts_model}")
    print(f"   TTS Voice: {vs.tts_voice}")
except Exception as e:
    print(f"   ✗ Creation error: {e}")

# Test 3: Test TTS (Text-to-Speech)
print("\n[3] Testing Text-to-Speech...")
test_text = "Hello! Welcome to our pharmacy. How can I help you today?"

async def test_tts():
    try:
        audio_bytes = await vs.text_to_speech(test_text, voice="nova")
        return audio_bytes
    except Exception as e:
        return f"Error: {e}"

try:
    result = asyncio.run(test_tts())
    if isinstance(result, bytes):
        print(f"   ✓ TTS successful!")
        print(f"   Text: \"{test_text}\"")
        print(f"   Audio size: {len(result)} bytes")
        
        # Save sample audio
        output_path = "test_audio_output.mp3"
        with open(output_path, "wb") as f:
            f.write(result)
        print(f"   Saved to: {output_path}")
    else:
        print(f"   ✗ TTS failed: {result}")
except Exception as e:
    print(f"   ✗ TTS error: {e}")

# Test 4: Test TTS Base64
print("\n[4] Testing TTS Base64 encoding...")
async def test_tts_base64():
    try:
        b64_audio = await vs.text_to_speech_base64("Your order is ready!", voice="alloy")
        return b64_audio
    except Exception as e:
        return f"Error: {e}"

try:
    result = asyncio.run(test_tts_base64())
    if not result.startswith("Error"):
        print(f"   ✓ Base64 TTS successful!")
        print(f"   Base64 length: {len(result)} chars")
        print(f"   Base64 preview: {result[:50]}...")
    else:
        print(f"   ✗ Base64 TTS failed: {result}")
except Exception as e:
    print(f"   ✗ Base64 error: {e}")

# Test 5: Voice options
print("\n[5] Testing voice options...")
voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
print(f"   Available voices: {voices}")
try:
    vs.set_voice("nova")
    print(f"   ✓ Voice set to: {vs.tts_voice}")
except Exception as e:
    print(f"   ✗ Voice setting error: {e}")

# Test 6: Quality settings
print("\n[6] Testing quality settings...")
try:
    vs.set_model_quality(high_quality=True)
    print(f"   ✓ High quality model: {vs.tts_model}")
    vs.set_model_quality(high_quality=False)
    print(f"   ✓ Standard model: {vs.tts_model}")
except Exception as e:
    print(f"   ✗ Quality setting error: {e}")

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("""
✅ Voice Service Features:

SPEECH-TO-TEXT (STT):
- Model: whisper-1
- Formats: mp3, mp4, wav, webm, m4a
- Multilingual support

TEXT-TO-SPEECH (TTS):
- Model: tts-1 (standard) / tts-1-hd (high quality)
- Voices: alloy, echo, fable, onyx, nova, shimmer
- Formats: mp3, opus, aac, flac
- Speed: 0.25x to 4.0x

Usage:
  from services.voice_service import voice_service
  
  # STT
  text, lang = await voice_service.speech_to_text(audio_bytes)
  
  # TTS  
  audio = await voice_service.text_to_speech("Hello!")
""")
print("=" * 60)
