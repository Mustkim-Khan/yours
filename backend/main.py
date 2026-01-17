"""
Agentic AI Pharmacy - FastAPI Backend
Main entry point for the pharmacy AI system.
"""

import os
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import agents and services
from agents import OrchestratorAgent
from services.data_services import data_service
from models.schemas import OrchestratorRequest, OrchestratorResponse
from utils.tracing import init_langsmith


# ============ REQUEST/RESPONSE MODELS ============

class ChatRequest(BaseModel):
    """Chat request from frontend"""
    message: str
    session_id: str = "default"
    patient_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response to frontend"""
    response: str
    session_id: str
    agent_chain: list[str]
    order_id: Optional[str] = None
    requires_prescription: bool = False
    safety_warnings: list[str] = []
    trace_id: Optional[str] = None
    
    # UI Card data - frontend uses these to display appropriate cards
    ui_card_type: str = "none"  # "none", "order_preview", "order_confirmation", "prescription_upload"
    order_preview: Optional[dict] = None
    order_confirmation: Optional[dict] = None
    prescription_upload: Optional[dict] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str


# ============ APP SETUP ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    print("🚀 Starting Agentic AI Pharmacy Backend...")
    init_langsmith()
    print("✅ LangSmith tracing initialized")
    print("✅ Data service loaded")
    yield
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title="Agentic AI Pharmacy",
    description="AI-powered pharmacy management system with autonomous agents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = OrchestratorAgent()
orchestrator.set_data_service(data_service)


# ============ ENDPOINTS ============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for pharmacy interactions.
    
    Processes user messages through the agent chain:
    Orchestrator → PharmacistAgent → [InventoryAgent|PolicyAgent|FulfillmentAgent|RefillAgent]
    
    When appropriate, returns UI card data for:
    - OrderPreviewCard: When customer wants to order
    - OrderConfirmationCard: When order is confirmed
    - PrescriptionUploadCard: When prescription is required
    
    Full LangSmith traceability for every request.
    """
    try:
        # Create orchestrator request
        orch_request = OrchestratorRequest(
            session_id=request.session_id,
            user_message=request.message,
            patient_id=request.patient_id
        )
        
        # Process through agent chain
        result = await orchestrator.process_request(orch_request)
        
        # Prepare UI card data
        ui_card_type = result.ui_card_type.value if result.ui_card_type else "none"
        order_preview = result.order_preview_data.model_dump() if result.order_preview_data else None
        order_confirmation = result.order_confirmation_data.model_dump() if result.order_confirmation_data else None
        prescription_upload = result.prescription_upload_data.model_dump() if result.prescription_upload_data else None
        
        return ChatResponse(
            response=result.response_text,
            session_id=result.session_id,
            agent_chain=result.agent_chain,
            order_id=result.order_created,
            requires_prescription=result.requires_prescription,
            safety_warnings=result.safety_warnings,
            trace_id=result.trace_id,
            ui_card_type=ui_card_type,
            order_preview=order_preview,
            order_confirmation=order_confirmation,
            prescription_upload=prescription_upload
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/inventory/search")
async def search_inventory(query: str = ""):
    """Search inventory for medicines - returns complete medicine data"""
    if query:
        medicines = data_service.search_medicine(query)
    else:
        medicines = data_service.get_all_medicines()
    
    return {
        "query": query,
        "count": len(medicines),
        "results": [
            {
                "medicine_id": m.medicine_id,
                "id": m.medicine_id,
                "name": m.medicine_name,
                "strength": m.strength,
                "form": m.form,
                "stock_level": m.stock_level,
                "in_stock": m.stock_level > 0,
                "prescription_required": m.prescription_required,
                "category": m.category,
                "discontinued": m.discontinued,
                "controlled_substance": m.controlled_substance
            }
            for m in medicines
        ]
    }


@app.get("/inventory/stats")
async def inventory_stats():
    """Get inventory statistics"""
    return data_service.get_inventory_stats()


@app.get("/patients")
async def get_patients():
    """Get all patients - returns array format for frontend"""
    patients = data_service.get_all_patients()
    # Return as array (frontend expects this format)
    return [
        {
            "patient_id": p.patient_id,
            "patient_name": p.patient_name,
            "patient_email": p.patient_email,
            "patient_phone": p.patient_phone
        }
        for p in patients
    ]


@app.get("/chat/history/{patient_id}")
async def get_chat_history(patient_id: str):
    """
    Get chat history for a patient.
    For now, returns empty array - can be extended to use database.
    """
    # TODO: Implement persistent chat history storage
    return []


@app.post("/voice")
async def process_voice(request: dict):
    """
    Process voice input: STT → Agent → TTS
    
    Input: { audio_base64: string, patient_id: string, session_id: string }
    Output: { transcript: string, chat_response: {...}, audio_response_base64: string }
    """
    import base64
    from services.voice_service import voice_service, VoiceServiceError
    
    try:
        audio_b64 = request.get("audio_base64", "")
        patient_id = request.get("patient_id")
        session_id = request.get("session_id", "default")
        
        # 1. STT: Convert audio to text
        audio_bytes = base64.b64decode(audio_b64)
        transcript, _ = await voice_service.speech_to_text(audio_bytes, "webm")
        
        # 2. Process through agent chain
        orch_request = OrchestratorRequest(
            session_id=session_id,
            user_message=transcript,
            patient_id=patient_id
        )
        result = await orchestrator.process_request(orch_request)
        
        # 3. TTS: Convert response to speech
        try:
            response_audio = await voice_service.text_to_speech(result.response_text, voice="nova")
            audio_response_b64 = base64.b64encode(response_audio).decode("utf-8")
        except VoiceServiceError:
            audio_response_b64 = None
        
        return {
            "transcript": transcript,
            "chat_response": {
                "message": result.response_text,
                "agent_chain": result.agent_chain,
                "trace_url": result.trace_id,
                "extracted_entities": None,
                "safety_result": None,
                "order_preview": result.order_preview_data.model_dump() if result.order_preview_data else None,
                "order": None
            },
            "audio_response_base64": audio_response_b64
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")


@app.get("/patients/{patient_id}/refills")
async def get_patient_refills(patient_id: str, days_ahead: int = 30):
    """Get refill predictions for a patient"""
    refills = data_service.get_medicines_needing_refill(patient_id, datetime.now())
    
    # Get patient info
    patients = data_service.get_all_patients()
    patient = next((p for p in patients if p.patient_id == patient_id), None)
    patient_name = patient.patient_name if patient else f"Patient {patient_id}"
    
    # Filter by days ahead and format for frontend
    formatted_refills = []
    for r in refills:
        if r.get("days_remaining", 0) <= days_ahead:
            days = r.get("days_remaining", 0)
            # Determine action based on days remaining
            if days <= 0:
                action = "BLOCK"
            elif days <= 7:
                action = "AUTO_REFILL"
            else:
                action = "REMIND"
            
            formatted_refills.append({
                "patient_id": patient_id,
                "patient_name": patient_name,
                "medicine": r.get("medicine_name", "Unknown"),
                "medicine_id": f"MED-{r.get('medicine_name', 'UNK')[:3].upper()}",
                "dosage": "1 tablet/day",
                "days_remaining": days,
                "last_purchase_date": r.get("last_order_date", ""),
                "action": action,
                "justification": f"Based on {r.get('quantity', 30)} units ordered on {r.get('last_order_date', 'N/A')[:10]}",
                "urgency": "CRITICAL" if days <= 0 else ("HIGH" if days <= 3 else ("MEDIUM" if days <= 7 else "LOW"))
            })
    
    return {
        "patient_id": patient_id,
        "days_ahead": days_ahead,
        "refills": formatted_refills
    }


@app.get("/patients/{patient_id}/history")
async def get_patient_history(patient_id: str):
    """Get order history for a patient"""
    history = data_service.get_patient_order_history(patient_id)
    
    if history.empty:
        return {"patient_id": patient_id, "orders": []}
    
    orders = history.to_dict("records")
    return {
        "patient_id": patient_id,
        "order_count": len(orders),
        "orders": orders
    }


# ============ RUN SERVER ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
