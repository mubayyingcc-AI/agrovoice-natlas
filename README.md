# AgroVoice — Powered by N-ATLAS

AgroVoice is a voice-to-action agricultural assistance foundation for Nigerian smallholder farmers. It is designed for NAIC 2026 Problem Statement 02: Voice-First Access.

The repository contains a runnable API foundation with:

- an auditable N-ATLAS adapter boundary for ASR and generation;
- reviewed agricultural knowledge cards for maize and tomato;
- deterministic GREEN/AMBER/RED/GREY safety routing;
- structured interaction and VoiceBench evaluation records;
- a human-escalation path;
- a developer-facing `POST /voice/query` gateway;
- conversation history, farm-log, and metrics endpoints;
- a lightweight evaluator page at `/`;
- a mock mode for local development before official N-ATLAS credentials are available.

## Important integration note

The official N-ATLAS ASR endpoint, authentication, payload format, rate limits, and deployment terms must be confirmed with NCAIR/N-ATLAS maintainers. This repository therefore uses a provider-neutral adapter. Set `NATLAS_MODE=http` and configure the endpoint only after official access is granted. Do not claim that mock-mode outputs are N-ATLAS results.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`.

The default mode is `mock`, which makes the complete orchestration testable without external credentials. The mock adapter is deliberately labelled in responses and logs.

The designated WhatsApp pilot number is stored as `WHATSAPP_PILOT_NUMBER` for configuration and documentation only. This repository does not send WhatsApp messages or claim that the number is connected to an approved WhatsApp Business API. A verified WhatsApp provider webhook must be connected before pilot use.

## Test

```bash
pytest -q
```

## API example

```bash
curl -X POST http://localhost:8000/voice/query \
  -H 'Content-Type: application/json' \
  -d '{"language":"hausa","audio_text":"Ganyen tumatir dina suna yin rawaya, me zan yi?","crop":"tomato","consent":true}'
```

For the first real pilot, replace `audio_text` with an audio upload endpoint connected to the official N-ATLAS ASR service. The current JSON endpoint keeps the orchestration and evaluation path testable while that access is being confirmed.

## Intended first pilot

- Problem statement: Voice-First Access
- Languages: Hausa and Yoruba first; Nigerian English and Igbo only after review capacity is confirmed
- Crops: maize and tomato
- Target: 70–90 documented interactions, with unique farmers and total interactions reported separately
- Primary channel: WhatsApp voice notes or another officially approved voice channel

## Safety position

AgroVoice does not diagnose crop disease with certainty, prescribe arbitrary pesticide dosages, guarantee yields, or replace extension officers. Uncertain, chemical, food-safety, or severe-loss queries are escalated.

## Repository status

This is a foundational build. The mock adapter is runnable now. N-ATLAS credentials, a real audio transport, pilot partner, bilingual review, and production deployment must be added before the challenge submission.
