import time
import uuid
from fastapi import FastAPI, HTTPException
from .adapters import NatlasAdapter
from .knowledge import KnowledgeBase
from .safety import classify, validate_answer
from .schemas import VoiceQuery, VoiceResponse
from .store import InteractionStore

app = FastAPI(title="AgroVoice — Powered by N-ATLAS", version="0.1.0")
natlas = NatlasAdapter()
knowledge = KnowledgeBase()
store = InteractionStore()

@app.get("/health")
def health():
    return {"status": "ok", "adapter_mode": natlas.mode, "warning": "mock mode is not N-ATLAS evidence" if natlas.mode == "mock" else None}

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
