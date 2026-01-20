"""
Pydantic Schemas for Structured Agent Outputs
All agents must respond exclusively via these structured schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


# ============ Base Models ============

class Medicine(BaseModel):
    """Medicine data model"""
    medicine_id: str
    medicine_name: str
    strength: str
    form: str
    stock_level: int
    prescription_required: bool
    category: str
    discontinued: bool
    max_quantity_per_order: int = 30
    controlled_substance: bool = False


class Patient(BaseModel):
    """Patient data model"""
    patient_id: str
    patient_name: str
    patient_email: str
    patient_phone: str


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class OrderItem(BaseModel):
    """Single item in an order"""
    medicine_id: str
    medicine_name: str
    dosage: str
    quantity: int
    unit_price: float = 0.0
    total_price: float = 0.0


class Order(BaseModel):
    """Order data model"""
    order_id: str
    patient_id: str
    items: List[OrderItem]
    status: OrderStatus
    created_at: datetime
    total_amount: float = 0.0


# ============ Standardized Agent Output ============

class Decision(str, Enum):
    """All agents must emit one of these decisions"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_INFO = "NEEDS_INFO"
    SCHEDULED = "SCHEDULED"


class AgentOutput(BaseModel):
    """
    STANDARDIZED OUTPUT FORMAT - ALL AGENTS MUST EMIT THIS
    
    Every agent function call must return this exact structure.
    """
    agent: str = Field(..., description="Name of the agent (e.g., PharmacistAgent)")
    decision: Decision = Field(..., description="APPROVED, REJECTED, NEEDS_INFO, or SCHEDULED")
    reason: str = Field(..., description="Short factual justification for the decision")
    evidence: List[str] = Field(default_factory=list, description="Exact data points from context")
    message: Optional[str] = Field(default=None, description="User-facing message (PharmacistAgent only)")
    next_agent: Optional[str] = Field(default=None, description="Next agent name or null")
    # UI Card fields - optional, used by PharmacistAgent for UI card rendering
    ui_card: Optional[str] = Field(default=None, description="Type of UI card: order_preview, order_confirmation, prescription_upload")
    ui_data: Optional[dict] = Field(default=None, description="Data for the UI card component")


# ============ Agent Action Types ============

class AgentAction(str, Enum):
    """Enumeration of all possible agent actions"""
    # Pharmacist Actions
    GREET_CUSTOMER = "greet_customer"
    ANSWER_QUERY = "answer_query"
    DELEGATE_TO_INVENTORY = "delegate_to_inventory"
    DELEGATE_TO_POLICY = "delegate_to_policy"
    DELEGATE_TO_FULFILLMENT = "delegate_to_fulfillment"
    DELEGATE_TO_REFILL = "delegate_to_refill"
    PROVIDE_SAFETY_WARNING = "provide_safety_warning"
    
    # Inventory Actions
    CHECK_STOCK = "check_stock"
    SEARCH_MEDICINE = "search_medicine"
    UPDATE_STOCK = "update_stock"
    
    # Policy Actions
    CHECK_PRESCRIPTION = "check_prescription"
    VALIDATE_INSURANCE = "validate_insurance"
    CHECK_INTERACTIONS = "check_interactions"
    
    # Fulfillment Actions
    CREATE_ORDER = "create_order"
    UPDATE_ORDER = "update_order"
    CANCEL_ORDER = "cancel_order"
    GET_ORDER_STATUS = "get_order_status"
    
    # Refill Actions
    PREDICT_REFILL = "predict_refill"
    CALCULATE_ADHERENCE = "calculate_adherence"
    SEND_REMINDER = "send_reminder"
    
    # UI Card Actions
    SHOW_ORDER_PREVIEW = "show_order_preview"
    SHOW_ORDER_CONFIRMATION = "show_order_confirmation"
    SHOW_PRESCRIPTION_UPLOAD = "show_prescription_upload"


# ============ UI Card Types ============

class UICardType(str, Enum):
    """Types of UI cards that agents can trigger"""
    NONE = "none"
    ORDER_PREVIEW = "order_preview"
    ORDER_CONFIRMATION = "order_confirmation"
    PRESCRIPTION_UPLOAD = "prescription_upload"


class OrderPreviewItem(BaseModel):
    """Item for OrderPreviewCard"""
    medicine_id: str
    medicine_name: str
    strength: str
    quantity: int
    prescription_required: bool = False
    unit_price: float = 0.0
    supply_days: int = 30


class OrderPreviewData(BaseModel):
    """Data structure for OrderPreviewCard component"""
    preview_id: str
    patient_id: str
    patient_name: str
    items: List[OrderPreviewItem]
    total_amount: float
    safety_decision: str = "APPROVE"
    safety_reasons: List[str] = Field(default_factory=list)
    requires_prescription: bool = False


class OrderConfirmationData(BaseModel):
    """Data structure for OrderConfirmationCard component"""
    order_id: str
    preview_id: Optional[str] = None
    patient_id: str
    patient_name: str
    items: List[OrderPreviewItem]
    subtotal: float = 0.0
    tax: float = 0.0
    delivery_fee: float = 0.0
    total_amount: float
    safety_decision: str = "APPROVE"
    safety_reasons: List[str] = Field(default_factory=list)
    requires_prescription: bool = False
    status: str = "CONFIRMED"
    created_at: str
    estimated_delivery: Optional[str] = None


class PrescriptionUploadData(BaseModel):
    """Data structure for PrescriptionUploadCard component"""
    medicine_name: str
    medicine_id: str
    requires_prescription: bool = True
    is_controlled: bool = False
    message: str = "This medication requires a valid prescription"


# ============ Structured Agent Responses ============

class AgentDecision(BaseModel):
    """Base decision model for all agent responses"""
    agent_name: str = Field(..., description="Name of the agent making the decision")
    action: AgentAction = Field(..., description="The action being taken")
    reasoning: str = Field(..., description="Chain of thought explaining the decision")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")


class PharmacistResponse(BaseModel):
    """Structured response from PharmacistAgent"""
    decision: AgentDecision
    message_to_customer: str = Field(..., description="Response message to show the customer")
    extracted_entities: Optional[dict] = Field(default=None, description="Extracted medicine entities")
    delegate_to: Optional[str] = Field(default=None, description="Agent to delegate to if needed")
    delegate_context: Optional[dict] = Field(default=None, description="Context to pass to delegated agent")
    requires_follow_up: bool = Field(default=False, description="Whether agent needs more info")
    safety_flags: List[str] = Field(default_factory=list, description="Any safety concerns flagged")
    
    # UI Card fields
    ui_card_type: Optional[str] = Field(default=None, description="Type of UI card to display: order_preview, order_confirmation, prescription_upload")
    ui_card_data: Optional[dict] = Field(default=None, description="Data for the UI card component")


class InventoryResponse(BaseModel):
    """Structured response from InventoryAgent"""
    decision: AgentDecision
    medicine_found: bool
    medicine_details: Optional[Medicine] = None
    stock_status: Literal["in_stock", "low_stock", "out_of_stock", "not_found"] = "not_found"
    alternatives: List[str] = Field(default_factory=list)
    message: str


class PolicyResponse(BaseModel):
    """Structured response from PolicyAgent"""
    decision: AgentDecision
    prescription_required: bool = False
    is_controlled: bool = False
    age_restriction: Optional[int] = None
    insurance_covers: bool = False
    copay_amount: Optional[float] = None
    interactions_found: List[str] = Field(default_factory=list)
    can_dispense: bool = True
    restrictions: List[str] = Field(default_factory=list)
    message: str


class FulfillmentResponse(BaseModel):
    """Structured response from FulfillmentAgent"""
    decision: AgentDecision
    order_id: Optional[str] = None
    order_status: Optional[OrderStatus] = None
    items: List[OrderItem] = Field(default_factory=list)
    total_amount: float = 0.0
    estimated_time: Optional[str] = None
    delivery_type: Literal["pickup", "delivery"] = "pickup"
    success: bool
    message: str


class RefillResponse(BaseModel):
    """Structured response from RefillPredictionAgent"""
    decision: AgentDecision
    patient_id: str
    upcoming_refills: List[dict] = Field(default_factory=list)
    adherence_score: Optional[float] = None
    reminder_sent: bool = False
    next_refill_date: Optional[str] = None
    message: str


# ============ Orchestrator Communication ============

class OrchestratorRequest(BaseModel):
    """Request structure for orchestrator"""
    session_id: str
    user_message: str
    patient_id: Optional[str] = None
    user_name: Optional[str] = None  # User's display name from Firestore for greeting
    conversation_history: List[dict] = Field(default_factory=list)


class OrchestratorResponse(BaseModel):
    """Structured response from the orchestrator"""
    session_id: str
    response_text: str
    agent_chain: List[str] = Field(..., description="Chain of agents involved: [PharmacistAgent, InventoryAgent]")
    decisions_made: List[AgentDecision] = Field(default_factory=list)
    final_action: AgentAction
    order_created: Optional[str] = None
    requires_prescription: bool = False
    safety_warnings: List[str] = Field(default_factory=list)
    trace_id: Optional[str] = Field(default=None, description="LangSmith trace ID for debugging")
    
    # UI Card fields - when set, frontend should display the corresponding card
    ui_card_type: UICardType = Field(default=UICardType.NONE, description="Type of UI card to display")
    order_preview_data: Optional[OrderPreviewData] = Field(default=None, description="Data for OrderPreviewCard")
    order_confirmation_data: Optional[OrderConfirmationData] = Field(default=None, description="Data for OrderConfirmationCard")
    prescription_upload_data: Optional[PrescriptionUploadData] = Field(default=None, description="Data for PrescriptionUploadCard")


# ============ Tool Definitions for Function Calling ============

class ToolCall(BaseModel):
    """Represents a tool/function call made by an agent"""
    tool_name: str
    arguments: dict
    result: Optional[dict] = None
    execution_time_ms: Optional[int] = None


class AgentSpan(BaseModel):
    """Represents a span in the agent execution trace"""
    span_id: str
    parent_span_id: Optional[str] = None
    agent_name: str
    action: str
    input_data: dict
    output_data: Optional[dict] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    start_time: datetime
    end_time: Optional[datetime] = None
    status: Literal["running", "completed", "error"] = "running"
