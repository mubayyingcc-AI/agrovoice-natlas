import os
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from .adapters import NatlasAdapter
from .knowledge import KnowledgeBase
from .safety import classify, validate_answer
from .schemas import FarmLogRequest, FarmLogResponse, VoiceQuery, VoiceResponse
from .store import InteractionStore

app = FastAPI(title="AgroVoice — Powered by N-ATLAS", version="0.2.0")
natlas = NatlasAdapter()
knowledge = KnowledgeBase()
store = InteractionStore()

@app.get("/", response_class=HTMLResponse)
def evaluator_page():
    page = Path(__file__).resolve().parent.parent / "web" / "index.html"
    return HTMLResponse(page.read_text(encoding="utf-8"))

@app.get("/health")
def health():
    return {"status": "ok", "adapter_mode": natlas.mode, "whatsapp_pilot_number": os.getenv("WHATSAPP_PILOT_NUMBER"), "warning": "mock mode is not N-ATLAS evidence" if natlas.mode == "mock" else None}

@app.post("/voice/query", response_model=VoiceResponse)
def voice_query(query: VoiceQuery):
    started = time.perf_counter()
    if not query.consent:
        raise HTTPException(status_code=400, detail="Consent is required before storing or evaluating an interaction")
    try:
        asr = natlas.transcribe(query.language, query.audio_text)
        risk, intent, clarification = classify(asr.text, query.crop)
        cards = knowledge.retrieve(query.crop, asr.text)
        if clarification:
            answer = clarification
            requires_human = False
        else:
            context = "\n".join(f"[{c['id']}] {c['title']}: {c['content']}" for c in cards)
            prompt = f"Language: {query.language}\nRisk: {risk}\nQuestion: {asr.text}\nApproved context:\n{context}\nAnswer briefly, safely, and only from the approved context. Do not diagnose or prescribe chemical dosage."
            generated = natlas.generate(query.language, prompt)
            answer, requires_human = validate_answer(generated.text, risk)
        interaction_id = str(uuid.uuid4())
        latency_ms = int((time.perf_counter() - started) * 1000)
        trace = {"asr_model": asr.model, "asr_mode": asr.mode, "asr_latency_ms": asr.latency_ms, "llm_mode": natlas.mode, "knowledge_card_count": len(cards)}
        record = {"interaction_id": interaction_id, "language": query.language, "transcription": asr.text, "intent": intent, "crop": query.crop, "risk_level": risk, "answer": answer, "source_card_ids": [c["id"] for c in cards], "requires_human": requires_human, "session_id": query.session_id}
        store.append(record)
        return VoiceResponse(interaction_id=interaction_id, adapter_mode=natlas.mode, transcription=asr.text, language=query.language, intent=intent, crop=query.crop, risk_level=risk, clarification_question=clarification, answer=answer, source_card_ids=[c["id"] for c in cards], requires_human=requires_human, feedback_prompt="Did this answer help you?", latency_ms=latency_ms, trace=trace)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

@app.post("/farm-log", response_model=FarmLogResponse)
def farm_log(request: FarmLogRequest):
    if not request.consent:
        raise HTTPException(status_code=400, detail="Consent is required before storing a farm log")
    text = request.activity_text.lower()
    if "plant" in text or "seed" in text:
        activity = "planting"
    elif "harvest" in text:
        activity = "harvest"
    else:
        activity = "farm_activity"
    log_id = str(uuid.uuid4())
    store.append_farm_log({"log_id": log_id, "language": request.language, "activity": activity, "activity_text": request.activity_text, "crop": request.crop, "session_id": request.session_id})
    return FarmLogResponse(log_id=log_id, crop=request.crop, activity=activity, status="recorded_with_consent", adapter_mode=natlas.mode)

@app.get("/history")
def history(session_id: str | None = None, limit: int = 50):
    return {"items": store.history(session_id=session_id, limit=min(limit, 200))}

@app.get("/metrics")
def metrics():
    return store.metrics()
