"""
Medicine Explainer Service
Generates human-pharmacist-like explanations for medicines.
This is a READ-ONLY explainability layer - does not affect any decisions.
"""

import os
from typing import Dict, Optional
from openai import AsyncOpenAI

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Model configuration - using gpt-4o-mini for reliable JSON output
MODEL_NAME = "gpt-4o-mini"  # Fast, cost-effective, supports max_tokens


async def generate_medicine_explanation(
    medicine_name: str,
    strength: str,
    quantity: int,
    frequency: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate a friendly, pharmacist-like explanation for a medicine.
    
    This is an explainability layer ONLY - it does not:
    - Provide medical advice
    - Make diagnostic claims
    - Alter any treatment decisions
    
    Args:
        medicine_name: Name of the medicine
        strength: Dosage strength (e.g., "500mg")
        quantity: Number of units ordered
        frequency: How often to take (optional)
    
    Returns:
        Dictionary with explanation sections
    """
    
    # Build the prompt
    frequency_text = frequency if frequency else "as directed by your doctor"
    
    system_prompt = """You are a friendly, professional pharmacist helping a patient understand their medicine.

STRICT RULES:
- Never diagnose or suggest conditions
- Never give specific medical advice
- Always use hedging language ("typically", "generally", "often")
- Keep explanations brief and reassuring
- Do NOT mention you are an AI

OUTPUT FORMAT (return as JSON):
{
    "purpose": "1-2 sentences on why this medicine is commonly prescribed (no diagnosis claims)",
    "onset": "When effects are typically noticed (use ranges)",
    "common_mistakes": "2-3 bullet points of common mistakes to avoid",
    "precautions": "2-3 bullet points of important precautions",
    "closing": "1 sentence of friendly encouragement"
}"""

    user_prompt = f"""Medicine: {medicine_name} {strength}
Quantity: {quantity} units
Frequency: {frequency_text}

Generate a patient-friendly explanation following the exact JSON format."""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=500,
            temperature=0.3  # Low temperature for consistent, safe outputs
        )
        
        # Parse the JSON response
        import json
        explanation = json.loads(response.choices[0].message.content)
        
        # Add metadata
        explanation["medicine_name"] = medicine_name
        explanation["strength"] = strength
        explanation["generated"] = True
        
        return explanation
        
    except Exception as e:
        print(f"Medicine Explainer Error: {e}")
        # Return fallback explanation
        return {
            "medicine_name": medicine_name,
            "strength": strength,
            "purpose": f"{medicine_name} has been prescribed by your doctor based on your specific needs.",
            "onset": "Effects vary by individual. Follow your doctor's guidance on what to expect.",
            "common_mistakes": "• Don't skip doses\n• Don't stop without consulting your doctor\n• Don't double up if you miss a dose",
            "precautions": "• Take as directed\n• Store properly\n• Keep out of reach of children",
            "closing": "If you have any questions, don't hesitate to ask your pharmacist or doctor.",
            "generated": False
        }


def format_explanation_for_display(explanation: Dict[str, str]) -> str:
    """
    Format the explanation dictionary into a readable string for UI display.
    """
    sections = []
    
    # Purpose section
    if explanation.get("purpose"):
        sections.append(f"💊 **Why this was prescribed**\n{explanation['purpose']}")
    
    # Onset section
    if explanation.get("onset"):
        sections.append(f"⏱️ **When it starts working**\n{explanation['onset']}")
    
    # Common mistakes
    if explanation.get("common_mistakes"):
        sections.append(f"⚠️ **Common mistakes to avoid**\n{explanation['common_mistakes']}")
    
    # Precautions
    if explanation.get("precautions"):
        sections.append(f"🛡️ **Important precautions**\n{explanation['precautions']}")
    
    # Closing
    if explanation.get("closing"):
        sections.append(f"💬 {explanation['closing']}")
    
    return "\n\n".join(sections)
