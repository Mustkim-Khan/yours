"""
Prescription Validator Service
==============================
Uses GPT-4 Vision API to validate prescription images.
Checks for doctor's name, date, medicine, and other validity criteria.
"""

import os
import base64
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from openai import AsyncOpenAI


# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


VALIDATION_PROMPT = """You are a medical prescription validator. Analyze this prescription image and extract the following information.

REQUIRED FIELDS (prescription is INVALID without these):
1. Doctor's Name - The prescribing doctor's name
2. Date - The date of the prescription
3. Medicine Name - The prescribed medicine(s)

OPTIONAL FIELDS (add confidence if present):
4. Patient Name
5. Doctor's Signature or Stamp
6. Hospital/Clinic Name
7. Dosage Instructions

VALIDATION RULES:
- If you cannot clearly see a doctor's name, the prescription is INVALID
- If there is no visible date, the prescription is INVALID
- If no medicine names are visible, the prescription is INVALID
- Random images (selfies, landscapes, food, etc.) are INVALID

Respond in this exact JSON format:
{
    "is_valid": true/false,
    "doctor_name": "Dr. Name" or null,
    "date": "YYYY-MM-DD" or null,
    "patient_name": "Name" or null,
    "medicines": ["Medicine 1", "Medicine 2"] or [],
    "hospital_name": "Hospital Name" or null,
    "has_signature": true/false,
    "confidence": 0.0-1.0,
    "rejection_reason": "Reason if invalid" or null
}

IMPORTANT: Only return the JSON object, no other text."""


async def validate_prescription_image(
    image_base64: str,
    expected_medicine: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate a prescription image using GPT-4 Vision.
    
    Args:
        image_base64: Base64 encoded image data (with or without data URI prefix)
        expected_medicine: Optional medicine name to verify is on the prescription
    
    Returns:
        Dictionary with validation results:
        {
            "is_valid": bool,
            "doctor_name": str | None,
            "date": str | None,
            "patient_name": str | None,
            "medicines": list[str],
            "confidence": float,
            "rejection_reason": str | None,
            "is_expired": bool
        }
    """
    try:
        # Clean base64 data - remove data URI prefix if present
        if "base64," in image_base64:
            image_base64 = image_base64.split("base64,")[1]
        
        # Determine image type (default to jpeg)
        image_type = "image/jpeg"
        
        # Call GPT-5.2 Vision
        response = await client.chat.completions.create(
            model="gpt-5.2",  # GPT-5.2 with vision capabilities
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VALIDATION_PROMPT},
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
            max_completion_tokens=500
        )
        
        # Parse response
        response_text = response.choices[0].message.content.strip()
        
        # Extract JSON from response
        import json
        
        # Handle potential markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        
        # Check if prescription is expired (older than 6 months)
        is_expired = False
        if result.get("date"):
            try:
                rx_date = datetime.strptime(result["date"], "%Y-%m-%d")
                six_months_ago = datetime.now() - timedelta(days=180)
                is_expired = rx_date < six_months_ago
                
                if is_expired and result["is_valid"]:
                    result["is_valid"] = False
                    result["rejection_reason"] = f"Prescription expired. Date: {result['date']} is older than 6 months."
            except ValueError:
                pass  # Date parsing failed, don't mark as expired
        
        result["is_expired"] = is_expired
        
        # Check if expected medicine is on the prescription
        if expected_medicine and result["is_valid"]:
            medicines_lower = [m.lower() for m in result.get("medicines", [])]
            expected_lower = expected_medicine.lower()
            
            # Fuzzy match - check if expected medicine is partially in any listed medicine
            medicine_found = any(
                expected_lower in m or m in expected_lower 
                for m in medicines_lower
            )
            
            if not medicine_found and result.get("medicines"):
                # Don't reject, but note the mismatch - doctor might have written brand name
                result["medicine_mismatch"] = True
                result["expected_medicine"] = expected_medicine
        
        print(f"✅ Prescription validation complete: valid={result['is_valid']}")
        return result
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse prescription validation response: {e}")
        return {
            "is_valid": False,
            "doctor_name": None,
            "date": None,
            "patient_name": None,
            "medicines": [],
            "confidence": 0.0,
            "rejection_reason": "Failed to analyze the image. Please upload a clearer image.",
            "is_expired": False
        }
        
    except Exception as e:
        print(f"❌ Prescription validation error: {e}")
        return {
            "is_valid": False,
            "doctor_name": None,
            "date": None,
            "patient_name": None,
            "medicines": [],
            "confidence": 0.0,
            "rejection_reason": f"Validation service error: {str(e)}",
            "is_expired": False
        }
