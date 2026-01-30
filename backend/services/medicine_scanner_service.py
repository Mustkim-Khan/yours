"""
Medicine Scanner Service
Uses GPT-5.2 Vision to analyze medicine images and extract details.
"""

import base64
import os
from datetime import datetime, timedelta
from typing import Optional
from openai import OpenAI
from pydantic import BaseModel


class MedicineScanResult(BaseModel):
    """Result of medicine image analysis"""
    success: bool
    is_medicine: bool = True  # Whether the image is actually a medicine
    name: Optional[str] = None
    strength: Optional[str] = None
    form: Optional[str] = None  # tablet, capsule, syrup, etc.
    expiry_date: Optional[str] = None  # ISO format YYYY-MM-DD
    expiry_status: Optional[str] = None  # safe, expiring, expired
    manufacturer: Optional[str] = None
    ai_confidence: float = 0.0
    error_message: Optional[str] = None
    image_base64: Optional[str] = None  # Store the uploaded image


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def calculate_expiry_status(expiry_date_str: Optional[str]) -> str:
    """Calculate expiry status based on date"""
    if not expiry_date_str:
        return "safe"
    
    try:
        expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
        today = datetime.now()
        days_until_expiry = (expiry_date - today).days
        
        if days_until_expiry < 0:
            return "expired"
        elif days_until_expiry <= 60:  # Within 2 months
            return "expiring"
        else:
            return "safe"
    except ValueError:
        return "safe"


async def scan_medicine_image(image_base64: str) -> MedicineScanResult:
    """
    Analyze a medicine image using GPT-5.2 Vision.
    
    Args:
        image_base64: Base64 encoded image data
        
    Returns:
        MedicineScanResult with extracted medicine details
    """
    
    prompt = """Analyze this image carefully. First, determine if this is an image of medicine packaging, a medicine bottle, pills, or any pharmaceutical product.

If this is NOT a medicine image (e.g., random photo, food, person, landscape, document, etc.), respond with:
{
    "is_medicine": false,
    "confidence": 0.0
}

If this IS a medicine image, extract the following information:
1. **Medicine Name**: The brand name or generic name
2. **Strength/Dosage**: The strength (e.g., 500mg, 10mg, 5ml)
3. **Form**: Tablet, Capsule, Syrup, Cream, Injection, Softgel, etc.
4. **Expiry Date**: In YYYY-MM-DD format if visible
5. **Manufacturer**: The company name if visible

Respond with this JSON format:
{
    "is_medicine": true,
    "name": "Medicine Name",
    "strength": "500mg",
    "form": "Tablet",
    "expiry_date": "2027-06-15",
    "manufacturer": "Company Name",
    "confidence": 0.95
}

Set fields to null if not visible. Confidence (0.0-1.0) should reflect label clarity."""

    try:
        response = client.chat.completions.create(
            model="gpt-5.2",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_completion_tokens=500,
            temperature=0.1  # Low temperature for consistent extraction
        )
        
        # Parse the response
        content = response.choices[0].message.content
        
        # Extract JSON from response
        import json
        import re
        
        # Try to find JSON in the response
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            
            # Check if it's actually a medicine
            if not data.get("is_medicine", True):
                return MedicineScanResult(
                    success=False,
                    is_medicine=False,
                    error_message="This doesn't appear to be a medicine. Please upload a clear photo of medicine packaging, bottle, or pill strip.",
                    ai_confidence=0.0,
                    image_base64=image_base64
                )
            
            expiry_date = data.get("expiry_date")
            expiry_status = calculate_expiry_status(expiry_date)
            
            return MedicineScanResult(
                success=True,
                is_medicine=True,
                name=data.get("name"),
                strength=data.get("strength"),
                form=data.get("form"),
                expiry_date=expiry_date,
                expiry_status=expiry_status,
                manufacturer=data.get("manufacturer"),
                ai_confidence=data.get("confidence", 0.8),
                image_base64=image_base64  # Include the image
            )
        else:
            return MedicineScanResult(
                success=False,
                is_medicine=False,
                error_message="Could not analyze the image. Please upload a clearer photo of the medicine label.",
                ai_confidence=0.0,
                image_base64=image_base64
            )
            
    except Exception as e:
        print(f"❌ Medicine scan error: {e}")
        return MedicineScanResult(
            success=False,
            is_medicine=False,
            error_message=f"Analysis failed. Please try again with a clearer image.",
            ai_confidence=0.0,
            image_base64=image_base64
        )


async def scan_medicine_from_file(file_path: str) -> MedicineScanResult:
    """Convenience function to scan from a file path"""
    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    return await scan_medicine_image(image_data)
