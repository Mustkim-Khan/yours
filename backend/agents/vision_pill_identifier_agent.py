"""
VisionPillIdentifierAgent - GPT Vision Pill Identification
============================================================
Uses GPT Vision to analyze pill images and suggest possible medicine matches.
This agent ONLY suggests - final confirmation is required from user.

IMPORTANT: This is AI-assisted identification and does NOT replace pharmacist judgment.
"""

import os
import json
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from models.schemas import AgentOutput, Decision
from utils.tracing import agent_trace

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Model configuration
MODEL_NAME = "gpt-5.2"  # Vision-capable model

PILL_IDENTIFICATION_PROMPT = """You are an AI pill identification assistant. Analyze this pill image and identify possible medicines based on visual characteristics.

IMPORTANT RULES:
1. NEVER claim 100% certainty - always express as "possible match" or "likely"
2. Identify based on: shape, color, size, imprints/markings, coating type
3. Provide 1-3 most likely candidates with confidence levels
4. If image is unclear, blurry, or not a pill, say so clearly

Analyze the pill and respond in this EXACT JSON format:
{
    "is_pill_image": true/false,
    "possible_medicines": [
        {
            "name": "Medicine Name",
            "strength": "500mg",
            "form": "tablet",
            "confidence": "high/medium/low",
            "visual_reasoning": "Round white tablet with 'PARA' imprint"
        }
    ],
    "pill_characteristics": {
        "shape": "round/oval/capsule/other",
        "color": "color description",
        "imprint": "any visible text/numbers/logos",
        "coating": "film-coated/sugar-coated/none"
    },
    "image_quality": "clear/acceptable/unclear",
    "uncertainty_reason": "Reason if uncertain" or null
}

CONFIDENCE LEVELS:
- high: Clear imprint matches known medicine, distinctive characteristics
- medium: Color and shape match, but imprint unclear
- low: General category match only, needs verification

If this is NOT a pill image (food, random object, etc.), set is_pill_image to false.

IMPORTANT: Only return the JSON object, no other text."""


SAFETY_DISCLAIMER = "⚠️ This is AI-assisted identification and does not replace a pharmacist's judgment. Please verify before proceeding."


class VisionPillIdentifierAgent:
    """
    Vision-based Pill Identification Agent.
    
    Uses GPT Vision to analyze pill images and suggest possible medicine matches.
    This is a READ-ONLY agent that only provides suggestions.
    All decisions must be confirmed by the user through the Pharmacist Agent.
    """
    
    def __init__(self):
        self.model_name = MODEL_NAME
    
    @agent_trace("VisionPillIdentifierAgent", MODEL_NAME)
    async def identify_pill(
        self,
        image_base64: str,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Analyze a pill image and return possible medicine matches.
        
        Args:
            image_base64: Base64 encoded image data (with or without data URI prefix)
            session_id: Session identifier for tracing
            
        Returns:
            Dictionary with identification results and safety disclaimer
        """
        try:
            # Clean base64 data - remove data URI prefix if present
            if "base64," in image_base64:
                image_base64 = image_base64.split("base64,")[1]
            
            # Determine image type (default to jpeg)
            image_type = "image/jpeg"
            
            # Call GPT Vision
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PILL_IDENTIFICATION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_type};base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_completion_tokens=800
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            
            # Handle potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            # Validate response
            if not result.get("is_pill_image", False):
                return {
                    "success": False,
                    "is_pill_image": False,
                    "message": "The uploaded image does not appear to be a pill. Please upload a clear image of the medicine you want to identify.",
                    "disclaimer": SAFETY_DISCLAIMER,
                    "possible_medicines": []
                }
            
            # Check image quality
            if result.get("image_quality") == "unclear":
                return {
                    "success": True,
                    "is_pill_image": True,
                    "message": "The image is unclear. Please upload a clearer, well-lit photo of the pill for better identification.",
                    "disclaimer": SAFETY_DISCLAIMER,
                    "possible_medicines": result.get("possible_medicines", []),
                    "pill_characteristics": result.get("pill_characteristics"),
                    "needs_clearer_image": True
                }
            
            # Build successful response
            possible_medicines = result.get("possible_medicines", [])
            
            if not possible_medicines:
                return {
                    "success": True,
                    "is_pill_image": True,
                    "message": "Could not identify the pill with confidence. Please try manual selection or consult a pharmacist.",
                    "disclaimer": SAFETY_DISCLAIMER,
                    "possible_medicines": [],
                    "pill_characteristics": result.get("pill_characteristics")
                }
            
            # Format response message
            top_match = possible_medicines[0]
            confidence = top_match.get("confidence", "medium")
            name = top_match.get("name", "Unknown")
            strength = top_match.get("strength", "")
            
            confidence_text = {
                "high": "appears to be",
                "medium": "might be",
                "low": "could possibly be"
            }.get(confidence, "might be")
            
            message = f"This pill {confidence_text} **{name}**"
            if strength:
                message += f" **{strength}**"
            message += f". (Confidence: {confidence.capitalize()})"
            
            if len(possible_medicines) > 1:
                alternatives = [f"{m['name']} {m.get('strength', '')}".strip() for m in possible_medicines[1:3]]
                message += f"\n\nOther possibilities: {', '.join(alternatives)}"
            
            print(f"✅ Pill identification complete: {name} ({confidence} confidence)")
            
            return {
                "success": True,
                "is_pill_image": True,
                "message": message,
                "disclaimer": SAFETY_DISCLAIMER,
                "possible_medicines": possible_medicines,
                "pill_characteristics": result.get("pill_characteristics"),
                "top_match": {
                    "name": name,
                    "strength": strength,
                    "confidence": confidence
                }
            }
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse pill identification response: {e}")
            return {
                "success": False,
                "is_pill_image": True,
                "message": "Failed to analyze the image. Please try again with a clearer photo.",
                "disclaimer": SAFETY_DISCLAIMER,
                "possible_medicines": [],
                "error": "parse_error"
            }
            
        except Exception as e:
            print(f"❌ Pill identification error: {e}")
            return {
                "success": False,
                "is_pill_image": False,
                "message": f"Error analyzing image: {str(e)}. Please try again.",
                "disclaimer": SAFETY_DISCLAIMER,
                "possible_medicines": [],
                "error": str(e)
            }
    
    def get_pharmacist_prompt(self, identification_result: Dict[str, Any]) -> str:
        """
        Generate a prompt for the Pharmacist Agent based on identification results.
        This allows the pharmacist to ask the user for confirmation.
        """
        if not identification_result.get("success") or not identification_result.get("possible_medicines"):
            return None
        
        top_match = identification_result.get("top_match", {})
        name = top_match.get("name", "")
        strength = top_match.get("strength", "")
        
        if name:
            return f"Based on the pill image analysis, this appears to be {name} {strength}. Would you like to proceed with ordering this medicine?"
        
        return None
