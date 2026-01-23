"""
Agentic AI Pharmacy - FastAPI Backend
Main entry point for the pharmacy AI system.
"""

import os
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import agents and services
from agents import OrchestratorAgent
from services.data_services import data_service
from services.firestore_service import get_orders, get_db  # Import Firestore service
from models.schemas import OrchestratorRequest, OrchestratorResponse
from utils.tracing import init_langsmith
from utils.auth import get_current_user, get_optional_user, init_firebase



# ============ REQUEST/RESPONSE MODELS ============

class ChatRequest(BaseModel):
    """Chat request from frontend"""
    message: str
    session_id: str = "default"
    patient_id: Optional[str] = None
    user_name: Optional[str] = None  # User's display name for personalized greeting
    conversation_id: Optional[str] = None  # Firestore conversation ID for loading history


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
    
    # Initialize Firebase Auth
    if init_firebase():
        print("✅ Firebase Auth initialized")
    else:
        print("⚠️ Firebase Auth not configured - API will be unprotected")
    
    print("✅ Data service loaded")
    
    # Start Background Scheduler
    import asyncio
    asyncio.create_task(run_daily_refill_check())
    print("✅ Daily Refill Scheduler started")
    
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

# Initialize Refill Agent for background jobs
from agents import RefillPredictionAgent
refill_agent = RefillPredictionAgent()
refill_agent.set_data_service(data_service)

async def run_daily_refill_check():
    """
    Background Task: 
    Iterates all users -> Calculates Refills -> Updates Firestore -> Sends Notifications
    Runs in background loop.
    """
    import asyncio
    while True:
        try:
            print("🕒 Starting Daily Refill Check...")
            # 1. Get all users
            users = data_service.get_all_patients()
            
            for user in users:
                # Calculate & Persist
                alerts = await refill_agent.evaluate_patient_refills(user.patient_id)
                
                # Send Notifications
                if alerts:
                    await refill_agent.send_refill_notifications(user.patient_id, alerts)
                    
            print(f"✅ Daily Refill Check Complete. Checked {len(users)} users.")
            
            # Wait 24 hours (or 60s for demo purposes if needed, let's stick to long sleep)
            # For hackathon demo: maybe check every 5 minutes? 
            # Or just run once on startup and then sleep long.
            # Let's do 60 minutes for safety or user can trigger manual.
            await asyncio.sleep(3600) 
            
        except Exception as e:
            print(f"❌ Background Job Error: {e}")
            await asyncio.sleep(60) # Retry after 1 min on error


# ============ ENDPOINTS ============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@app.get("/admin/refills")
async def get_admin_refills():
    """
    Get aggregated refill alerts for Admin Dashboard.
    READ-ONLY: Fetches pre-calculated alerts from user profiles.
    """
    try:
        from services.firestore_service import get_db
        db = get_db()
        if not db:
            return {"alerts": []}
            
        users_ref = db.collection("users")
        docs = users_ref.stream()
        
        aggregated_alerts = []
        
        for doc in docs:
            data = doc.to_dict()
            alerts = data.get("refill_alerts", [])
            
            if alerts:
                # Resolve real name
                patient_name = data.get("name", "Unknown User")
                patient_id = doc.id
                
                for alert in alerts:
                    # Flatten for table
                    flattened = {
                        "patient_name": patient_name,
                        "patient_id": patient_id,
                        "medicine": alert.get("medicine", ""),
                        "days_remaining": alert.get("days_remaining", 0),
                        "status": alert.get("status", "REMIND"),
                        "last_updated": alert.get("last_updated", ""),
                        "refill_date": alert.get("refill_date", ""),
                        # Detailed fields
                        "dosage": alert.get("dosage", "1 tablet/day"),
                        "last_order_date": alert.get("last_order_date", ""),
                        "triggered_agent": alert.get("triggered_agent", "RefillPredictionAgent"),
                        "ai_reason": alert.get("ai_reason", "Predicted based on order history")
                    }
                    aggregated_alerts.append(flattened)
        
        # Sort by urgency (days remaining)
        aggregated_alerts.sort(key=lambda x: x["days_remaining"])
        
        return {"alerts": aggregated_alerts}
        
    except Exception as e:
        print(f"Error fetching admin refills: {e}")
        return {"alerts": [], "error": str(e)}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: Optional[dict] = Depends(get_optional_user)  # Auth: get user if token provided
):
    """
    Main chat endpoint for pharmacy interactions.
    
    Requires Firebase authentication - pass token in Authorization header:
    Authorization: Bearer <firebase_id_token>
    
    Processes user messages through the agent chain:
    Orchestrator → PharmacistAgent → [InventoryAgent|PolicyAgent|FulfillmentAgent|RefillAgent]
    
    When appropriate, returns UI card data for:
    - OrderPreviewCard: When customer wants to order
    - OrderConfirmationCard: When order is confirmed
    - PrescriptionUploadCard: When prescription is required
    
    Full LangSmith traceability for every request.
    """
    # Log authenticated user (optional - for now we allow unauthenticated for gradual rollout)
    if current_user:
        print(f"📝 Authenticated request from: {current_user.get('email', 'unknown')}")

    try:
        # Extract user_id if authenticated
        user_id = current_user.get("uid") if current_user else None

        # Create orchestrator request
        orch_request = OrchestratorRequest(
            session_id=request.session_id,
            user_message=request.message,
            patient_id=request.patient_id,
            user_name=request.user_name,  # Pass user name for personalized greeting
            user_id=user_id,              # Pass Firebase UID for persistence
            conversation_id=request.conversation_id  # Pass Firestore conversation ID
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


# ============ PRESCRIPTION UPLOAD ENDPOINT ============

class PrescriptionUploadRequest(BaseModel):
    """Prescription upload request from frontend"""
    session_id: str
    medicine_id: str
    medicine_name: Optional[str] = None  # For validation matching
    prescription_file: str  # Base64 encoded image data


class PrescriptionUploadResponse(BaseModel):
    """Prescription upload response"""
    success: bool
    message: str
    session_id: str
    agent_chain: list[str]
    order_id: Optional[str] = None
    trace_id: Optional[str] = None
    ui_card_type: str = "order_preview"
    validation_result: Optional[dict] = None  # Prescription validation details
    order_preview: Optional[dict] = None
    order_confirmation: Optional[dict] = None


@app.post("/prescription/upload", response_model=PrescriptionUploadResponse)
async def upload_prescription(request: PrescriptionUploadRequest):
    """
    Handle prescription upload from frontend.
    
    Flow:
    1. Accept prescription image (base64)
    2. Validate using AI vision (PolicyAgent)
    3. If valid: Return ORDER_PREVIEW
    4. If invalid: Return rejection with reason
    """
    from agents.policy_agent import PolicyAgent
    
    try:
        # Step 1: Validate prescription using AI vision
        policy_agent = PolicyAgent()
        validation_output = await policy_agent.validate_prescription(
            image_base64=request.prescription_file,
            medicine_name=request.medicine_name or ""
        )
        
        # Check validation result
        if validation_output.decision.value != "APPROVED":
            # Prescription validation failed
            return PrescriptionUploadResponse(
                success=False,
                message=validation_output.message or "Prescription validation failed",
                session_id=request.session_id,
                agent_chain=["PolicyAgent:prescription_validation_failed"],
                order_id=None,
                trace_id=policy_agent.get_trace_id(),
                ui_card_type="none",
                validation_result={
                    "is_valid": False,
                    "rejection_reason": validation_output.message,
                    "evidence": validation_output.evidence
                },
                order_preview=None,
                order_confirmation=None
            )
        
        # Step 2: Validation passed - proceed with order
        result = await orchestrator.resume_with_prescription(
            session_id=request.session_id,
            medicine_id=request.medicine_id,
            prescription_verified=True
        )
        
        # Prepare order preview data
        order_preview = None
        if result.order_preview_data:
            order_preview = result.order_preview_data.model_dump()
        
        order_confirmation = None
        if result.order_confirmation_data:
            order_confirmation = result.order_confirmation_data.model_dump()
        
        return PrescriptionUploadResponse(
            success=True,
            message=f"{validation_output.message} {result.response_text}",
            session_id=result.session_id,
            agent_chain=["PolicyAgent:prescription_validated"] + result.agent_chain,
            order_id=result.order_created,
            trace_id=result.trace_id,
            ui_card_type=result.ui_card_type.value if result.ui_card_type else "order_preview",
            validation_result={
                "is_valid": True,
                "evidence": validation_output.evidence
            },
            order_preview=order_preview,
            order_confirmation=order_confirmation
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prescription upload failed: {str(e)}")


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
async def process_voice(
    request: dict,
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Process voice input: STT → Agent → TTS
    
    Input: { audio_base64: string, patient_id: string, session_id: string }
    Output: { transcript: string, chat_response: {...}, audio_response_base64: string }
    """
    import base64
    import time
    from services.voice_service import voice_service, VoiceServiceError
    from langsmith.run_helpers import traceable as ls_traceable
    
    @ls_traceable(
        name="VoicePipeline (STT → Agent → TTS)",
        run_type="chain",
        metadata={"type": "voice", "model_stt": "whisper-1", "model_tts": "tts-1"},
        tags=["voice", "stt", "tts"]
    )
    async def _process_voice_traced(audio_b64: str, patient_id: str, session_id: str, user_id: Optional[str], user_name: Optional[str]):
        voice_trace = {
            "stt": {"status": "pending", "model": "whisper-1"},
            "agents": {"status": "pending"},
            "tts": {"status": "pending", "model": "tts-1", "voice": "nova"}
        }
        
        # 1. STT: Convert audio to text
        stt_start = time.time()
        audio_bytes = base64.b64decode(audio_b64)
        transcript, detected_lang = await voice_service.speech_to_text(audio_bytes, "webm")
        stt_duration = int((time.time() - stt_start) * 1000)
        
        voice_trace["stt"] = {
            "status": "success",
            "model": "whisper-1",
            "transcript": transcript[:100] + "..." if len(transcript) > 100 else transcript,
            "detected_language": detected_lang,
            "duration_ms": stt_duration
        }
        
        # 2. Process through agent chain
        agent_start = time.time()
        orch_request = OrchestratorRequest(
            session_id=session_id,
            user_message=transcript,
            patient_id=patient_id,
            user_id=user_id,
            user_name=user_name
        )
        result = await orchestrator.process_request(orch_request)
        agent_duration = int((time.time() - agent_start) * 1000)
        
        voice_trace["agents"] = {
            "status": "success",
            "chain": result.agent_chain,
            "final_action": str(result.final_action),
            "duration_ms": agent_duration
        }
        
        # 3. TTS: Convert response to speech
        tts_start = time.time()
        audio_response_b64 = None
        try:
            response_audio = await voice_service.text_to_speech(result.response_text, voice="nova")
            audio_response_b64 = base64.b64encode(response_audio).decode("utf-8")
            tts_duration = int((time.time() - tts_start) * 1000)
            voice_trace["tts"] = {
                "status": "success",
                "model": "tts-1",
                "voice": "nova",
                "response_length": len(result.response_text),
                "duration_ms": tts_duration
            }
        except VoiceServiceError as e:
            voice_trace["tts"] = {
                "status": "failed",
                "error": str(e)
            }
        
        return {
            "transcript": transcript,
            "chat_response": {
                "message": result.response_text,
                "agent_chain": result.agent_chain,
                "trace_url": result.trace_id,
                "extracted_entities": None,
                "safety_result": None,
                "order_preview": result.order_preview_data.model_dump() if result.order_preview_data else None,
                "order": None,
                "voice_trace": voice_trace  # Include voice trace metadata
            },
            "audio_response_base64": audio_response_b64
        }
    
    try:
        audio_b64 = request.get("audio_base64", "")
        patient_id = request.get("patient_id")
        session_id = request.get("session_id", "default")
        
        # Extract user info
        user_id = current_user.get("uid") if current_user else None
        user_name = current_user.get("name") if current_user else None
        
        return await _process_voice_traced(audio_b64, patient_id, session_id, user_id, user_name)
        
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
            
            # Calculate predicted refill date based on last order + quantity (assuming 1/day)
            from datetime import timedelta
            last_order_str = r.get("last_order_date", "")[:10]
            predicted_date_str = "N/A"
            ai_reason = f"Based on {r.get('quantity', 30)} units ordered on {last_order_str}"
            
            if last_order_str:
                try:
                    last_order_dt = datetime.strptime(last_order_str, "%Y-%m-%d")
                    # Usage assumption: 1 tablet/day (standard mock logic)
                    usage_days = int(r.get('quantity', 30))
                    predicted_dt = last_order_dt + timedelta(days=usage_days)
                    predicted_date_str = predicted_dt.strftime("%Y-%m-%d")
                    
                    # Refine AI reason based on calculation
                    ai_reason = f"Predicted depletion on {predicted_date_str} based on 1 tablet/day usage"
                except Exception:
                    pass

            # Map triggers to specific agents
            triggered_agent = "Predictive Refill Agent"
            if action == "BLOCK":
                triggered_agent = "Safety & Prescription Policy Agent"
                ai_reason = "Refill blocked: Valid prescription required for controlled substance"
            elif action == "AUTO_REFILL":
                triggered_agent = "Predictive Refill Agent"
                ai_reason = f"Auto-refill scheduled (Stock < 7 days). {ai_reason}"
            elif action == "REMIND":
                triggered_agent = "Predictive Refill Agent"
                ai_reason = f"Patient reminder scheduled. {ai_reason}"

            formatted_refills.append({
                "patient_id": patient_id,
                "patient_name": patient_name,
                "medicine": r.get("medicine_name", "Unknown"),
                "medicine_id": f"MED-{r.get('medicine_name', 'UNK')[:3].upper()}",
                "dosage": "1 tablet/day",
                "days_remaining": days,
                "last_purchase_date": r.get("last_order_date", ""),
                "predicted_date": predicted_date_str,
                "action": action,
                "triggered_agent": triggered_agent,
                "ai_reason": ai_reason,
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


# ============ INVENTORY ENDPOINTS (Admin Dashboard) ============

@app.get("/inventory/stats")
async def get_inventory_stats():
    """Get inventory statistics for admin dashboard"""
    stats = data_service.get_inventory_stats()
    return stats


@app.get("/inventory/medicines")
async def get_all_medicines(query: str = ""):
    """Get all medicines in inventory, optionally filtered by search query"""
    medicines = data_service.get_all_medicines()
    
    # Filter by query if provided
    if query:
        query_lower = query.lower()
        medicines = [
            m for m in medicines 
            if query_lower in m.get('name', '').lower() 
            or query_lower in m.get('medicine_id', '').lower()
        ]
    
    return {"results": medicines, "count": len(medicines)}


# ============ ORDER ENDPOINTS (Customer "My Orders") ============

@app.get("/orders")
async def get_user_orders(current_user: Optional[dict] = Depends(get_optional_user)):
    """
    Get all orders for the authenticated user.
    Strictly enforced by userId in token.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    user_id = current_user.get("uid")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
        
    # security: get_orders strictly filters by user_id
    orders = get_orders(user_id, limit=20) 
    return {"orders": orders}


@app.get("/orders/{order_id}")
async def get_order_details(order_id: str, current_user: Optional[dict] = Depends(get_optional_user)):
    """
    Get specific order details.
    Must belong to the authenticated user.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    user_id = current_user.get("uid")
    
    # We don't have a get_order_by_id in firestore_service yet that checks ownership
    # effectively, but we can implement a quick check using the existing get_db
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    doc_ref = db.collection("orders").document(order_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order_data = doc.to_dict()
    
    # STRICT SECURITY CHECK
    if order_data.get("userId") != user_id:
        # Do not throw 403, throw 404 to avoid leaking existence
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Format timestamps
    if "orderedAt" in order_data and hasattr(order_data["orderedAt"], "isoformat"):
        order_data["orderedAt"] = order_data["orderedAt"].isoformat()
        
    return order_data


# ============ RUN SERVER ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
