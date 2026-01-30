"""
Realtime Voice Service
======================
GPT-4o-realtime-preview integration with native function calling.
Provides action-based voice interactions for pharmacy operations.

Uses WebSocket to OpenAI Realtime API for bidirectional audio streaming
with tool/function calling for pharmacy actions.
"""

import os
import json
import base64
import asyncio
from typing import Dict, List, Any, Optional, Callable, Awaitable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import websockets
from dotenv import load_dotenv

load_dotenv()

# ============ Configuration ============

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REALTIME_MODEL = "gpt-4o-realtime-preview"
REALTIME_WS_URL = "wss://api.openai.com/v1/realtime"

# ============ Data Classes ============

class UIActionType(Enum):
    """UI actions that can be triggered by voice"""
    SHOW_ORDER_PREVIEW = "show_order_preview"
    UPDATE_CART = "update_cart"
    ORDER_CONFIRMED = "order_confirmed"
    SHOW_REFILL_REMINDER = "show_refill_reminder"
    SHOW_MEDICINE_INFO = "show_medicine_info"


@dataclass
class UIAction:
    """Action to send to frontend for visual update"""
    action_type: UIActionType
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action_type.value,
            "data": self.data
        }


@dataclass
class RealtimeSession:
    """Represents an active realtime voice session"""
    session_id: str
    user_id: str
    conversation_id: Optional[str] = None
    openai_ws: Optional[Any] = None
    is_active: bool = False
    pending_order_preview: Optional[Dict[str, Any]] = None
    tools_invoked: List[str] = field(default_factory=list)
    trace_id: Optional[str] = None


# ============ Tool Definitions ============

REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "search_medicine",
        "description": "Search for medicines in the pharmacy inventory by name. Returns availability and details.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Medicine name to search for"
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "get_conversation_history",
        "description": "Get the recent conversation history with this customer to understand context.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "get_customer_orders",
        "description": "Get the customer's complete order history including past medications.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of orders to retrieve",
                    "default": 10
                }
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "get_cart",
        "description": "Get the customer's current shopping cart contents.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "add_to_cart",
        "description": "Add a medicine to the customer's cart. This will show a cart update on their screen.",
        "parameters": {
            "type": "object",
            "properties": {
                "medicine_id": {
                    "type": "string",
                    "description": "ID of the medicine to add"
                },
                "medicine_name": {
                    "type": "string",
                    "description": "Name of the medicine"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity to add",
                    "default": 30
                }
            },
            "required": ["medicine_id", "medicine_name"]
        }
    },
    {
        "type": "function",
        "name": "create_order_preview",
        "description": "Create an order preview from current cart. This will display an order preview card on the customer's screen for them to review.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "confirm_order",
        "description": "Confirm and place the pending order after customer gives verbal approval. Only call this after the customer explicitly confirms.",
        "parameters": {
            "type": "object",
            "properties": {
                "preview_id": {
                    "type": "string",
                    "description": "The preview ID from create_order_preview"
                }
            },
            "required": ["preview_id"]
        }
    },
    {
        "type": "function",
        "name": "check_prescription_status",
        "description": "Check if the customer has a valid prescription on file for a specific medicine.",
        "parameters": {
            "type": "object",
            "properties": {
                "medicine_name": {
                    "type": "string",
                    "description": "Name of the medicine"
                },
                "dosage": {
                    "type": "string",
                    "description": "Dosage/strength of the medicine"
                }
            },
            "required": ["medicine_name", "dosage"]
        }
    },
    {
        "type": "function",
        "name": "get_refill_reminders",
        "description": "Get list of medicines that will need refill soon based on order history.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

# System instructions for the realtime model
SYSTEM_INSTRUCTIONS = """You are a friendly and helpful pharmacy assistant named Aria. You have full access to the customer's order history, conversation history, and shopping cart.

Your capabilities:
- Search for medicines and check availability
- Add items to the customer's cart (they'll see it update on screen)
- Create order previews (shows a visual card for them to review)
- Confirm orders after they verbally approve
- Check if they have valid prescriptions on file
- Remind them about upcoming refills

Guidelines:
1. Be conversational and warm, like a helpful pharmacist
2. Keep responses brief - this is voice, not text
3. When you add to cart or create previews, mention that they can see it on their screen
4. Always confirm before placing orders - never assume consent
5. If a medicine requires prescription, check if they have one on file first
6. For controlled substances, be extra careful about verification

Example interactions:
- "I need my cholesterol medicine" → Check history, find previous order, offer to add same medicine to cart
- "What's in my cart?" → Get cart contents, summarize verbally
- "Place my order" → Create preview first, ask for confirmation, then confirm
"""


class RealtimeVoiceService:
    """
    Service for managing real-time voice sessions with GPT-4o-realtime-preview.
    Handles WebSocket connections, audio streaming, and function calling.
    """
    
    def __init__(self):
        self.sessions: Dict[str, RealtimeSession] = {}
        self.data_service = None  # Injected
        self.tool_handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}
        self._setup_tool_handlers()
    
    def set_data_service(self, data_service):
        """Inject data service for database operations"""
        self.data_service = data_service
    
    def _setup_tool_handlers(self):
        """Register tool handler functions"""
        self.tool_handlers = {
            "search_medicine": self._handle_search_medicine,
            "get_conversation_history": self._handle_get_conversation_history,
            "get_customer_orders": self._handle_get_customer_orders,
            "get_cart": self._handle_get_cart,
            "add_to_cart": self._handle_add_to_cart,
            "create_order_preview": self._handle_create_order_preview,
            "confirm_order": self._handle_confirm_order,
            "check_prescription_status": self._handle_check_prescription_status,
            "get_refill_reminders": self._handle_get_refill_reminders,
        }
    
    async def create_session(
        self, 
        session_id: str, 
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> RealtimeSession:
        """Create a new realtime voice session"""
        session = RealtimeSession(
            session_id=session_id,
            user_id=user_id,
            conversation_id=conversation_id,
            is_active=True
        )
        self.sessions[session_id] = session
        return session
    
    async def connect_to_openai(self, session: RealtimeSession) -> bool:
        """
        Connect to OpenAI Realtime API via WebSocket.
        Configures session with tools and instructions.
        """
        if not OPENAI_API_KEY:
            print("❌ OPENAI_API_KEY not set")
            return False
        
        try:
            # Connect to OpenAI Realtime API
            url = f"{REALTIME_WS_URL}?model={REALTIME_MODEL}"
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            session.openai_ws = await websockets.connect(url, additional_headers=headers)
            print(f"✅ Connected to OpenAI Realtime API for session {session.session_id}")
            
            # Configure session with tools and instructions
            await self._configure_session(session)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to OpenAI Realtime API: {e}")
            return False
    
    async def _configure_session(self, session: RealtimeSession):
        """Send session configuration to OpenAI"""
        config_event = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": SYSTEM_INSTRUCTIONS,
                "voice": "alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "tools": REALTIME_TOOLS,
                "tool_choice": "auto"
            }
        }
        
        await session.openai_ws.send(json.dumps(config_event))
        print(f"✅ Session configured with {len(REALTIME_TOOLS)} tools")
    
    async def send_audio(self, session_id: str, audio_data: bytes) -> bool:
        """Send audio chunk to OpenAI Realtime API"""
        session = self.sessions.get(session_id)
        if not session or not session.openai_ws:
            return False
        
        try:
            # Debug: Log audio data info
            if len(audio_data) > 0:
                print(f"🎵 Sending audio chunk: {len(audio_data)} bytes, first 4 bytes: {audio_data[:4].hex() if len(audio_data) >= 4 else 'N/A'}")
            
            # Encode audio as base64
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            
            event = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64
            }
            
            await session.openai_ws.send(json.dumps(event))
            return True
            
        except Exception as e:
            print(f"❌ Error sending audio: {e}")
            return False
    
    async def commit_audio(self, session_id: str) -> bool:
        """
        Signal that audio input is complete.
        Note: With server VAD enabled, OpenAI automatically detects speech end
        and starts responding. We only commit the buffer as a hint.
        """
        session = self.sessions.get(session_id)
        if not session or not session.openai_ws:
            return False
        
        try:
            # Commit buffer - but don't request response since server VAD handles that
            event = {"type": "input_audio_buffer.commit"}
            await session.openai_ws.send(json.dumps(event))
            print(f"✅ Audio buffer committed for session {session_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error committing audio: {e}")
            return False
    
    async def receive_events(self, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Async generator that yields events from OpenAI.
        Handles tool calls automatically and yields audio/UI events.
        """
        session = self.sessions.get(session_id)
        if not session or not session.openai_ws:
            return
        
        try:
            async for message in session.openai_ws:
                event = json.loads(message)
                event_type = event.get("type", "")
                
                # Handle different event types
                if event_type == "response.audio.delta":
                    # Audio output chunk
                    yield {
                        "type": "audio",
                        "data": event.get("delta", "")
                    }
                
                elif event_type == "response.audio.done":
                    yield {"type": "audio_done"}
                
                elif event_type == "response.function_call_arguments.done":
                    # Tool call completed - execute it
                    tool_result = await self._execute_tool_call(session, event)
                    
                    # If tool returns UI action, yield it
                    if tool_result.get("ui_action"):
                        yield {
                            "type": "ui_action",
                            "action": tool_result["ui_action"]
                        }
                    
                    # Send tool result back to OpenAI
                    await self._send_tool_result(session, event, tool_result)
                
                elif event_type == "response.done":
                    yield {"type": "response_done"}
                
                elif event_type == "error":
                    yield {
                        "type": "error",
                        "message": event.get("error", {}).get("message", "Unknown error")
                    }
                    
        except websockets.exceptions.ConnectionClosed:
            yield {"type": "disconnected"}
        except Exception as e:
            yield {"type": "error", "message": str(e)}
    
    async def _execute_tool_call(
        self, 
        session: RealtimeSession, 
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool call and return the result"""
        tool_name = event.get("name", "")
        call_id = event.get("call_id", "")
        
        try:
            arguments = json.loads(event.get("arguments", "{}"))
        except json.JSONDecodeError:
            arguments = {}
        
        print(f"🔧 Executing tool: {tool_name} with args: {arguments}")
        session.tools_invoked.append(tool_name)
        
        handler = self.tool_handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            result = await handler(session, **arguments)
            return result
        except Exception as e:
            print(f"❌ Tool {tool_name} failed: {e}")
            return {"error": str(e)}
    
    async def _send_tool_result(
        self, 
        session: RealtimeSession, 
        event: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """Send tool result back to OpenAI"""
        call_id = event.get("call_id", "")
        
        # Remove UI action from result (not for OpenAI)
        result_for_openai = {k: v for k, v in result.items() if k != "ui_action"}
        
        response_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result_for_openai)
            }
        }
        
        await session.openai_ws.send(json.dumps(response_event))
        
        # Request continuation
        await session.openai_ws.send(json.dumps({"type": "response.create"}))
    
    # ============ Tool Handlers ============
    
    async def _handle_search_medicine(
        self, 
        session: RealtimeSession, 
        query: str
    ) -> Dict[str, Any]:
        """Search for medicines"""
        if not self.data_service:
            return {"error": "Data service not available"}
        
        medicines = self.data_service.search_medicine(query)
        
        if not medicines:
            return {"found": False, "message": f"No medicines found for '{query}'"}
        
        results = []
        for med in medicines[:5]:  # Limit to 5
            results.append({
                "medicine_id": med.medicine_id,
                "name": med.medicine_name,
                "strength": med.strength,
                "form": med.form,
                "in_stock": med.stock_level > 0,
                "stock_level": med.stock_level,
                "prescription_required": med.prescription_required
            })
        
        return {
            "found": True,
            "count": len(results),
            "medicines": results
        }
    
    async def _handle_get_conversation_history(
        self, 
        session: RealtimeSession
    ) -> Dict[str, Any]:
        """Get conversation history"""
        if not session.conversation_id:
            return {"messages": [], "note": "No conversation ID provided"}
        
        from services.firestore_service import get_conversation_history
        messages = get_conversation_history(session.conversation_id, limit=10)
        
        return {
            "message_count": len(messages),
            "messages": messages
        }
    
    async def _handle_get_customer_orders(
        self, 
        session: RealtimeSession,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get customer order history"""
        from services.firestore_service import get_orders
        orders = get_orders(session.user_id, limit=limit)
        
        # Simplify for voice context
        simplified = []
        for order in orders:
            simplified.append({
                "order_id": order.get("orderId"),
                "medicine": order.get("medicine"),
                "dosage": order.get("dosage"),
                "quantity": order.get("quantity"),
                "date": order.get("orderedAt"),
                "status": order.get("status")
            })
        
        return {
            "order_count": len(simplified),
            "orders": simplified
        }
    
    async def _handle_get_cart(self, session: RealtimeSession) -> Dict[str, Any]:
        """Get current cart contents"""
        if not self.data_service:
            return {"items": []}
        
        cart = self.data_service.get_active_cart(session.user_id)
        return cart
    
    async def _handle_add_to_cart(
        self,
        session: RealtimeSession,
        medicine_id: str,
        medicine_name: str,
        quantity: int = 30
    ) -> Dict[str, Any]:
        """Add item to cart and trigger UI update"""
        # Get medicine details
        medicine = None
        if self.data_service:
            medicine = self.data_service.get_medicine_by_id(medicine_id)
        
        cart_item = {
            "medicine_id": medicine_id,
            "name": medicine_name,
            "strength": medicine.strength if medicine else "",
            "quantity": quantity,
            "prescription_required": medicine.prescription_required if medicine else False
        }
        
        # Add to Firestore cart
        try:
            from services.firestore_service import get_db
            db = get_db()
            if db:
                cart_ref = db.collection("users").document(session.user_id).collection("cart").document("active")
                cart_doc = cart_ref.get()
                
                if cart_doc.exists:
                    items = cart_doc.to_dict().get("items", [])
                    items.append(cart_item)
                    cart_ref.update({"items": items})
                else:
                    cart_ref.set({"items": [cart_item]})
        except Exception as e:
            print(f"Error updating cart: {e}")
        
        return {
            "success": True,
            "added": cart_item,
            "ui_action": UIAction(
                action_type=UIActionType.UPDATE_CART,
                data={"item": cart_item, "action": "add"}
            ).to_dict()
        }
    
    async def _handle_create_order_preview(
        self, 
        session: RealtimeSession
    ) -> Dict[str, Any]:
        """Create order preview from cart"""
        import uuid
        
        # Get cart
        cart = await self._handle_get_cart(session)
        items = cart.get("items", [])
        
        if not items:
            return {"success": False, "message": "Cart is empty"}
        
        # Build preview
        preview_id = f"PRV-{uuid.uuid4().hex[:8].upper()}"
        
        preview_items = []
        total_amount = 0.0
        requires_prescription = False
        
        for item in items:
            price = 9.99  # Default price, would come from DB
            subtotal = price * item.get("quantity", 1)
            total_amount += subtotal
            
            if item.get("prescription_required"):
                requires_prescription = True
            
            preview_items.append({
                "medicine_id": item.get("medicine_id", ""),
                "medicine_name": item.get("name", ""),
                "strength": item.get("strength", ""),
                "quantity": item.get("quantity", 1),
                "prescription_required": item.get("prescription_required", False),
                "price": price,
                "subtotal": subtotal
            })
        
        preview = {
            "preview_id": preview_id,
            "patient_id": session.user_id,
            "patient_name": "Customer",  # Would get from user profile
            "items": preview_items,
            "total_amount": round(total_amount, 2),
            "safety_decision": "APPROVED",
            "safety_reasons": [],
            "requires_prescription": requires_prescription
        }
        
        # Store for later confirmation
        session.pending_order_preview = preview
        
        return {
            "success": True,
            "preview": preview,
            "ui_action": UIAction(
                action_type=UIActionType.SHOW_ORDER_PREVIEW,
                data=preview
            ).to_dict()
        }
    
    async def _handle_confirm_order(
        self,
        session: RealtimeSession,
        preview_id: str
    ) -> Dict[str, Any]:
        """Confirm and place the order via voice command"""
        import uuid
        from datetime import datetime
        
        if not session.pending_order_preview:
            return {"success": False, "message": "No pending order preview found"}
        
        if session.pending_order_preview.get("preview_id") != preview_id:
            return {"success": False, "message": "Preview ID mismatch"}
        
        preview = session.pending_order_preview
        
        # Generate order ID
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Create order data with voice metadata
        order_data = {
            "order_id": order_id,
            "patient_id": session.user_id,
            "items": preview.get("items", []),
            "total_amount": preview.get("total_amount", 0),
            "requires_prescription": preview.get("requires_prescription", False),
            "status": "CONFIRMED",
            "ordered_at": datetime.now().isoformat(),
            # Voice order metadata
            "order_source": "voice",
            "voice_session_id": session.session_id,
            "conversation_id": session.conversation_id,
        }
        
        # Save to Firestore
        try:
            from services.firestore_service import save_order
            save_order(session.user_id, order_data)
            print(f"✅ Voice order {order_id} saved to Firestore for user {session.user_id}")
            
            # Clear cart
            from services.firestore_service import get_db
            db = get_db()
            if db:
                cart_ref = db.collection("users").document(session.user_id).collection("cart").document("active")
                cart_ref.set({"items": []})
            
            success = True
        except Exception as e:
            print(f"❌ Error saving voice order: {e}")
            success = False
        
        # Clear pending preview
        session.pending_order_preview = None
        
        return {
            "success": success,
            "order_id": order_id,
            "message": f"Order {order_id} confirmed via voice!" if success else "Failed to confirm order",
            "ui_action": UIAction(
                action_type=UIActionType.ORDER_CONFIRMED,
                data={"order_id": order_id, "order": order_data}
            ).to_dict()
        }
    
    async def _handle_check_prescription_status(
        self,
        session: RealtimeSession,
        medicine_name: str,
        dosage: str
    ) -> Dict[str, Any]:
        """Check if user has valid prescription"""
        if not self.data_service:
            return {"has_prescription": False, "checked": False}
        
        has_prescription = self.data_service.has_valid_prescription(
            session.user_id, 
            medicine_name, 
            dosage
        )
        
        return {
            "has_prescription": has_prescription,
            "medicine": medicine_name,
            "dosage": dosage,
            "message": "Valid prescription found on file" if has_prescription else "No valid prescription on file"
        }
    
    async def _handle_get_refill_reminders(
        self, 
        session: RealtimeSession
    ) -> Dict[str, Any]:
        """Get medicines needing refill"""
        if not self.data_service:
            return {"refills": []}
        
        from datetime import datetime
        refills = self.data_service.get_medicines_needing_refill(
            session.user_id,
            datetime.now(),
            days_ahead=14
        )
        
        return {
            "refill_count": len(refills),
            "refills": refills,
            "ui_action": UIAction(
                action_type=UIActionType.SHOW_REFILL_REMINDER,
                data={"refills": refills}
            ).to_dict() if refills else None
        }
    
    async def close_session(self, session_id: str):
        """Close and cleanup a session"""
        session = self.sessions.get(session_id)
        if not session:
            return
        
        session.is_active = False
        
        if session.openai_ws:
            try:
                await session.openai_ws.close()
            except:
                pass
        
        del self.sessions[session_id]
        print(f"✅ Session {session_id} closed")


# Global instance
realtime_voice_service = RealtimeVoiceService()


# ============ Convenience Functions ============

async def create_voice_session(
    session_id: str, 
    user_id: str,
    conversation_id: Optional[str] = None
) -> Optional[RealtimeSession]:
    """Create and connect a new voice session"""
    session = await realtime_voice_service.create_session(
        session_id, user_id, conversation_id
    )
    
    connected = await realtime_voice_service.connect_to_openai(session)
    if not connected:
        await realtime_voice_service.close_session(session_id)
        return None
    
    return session


async def send_voice_audio(session_id: str, audio_data: bytes) -> bool:
    """Send audio to a voice session"""
    return await realtime_voice_service.send_audio(session_id, audio_data)


async def end_voice_input(session_id: str) -> bool:
    """Signal end of voice input and get response"""
    return await realtime_voice_service.commit_audio(session_id)


async def close_voice_session(session_id: str):
    """Close a voice session"""
    await realtime_voice_service.close_session(session_id)
