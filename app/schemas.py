from typing import Any, Literal
from pydantic import BaseModel, Field

Language = Literal["hausa", "yoruba", "igbo", "nigerian_english"]
Risk = Literal["green", "amber", "red", "grey"]
EscalationStatus = Literal["open", "acknowledged", "resolved"]

class VoiceQuery(BaseModel):
    language: Language
    audio_text: str = Field(min_length=1, description="Temporary text stand-in until the official ASR upload adapter is connected")
    domain: Literal["agriculture"] = "agriculture"
    crop: str | None = None
    broad_location: str | None = None
    session_id: str | None = None
    consent: bool = False

class FarmLogRequest(BaseModel):
    language: Language
    activity_text: str = Field(min_length=1)
    crop: str | None = None
    session_id: str | None = None
    consent: bool = False

class EscalationUpdate(BaseModel):
    status: EscalationStatus
    assigned_to: str | None = None
    resolution_note: str | None = None

class VoiceResponse(BaseModel):
    interaction_id: str
    adapter_mode: str
    transcription: str
    language: str
    intent: str
    crop: str | None
    risk_level: Risk
    clarification_question: str | None = None
    answer: str
    source_card_ids: list[str] = []
    requires_human: bool
    feedback_prompt: str
    latency_ms: int
    trace: dict[str, Any]

class FarmLogResponse(BaseModel):
    log_id: str
    crop: str | None
    activity: str
    status: str
    adapter_mode: str

class WhatsAppWebhookResponse(BaseModel):
    status: str
    interaction_id: str | None = None
    message: str | None = None
    whatsapp_configured: bool

class EscalationResponse(BaseModel):
    escalation_id: str
    source_interaction_id: str | None
    status: EscalationStatus
    reason: str
    assigned_to: str | None = None
    resolution_note: str | None = None
