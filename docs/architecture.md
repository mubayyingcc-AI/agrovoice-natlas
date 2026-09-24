# AgroVoice foundational architecture

## Scope

The first build targets NAIC 2026 Problem Statement 02: Voice-First Access. It validates two crops (maize and tomato) and starts with Hausa and Yoruba review capacity. Nigerian English and Igbo are feature flags, not claims of validated parity.

## Runtime flow

```text
voice channel / PWA
  -> channel adapter
  -> N-ATLAS ASR adapter
  -> transcript + language
  -> deterministic risk and intent router
  -> reviewed knowledge-card retrieval
  -> N-ATLAS generation adapter
  -> safety validator
  -> answer or human escalation
  -> interaction store / VoiceBench
```

## N-ATLAS boundary

`app/adapters.py` is the only module that knows how to call the external N-ATLAS service. This keeps the system auditable and prevents a hidden general-purpose model from generating the farmer-facing answer. The current default is `mock` solely so the repository can be executed before official credentials and endpoint formats are confirmed.

When N-ATLAS access is supplied:

1. Implement the exact official ASR request and response shape in `NatlasAdapter.transcribe`.
2. Implement the exact official generation request and response shape in `NatlasAdapter.generate`.
3. Set `NATLAS_MODE=http` and the official URLs and key.
4. Capture model IDs, request IDs, language, latency, and failure status.
5. Save redacted integration traces for the submission evidence.

Do not label mock output as N-ATLAS output.

## Safety tiers

- GREEN: general crop-management information can proceed from approved cards.
- AMBER: ask a clarification question for missing crop, timing, symptom, or poor transcription.
- RED: restrict output and escalate chemicals, dosage, food-safety, severe-loss, or uncertain treatment matters.
- GREY: redirect unrelated or unsupported domains.

## Data model

Each consented interaction should retain only the minimum information needed for operation and validation: pseudonymous interaction ID, language, transcript, crop, intent, risk, source cards, answer, escalation, reviewer score, feedback, and timestamps. Audio retention is optional and requires separate consent and a defined deletion period.

## Future gateway contract

`POST /voice/query` is the first developer-facing gateway. It should later accept an audio file or signed audio URL instead of the temporary `audio_text` field. The response is structured so that a WhatsApp, IVR, PWA, cooperative dashboard, or future public-service application can reuse the same orchestration.

## Evidence to collect

- N-ATLAS ASR and generation traces;
- 70–90 documented interactions, with unique farmers and total interactions reported separately;
- language-by-language ASR usability, comprehension, relevance, task completion, and escalation results;
- failure examples and product changes made because of them;
- safety review and consent records;
- human-extension referrals and outcomes.
