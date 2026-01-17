"""
Voice Service - Speech-to-Text and Text-to-Speech
Uses OpenAI Whisper for STT and OpenAI TTS for speech synthesis.
"""

import os
import io
import base64
from typing import Optional, Tuple
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class VoiceService:
    """
    Voice Service for the Agentic AI Pharmacy.
    
    Features:
    - Speech-to-Text (STT): Convert audio to text using OpenAI Whisper
    - Text-to-Speech (TTS): Convert text to audio using OpenAI TTS
    
    Supported audio formats:
    - Input (STT): mp3, mp4, mpeg, mpga, m4a, wav, webm
    - Output (TTS): mp3, opus, aac, flac
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.stt_model = "whisper-1"
        self.tts_model = "tts-1"  # or "tts-1-hd" for higher quality
        self.tts_voice = "alloy"  # Options: alloy, echo, fable, onyx, nova, shimmer
    
    async def speech_to_text(
        self, 
        audio_data: bytes, 
        audio_format: str = "webm",
        language: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Convert speech audio to text using OpenAI Whisper.
        
        Args:
            audio_data: Audio file bytes
            audio_format: Format of the audio (mp3, wav, webm, etc.)
            language: Optional language code (e.g., "en", "hi", "es")
            
        Returns:
            Tuple of (transcribed_text, detected_language)
        """
        try:
            # Create a file-like object from bytes
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{audio_format}"
            
            # Transcribe using Whisper
            params = {
                "model": self.stt_model,
                "file": audio_file,
                "response_format": "json"
            }
            
            if language:
                params["language"] = language
            
            response = self.client.audio.transcriptions.create(**params)
            
            transcribed_text = response.text
            detected_language = getattr(response, 'language', None)
            
            return transcribed_text, detected_language
            
        except Exception as e:
            raise VoiceServiceError(f"Speech-to-text failed: {str(e)}")
    
    async def text_to_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        output_format: str = "mp3",
        speed: float = 1.0
    ) -> bytes:
        """
        Convert text to speech audio using OpenAI TTS.
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            output_format: Output audio format (mp3, opus, aac, flac)
            speed: Speed of speech (0.25 to 4.0)
            
        Returns:
            Audio data as bytes
        """
        try:
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=voice or self.tts_voice,
                input=text,
                response_format=output_format,
                speed=max(0.25, min(4.0, speed))
            )
            
            # Get audio bytes
            audio_bytes = response.content
            return audio_bytes
            
        except Exception as e:
            error_msg = str(e)
            if "model_not_found" in error_msg:
                raise VoiceServiceError(
                    f"TTS model '{self.tts_model}' not available. "
                    "Your OpenAI account may not have access to TTS APIs. "
                    "Check https://platform.openai.com/docs/guides/text-to-speech"
                )
            raise VoiceServiceError(f"Text-to-speech failed: {error_msg}")
    
    async def text_to_speech_base64(
        self,
        text: str,
        voice: Optional[str] = None,
        output_format: str = "mp3"
    ) -> str:
        """
        Convert text to speech and return as base64 string.
        Useful for sending audio over HTTP JSON responses.
        
        Args:
            text: Text to convert
            voice: Voice to use
            output_format: Output format
            
        Returns:
            Base64 encoded audio string
        """
        audio_bytes = await self.text_to_speech(text, voice, output_format)
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    def set_voice(self, voice: str):
        """
        Set the default TTS voice.
        
        Available voices:
        - alloy: Neutral, balanced
        - echo: Warm, conversational
        - fable: Expressive, storytelling
        - onyx: Deep, authoritative
        - nova: Friendly, upbeat
        - shimmer: Clear, professional
        """
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if voice in valid_voices:
            self.tts_voice = voice
        else:
            raise ValueError(f"Invalid voice. Choose from: {valid_voices}")
    
    def set_model_quality(self, high_quality: bool = False):
        """
        Set TTS model quality.
        
        Args:
            high_quality: If True, use tts-1-hd (higher quality, slower)
        """
        self.tts_model = "tts-1-hd" if high_quality else "tts-1"


class VoiceServiceError(Exception):
    """Custom exception for voice service errors"""
    pass


# Global instance
voice_service = VoiceService()


# ============ CONVENIENCE FUNCTIONS ============

async def transcribe_audio(audio_data: bytes, audio_format: str = "webm") -> str:
    """Transcribe audio to text"""
    text, _ = await voice_service.speech_to_text(audio_data, audio_format)
    return text


async def speak_text(text: str, voice: str = "nova") -> bytes:
    """Convert text to speech audio"""
    return await voice_service.text_to_speech(text, voice)


async def speak_text_base64(text: str, voice: str = "nova") -> str:
    """Convert text to speech and return base64"""
    return await voice_service.text_to_speech_base64(text, voice)