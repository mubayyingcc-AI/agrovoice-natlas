import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .adapters import NatlasAdapter, NatlasResult
from .knowledge import KnowledgeBase
from .safety import classify, validate_answer
from .schemas import EscalationResponse, EscalationUpdate, FarmLogRequest, FarmLogResponse, VoiceQuery, VoiceResponse, WhatsAppWebhookResponse
from .store import InteractionStore
from .whatsapp import WhatsAppAdapter

app = FastAPI(title="AgroVoice — Powered by N-ATLAS", version="0.4.0")
app.mount("/assets", StaticFiles(directory=Path(__file__).resolve().parent.parent / "assets"), name="assets")
natlas = NatlasAdapter()
whatsapp = WhatsAppAdapter()
knowledge = KnowledgeBase()
store = InteractionStore()

@app.get("/", response_class=HTMLResponse)
def evaluator_page():
    page = Path(__file__).resolve().parent.parent / "web" / "index.html"
    return HTMLResponse(page.read_text(encoding="utf-8"))

@app.get("/natlas", response_class=HTMLResponse)
def natlas_evidence_page():
    mode = natlas.mode
    warning = "MOCK MODE — this is not N-ATLAS evidence" if mode == "mock" else "OFFICIAL MODE — redact credentials before sharing traces"
    return HTMLResponse(f"""<!doctype html><html><head><meta charset='utf-8'><title>N-ATLAS Integration Evidence</title><style>body{{font-family:system-ui;max-width:800px;margin:2rem auto;padding:0 1rem;color:#18221d}}pre{{background:#f3f7f4;padding:1rem;border-radius:8px;overflow:auto}}.warning{{padding:1rem;background:#fff3cd;border-radius:8px}}</style></head><body><h1>AgroVoice N-ATLAS Integration Evidence</h1><div class='warning'><strong>{warning}</strong></div><h2>Critical path</h2><pre>WhatsApp audio → Meta media download → official N-ATLAS ASR → transcript → context/router → official N-ATLAS LLM → safety validator → response</pre><h2>Configured boundary</h2><pre>mode: {mode}
ASR endpoint configured: {bool(natlas.asr_url)}
LLM endpoint configured: {bool(natlas.llm_url)}
API key present: {bool(natlas.api_key)}
WhatsApp adapter configured: {whatsapp.configured}
ASR model: adapter-reported per request
LLM model: adapter-reported per request</pre><p>Credentials are never displayed. Official N-ATLAS endpoint schemas must be confirmed with NCAIR/N-ATLAS maintainers before enabling official mode.</p></body></html>""")

@app.get("/health")
def health():
    return {"status": "ok", "adapter_mode": natlas.mode, "storage_backend": store.backend, "whatsapp_configured": whatsapp.configured, "whatsapp_pilot_number": os.getenv("WHATSAPP_PILOT_NUMBER"), "warning": "mock mode is not N-ATLAS evidence" if natlas.mode == "mock" else None}

def _answer_from_asr(asr: NatlasResult, language: str, crop: str | None, session_id: str | None, started: float) -> VoiceResponse:
    risk, intent, clarification = classify(asr.text, crop)
    cards = knowledge.retrieve(crop, asr.text)
    if clarification:
        answer = clarification
        requires_human = False
        generated = None
    else:
        context = "\n".join(f"[{c['id']}] {c['title']}: {c['content']}" for c in cards)
        prompt = f"Language: {language}\nRisk: {risk}\nQuestion: {asr.text}\nApproved context:\n{context}\nAnswer briefly, safely, and only from the approved context. Do not diagnose or prescribe chemical dosage."
        generated = natlas.generate(language, prompt)
        answer, requires_human = validate_answer(generated.text, risk)
    interaction_id = str(uuid.uuid4())
    latency_ms = int((time.perf_counter() - started) * 1000)
    trace = {"asr_model": asr.model, "asr_mode": asr.mode, "asr_latency_ms": asr.latency_ms, "llm_mode": natlas.mode, "llm_model": generated.model if generated else None, "knowledge_card_count": len(cards)}
    record = {"interaction_id": interaction_id, "language": language, "transcription": asr.text, "intent": intent, "crop": crop, "risk_level": risk, "answer": answer, "source_card_ids": [c["id"] for c in cards], "requires_human": requires_human, "session_id": session_id, "trace": trace}
    store.append(record)
    if requires_human:
        store.create_escalation({"escalation_id": str(uuid.uuid4()), "source_interaction_id": interaction_id, "status": "open", "reason": f"{risk}:{intent}"})
    return VoiceResponse(interaction_id=interaction_id, adapter_mode=natlas.mode, transcription=asr.text, language=language, intent=intent, crop=crop, risk_level=risk, clarification_question=clarification, answer=answer, source_card_ids=[c["id"] for c in cards], requires_human=requires_human, feedback_prompt="Did this answer help you?", latency_ms=latency_ms, trace=trace)

@app.post("/voice/query", response_model=VoiceResponse)
def voice_query(query: VoiceQuery):
    if not query.consent:
        raise HTTPException(status_code=400, detail="Consent is required before storing or evaluating an interaction")
    try:
        return _answer_from_asr(natlas.transcribe(query.language, query.audio_text), query.language, query.crop, query.session_id, time.perf_counter())
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

@app.get("/whatsapp/webhook")
def whatsapp_verify(hub_mode: str | None = Query(None, alias="hub.mode"), hub_challenge: str | None = Query(None, alias="hub.challenge"), hub_verify_token: str | None = Query(None, alias="hub.verify_token")):
    if hub_mode == "subscribe" and hub_verify_token and hub_verify_token == whatsapp.verify_token:
        return int(hub_challenge or "0")
    raise HTTPException(status_code=403, detail="WhatsApp webhook verification failed")

@app.post("/whatsapp/webhook", response_model=WhatsAppWebhookResponse)
async def whatsapp_webhook(request: Request, x_hub_signature_256: str | None = Header(None)):
    raw = await request.body()
    if whatsapp.app_secret and not whatsapp.verify_signature(raw, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid WhatsApp webhook signature")
    if not whatsapp.configured:
        return WhatsAppWebhookResponse(status="accepted_not_configured", message="Configure WhatsApp credentials before processing media", whatsapp_configured=False)
    payload = await request.json()
    messages = whatsapp.parse_messages(payload)
    if not messages:
        return WhatsAppWebhookResponse(status="ignored", message="No supported message found", whatsapp_configured=True)
    message = messages[0]
    if not message.media_id:
        return WhatsAppWebhookResponse(status="ignored", message="Only voice notes are supported by this endpoint", whatsapp_configured=True)
    if natlas.mode != "http":
        return WhatsAppWebhookResponse(status="accepted_mock", message="Voice note received; official N-ATLAS mode is required for audio transcription", whatsapp_configured=True)
    try:
        audio, mime_type, media_id = whatsapp.download_media(message.media_id)
        language = os.getenv("WHATSAPP_DEFAULT_LANGUAGE", "nigerian_english")
        response = _answer_from_asr(natlas.transcribe_audio(language, audio, f"{media_id}.ogg", mime_type), language, None, f"whatsapp:{message.sender}", time.perf_counter())
        whatsapp.send_text(message.sender, response.answer)
        return WhatsAppWebhookResponse(status="processed", interaction_id=response.interaction_id, message="Voice note processed and reply sent", whatsapp_configured=True)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"WhatsApp processing failed: {exc}")

@app.post("/farm-log", response_model=FarmLogResponse)
def farm_log(request: FarmLogRequest):
    if not request.consent:
        raise HTTPException(status_code=400, detail="Consent is required before storing a farm log")
    text = request.activity_text.lower()
    activity = "planting" if "plant" in text or "seed" in text else "harvest" if "harvest" in text else "farm_activity"
    log_id = str(uuid.uuid4())
    store.append_farm_log({"log_id": log_id, "language": request.language, "activity": activity, "activity_text": request.activity_text, "crop": request.crop, "session_id": request.session_id})
    return FarmLogResponse(log_id=log_id, crop=request.crop, activity=activity, status="recorded_with_consent", adapter_mode=natlas.mode)

@app.get("/history")
def history(session_id: str | None = None, limit: int = 50):
    return {"items": store.history(session_id=session_id, limit=min(limit, 200))}

@app.get("/evidence/{interaction_id}")
def evidence(interaction_id: str):
    record = store.get(interaction_id)
    if record is None: raise HTTPException(status_code=404, detail="Interaction evidence not found")
    return record

@app.get("/escalations", response_model=list[EscalationResponse])
def escalations(status: str | None = None, limit: int = 50):
    return store.list_escalations(status=status, limit=min(limit, 200))

@app.patch("/escalations/{escalation_id}", response_model=EscalationResponse)
def update_escalation(escalation_id: str, update: EscalationUpdate):
    result = store.update_escalation(escalation_id, update.model_dump())
    if result is None: raise HTTPException(status_code=404, detail="Escalation not found")
    return result

@app.get("/metrics")
def metrics():
    return store.metrics()
