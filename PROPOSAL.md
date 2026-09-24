# AgroVoice — Powered by N-ATLAS
## A multilingual voice-to-action agricultural intelligence service for Nigerian smallholder farmers

**National AI Innovation Challenge 2026**  
**Problem Statement:** PS2 — Voice-First Access  
**Recommended track:** Innovation & Enterprise, subject to the team’s CAC or individual-ID eligibility  
**Initial languages:** Hausa and Yoruba; Nigerian English and Igbo only after validation capacity is confirmed  
**Initial crops:** Maize and tomato  
**Primary channel:** WhatsApp voice notes or the first officially approved voice channel the team can deploy  
**Core AI:** Official N-ATLAS ASR and N-ATLAS multilingual language generation

> **AgroVoice is not another agricultural chatbot. It is a measurable voice-to-action system that turns N-ATLAS into an accessible agricultural interface for Nigerians who prefer speaking to typing.**

## 1. Executive summary

AgroVoice enables Nigerian smallholder farmers to ask practical agricultural questions in their own voice. A farmer sends a voice message in Hausa or Yoruba. The system uses the official N-ATLAS Automatic Speech Recognition service to transcribe the message, identifies the crop and intent, retrieves a reviewed agricultural knowledge card, and uses N-ATLAS to generate a concise response. A deterministic safety layer checks the answer. If the question is ambiguous, high-risk, or outside scope, AgroVoice asks a clarification question or creates a referral for a human extension officer.

The initial build deliberately focuses on two crops, maize and tomato, and two pilot languages. This constraint is central to the project’s credibility. The team will not claim national language parity, crop-disease diagnosis, yield improvement, or replacement of extension workers before those claims are supported by evidence.

AgroVoice will be validated through 70–90 documented real interactions from approximately 30–40 unique farmers recruited through at least two community or extension networks. The report will distinguish total interactions from unique farmers. It will publish language-specific results for ASR usability, comprehension, relevance, task completion, clarification quality, safety escalation, repeat use, and latency. The official challenge requires at least 50 documented real user interactions for PS2, so the target provides a practical buffer [1].

The underlying technical contribution is reusable. AgroVoice includes an N-ATLAS adapter boundary, a documented `POST /voice/query` gateway, a structured interaction store, and a VoiceBench evaluation record. Agriculture is the first validated module. The same architecture can later support other voice-accessible Nigerian services without pretending that those domains are already complete.

## 2. Challenge fit

The official NAIC page describes a build-only challenge. Every valid submission must demonstrate a working technical artefact, genuine N-ATLAS integration, and real-world validation. The required submission package includes the working artefact, N-ATLAS integration evidence, real-world validation, technical documentation, a three-to-five-minute video, a team profile, and registration or endorsement evidence [1].

AgroVoice selects PS2 because the problem statement explicitly concerns Nigerians who do not type. The official page lists agricultural advisory among the use cases, names WhatsApp voice notes, IVR, USSD-linked voice applications, and low-bandwidth mobile applications as delivery channels, and requires the official N-ATLAS ASR service for voice input [1].

The team will not enter PS3 unless it is prepared to produce the required 500-plus-example benchmark against base N-ATLAS. Fine-tuning, LoRA training, and a new sector-specific model are therefore future work rather than dependencies for this PS2 submission.

## 3. The problem

Many digital services assume that a user can read formal text, type an English query, navigate a menu, and name a technical problem precisely. A farmer may own a mobile phone and possess extensive practical knowledge while still finding a text-based agricultural service inconvenient or inaccessible.

The problem is not only a lack of information. It is a lack of information access through a suitable interaction method and language. Research on agricultural extension in Nigeria reports barriers involving limited access to technology and information, inadequate training, poor infrastructure, and language and cultural factors. The same research reports that farmers value market information, demonstrations, training, and practical guidance [2].

AgroVoice addresses the interface and first-response gap. It does not claim to solve every agricultural problem. It helps a farmer move from a spoken concern to a safer, evidence-backed next action or a human referral.

## 4. Product vision

### Product promise

A farmer should not need to learn how to prompt an AI, type in English, know a scientific disease name, or formulate a technically precise query. The farmer should be able to speak naturally.

AgroVoice turns that natural speech into a structured assistance workflow:

> **Listen → Understand → Clarify → Retrieve → Advise → Verify → Act → Record → Follow up**

### Example

A farmer sends a Hausa voice note describing yellowing tomato leaves and visible insects. AgroVoice transcribes the message through N-ATLAS ASR. It identifies tomato, symptom observation, and an AMBER risk level because the symptom is not a confirmed diagnosis. It asks for the crop age and whether the problem is spreading. It retrieves an approved observation card. N-ATLAS generates a short response that recommends inspecting several plants and the underside of leaves, recording the crop stage, and contacting an extension officer before applying chemicals. The system records the interaction and asks whether the response helped.

### Additional use cases

The first version supports three bounded use cases:

1. **Crop guidance:** basic planting, early management, symptom observation, and follow-up for maize and tomato.
2. **Farm voice log:** a farmer can record an activity such as planting, subject to confirmation before a precise date is stored.
3. **Verified price lookup:** this is activated only if a reliable source provides market, product, unit, timestamp, and freshness information. It is not a price-prediction system.

## 5. Foundational architecture

```text
Farmer voice note / PWA audio
              |
              v
       Channel adapter
              |
              v
       Official N-ATLAS ASR
              |
              v
 Transcript + language metadata
              |
              v
   Context and risk router
       |       |       |
     GREEN   AMBER    RED/GREY
       |       |       |
       |   Clarify    Escalate/redirect
       v       |       |
 Reviewed knowledge cards
              |
              v
       Official N-ATLAS LLM
              |
              v
      Safety validator
              |
        +-----+-----+
        |           |
      Answer     Human referral
        |
        v
 Farmer response + feedback
              |
              v
 Interaction store / VoiceBench
```

The current GitHub foundation implements the orchestration in Python and FastAPI. `app/adapters.py` is the only module that calls the external model service. The default mode is `mock` so the repository can be tested before official N-ATLAS credentials and endpoint formats are supplied. Mock output is explicitly labelled as not being N-ATLAS evidence.

When official access is granted, the team will implement the exact ASR and generation payloads in the adapter, set `NATLAS_MODE=http`, capture model and request identifiers, and retain redacted traces for the submission evidence.

## 6. Safety architecture

Agricultural advice can create financial, crop, chemical, and food-safety risks. AgroVoice adopts bounded assistance rather than unrestricted answering.

The system must not diagnose crop disease with certainty from voice alone, prescribe arbitrary pesticide dosages, recommend unsafe chemical combinations, guarantee yields, or present itself as a replacement for an extension officer.

Every interaction receives one of four risk classifications:

| Level | Meaning | System action |
|---|---|---|
| GREEN | General, approved crop information | Retrieve a reviewed card and answer briefly |
| AMBER | Missing context, unclear symptom, poor transcription | Ask a clarification question |
| RED | Chemical application, dosage, food safety, severe loss, or high-risk treatment | Restrict the response and escalate to a qualified person |
| GREY | Unsupported or unrelated domain | Redirect without pretending to answer |

The safety validator is deterministic. It is not a replacement for expert review, but it prevents predictable classes of unsafe output from being delivered as normal advice.

## 7. Agricultural knowledge layer

N-ATLAS is not treated as an agricultural authority. AgroVoice uses a small, versioned knowledge base containing reviewed cards for maize and tomato.

Each card includes:

```json
{
  "id": "tomato-basic-observation-v1",
  "title": "Tomato: basic symptom observation",
  "crop": "tomato",
  "topic": "symptom_observation",
  "source": "reviewed extension material",
  "publisher": "named organisation",
  "date": "review date",
  "region": "Nigeria",
  "review_status": "approved",
  "version": "1.0"
}
```

The final pilot knowledge set should be reviewed by a qualified agriculture adviser and should use material from recognised agricultural institutions, extension resources, research organisations, or verified programmes. Unverified social-media content should not become authoritative context.

The system returns source-card identifiers in the API and stores them in the interaction log. This makes the response auditable without exposing technical metadata unnecessarily to the farmer.

## 8. N-ATLAS integration evidence

The evidence package must make the integration undeniable:

```text
Farmer audio
   ↓
N-ATLAS ASR
   ↓
AgroVoice orchestration
   ↓
N-ATLAS LLM
   ↓
Safety validation
   ↓
Farmer response
```

The repository will provide:

- the exact adapter implementation used in deployment;
- model and service identifiers;
- redacted request and response examples;
- latency and failure logs;
- screenshots of the N-ATLAS trace in the reviewer dashboard;
- a statement of which components are N-ATLAS and which are transport, storage, retrieval, or deterministic safety components.

The farmer-facing response must be generated by N-ATLAS in the real deployment. Another general-purpose foundation model must not secretly generate the substantive answer. The exact official endpoints, credentials, audio format, and permitted deployment mode must be confirmed before submission.

## 9. Reusable N-ATLAS Voice Gateway

AgroVoice includes a small developer-facing interface so it is more than a one-off application. The initial contract is:

```http
POST /voice/query
```

The request includes language, audio or an audio reference, agriculture as the domain, optional crop, optional broad location, session identifier, and consent. The response includes the transcript, language, intent, crop, risk level, clarification question or answer, source-card identifiers, escalation flag, latency, and model trace.

The current repository uses `audio_text` as a temporary local-development field because the official audio upload contract is not yet confirmed. The production adapter will replace this with an audio file or signed audio URL and will use the official N-ATLAS ASR service.

The API is domain-neutral at the boundary but the submission validates only agriculture. Education, finance, civic information, and health are future modules, not current claims.

## 10. VoiceBench evaluation layer

For every consented interaction, AgroVoice records a retention-safe evaluation record containing the interaction identifier, participant pseudonym, language, timestamp, transcript, human-verified transcript where available, crop, intent, risk, source cards, answer, escalation decision, reviewer assessment, farmer feedback, and product change triggered by the interaction.

The team should publish anonymised aggregates and selected consented examples. It should not publish phone numbers, exact home locations, or audio recordings without explicit permission.

### Pilot design

Recruit at least two farmer or extension networks, with one Hausa-speaking group and one Yoruba-speaking group where practical. This is not a nationally representative study. It is a real-world usability and integration pilot across two Nigerian language environments.

Target distribution:

| Interaction category | Target |
|---|---:|
| Crop management | 20 |
| Symptom or problem queries | 20 |
| Planting or harvest questions | 10 |
| Farm logging | 10 |
| Follow-up conversations | 10 |
| Clarification and error cases | 5–10 |
| **Total target** | **70–90** |

### Proposed targets, not achieved results

| Metric | Proposed target |
|---|---:|
| Documented interactions | 70–90 |
| Unique farmers | 30–40 |
| Response-language adherence | ≥90% |
| User comprehension | ≥75% |
| Agricultural relevance | ≥70% |
| Successful task completion | ≥70% |
| Appropriate clarification | ≥75% |
| High-risk escalation correctness | ≥90% |
| Repeat interaction | ≥25% |

The final report must show actual results, including failures, denominators, exclusions, and results separately for Hausa and Yoruba. No dashboard number should be invented before collection.

## 11. Failure analysis

A strong submission will deliberately test and report failure modes:

- noisy voice input that loses a crop term;
- ambiguous symptoms;
- mixed-language speech, tested rather than assumed to work;
- unsupported requests;
- missing crop or crop-stage context;
- harmful chemical requests;
- model or provider timeout;
- human referral failure.

Each failure should have a documented response, such as confirmation, clarification, controlled redirection, retry, or escalation. The goal is engineering maturity, not the appearance of perfection.

## 12. Privacy and consent

The pilot will obtain informed consent in a language participants understand. It will minimise stored personal information, pseudonymise participant IDs, avoid precise location unless necessary and consented, restrict access to pilot records, define a retention period, and provide a withdrawal route where technically feasible.

Audio retention is optional and must be separated from the minimum interaction record. The team must not use recordings for unrelated model training without appropriate consent and governance.

## 13. Team and delivery plan

The recommended four-person team is:

1. **Product and project lead:** submission, product scope, partner coordination, and presentation.
2. **AI/N-ATLAS engineer:** ASR and LLM integration, orchestration, prompts, traces, and evaluation.
3. **Full-stack engineer:** API, channel integration, database, dashboard, deployment, and reliability.
4. **Agriculture and field-validation lead:** knowledge review, farmer recruitment, language testing, consent, safety review, and pilot analysis.

### Sprint plan

| Phase | Work | Exit condition |
|---|---|---|
| Days 1–2 | Confirm N-ATLAS access, team, partner, languages, crops, and scope | Written integration and pilot plan |
| Days 3–5 | Implement ASR/LLM adapter boundary and core pipeline | One end-to-end test with real N-ATLAS access or a clearly labelled mock mode |
| Days 6–8 | Add knowledge cards, risk router, safety validation, logging, and referral queue | Internal safety suite passes |
| Days 9–11 | Add WhatsApp or PWA voice channel and reviewer view | Pilot-ready deployment |
| Days 12–16 | Collect 70–90 interactions and run bilingual review | Evidence pack has valid consent and language breakdown |
| Days 17–18 | Freeze features; analyse metrics; record failure improvements | Reproducible validation report |
| Days 19–20 | Record video, complete documentation, verify eligibility, and submit early | All seven submission components ready |

The exact calendar should be adjusted to the current date, but the ordering is fixed: confirm N-ATLAS access before investing heavily in frontend work, recruit pilot partners early, and freeze scope before the final evidence phase.

## 14. What must not be built for the first submission

The team should not make the following dependencies:

- custom N-ATLAS fine-tuning;
- a new 10,000-question dataset;
- computer-vision disease diagnosis;
- full weather prediction;
- price prediction;
- simultaneous WhatsApp, IVR, USSD, and offline AI;
- custom TTS before the official speech-output capability is confirmed;
- four-language parity without language reviewers;
- ten-crop coverage;
- drone, satellite, or sensor analytics.

These may become a roadmap. They must not prevent the basic working artefact and validation from succeeding.

## 15. Submission evidence package

The submission must contain:

1. **Working artefact:** deployed AgroVoice service, evaluator instructions, and test procedure.
2. **N-ATLAS integration evidence:** repository, adapter code, architecture, traces, screenshots, model identifiers, and limitations.
3. **Real-world validation:** consent approach, interaction records, language breakdown, user feedback, reviewer assessments, failures, and improvements.
4. **Technical documentation:** setup, API, architecture, safety, data handling, deployment, and known limitations.
5. **Three-to-five-minute video:** real or consented farmer interaction, visible N-ATLAS path, clarification, safety escalation, and pilot evidence.
6. **Team profile:** names, roles, affiliations, and relevant capability.
7. **Registration or identity evidence:** CAC certificate for a company applicant or valid IDs for individual applicants, as applicable [1].

## 16. Demonstration script

**0:00–0:20 — The problem:** show a farmer who prefers speaking to typing.

**0:20–1:10 — Voice interaction:** send a Hausa voice note and show the transcript. Do not hide transcription errors.

**1:10–1:50 — Clarification:** show AgroVoice asking for missing crop age or symptom context.

**1:50–2:30 — N-ATLAS evidence:** show ASR, AgroVoice routing, N-ATLAS generation, and safety validation in sequence.

**2:30–3:10 — Action:** show the response, source-card identifier, and farmer feedback prompt. Optionally show a farm-log interaction.

**3:10–3:50 — Escalation:** ask a chemical or severe-loss question and show the referral path.

**3:50–4:30 — Evidence:** show actual interaction count, unique farmers, Hausa/Yoruba split, comprehension, task completion, safety results, latency, and failures.

**4:30–5:00 — Reuse:** show the `POST /voice/query` contract and explain that agriculture is the first validated module of a reusable N-ATLAS voice architecture.

## 17. Sustainability and impact

AgroVoice should extend the reach of extension workers rather than replace them. Potential operating partners include cooperatives, extension services, agricultural organisations, agribusinesses, and institutional programmes. The farmer-facing service can be subsidised during the pilot; organisations can later pay for a referral dashboard, knowledge-card management, analytics, or integration into their existing programmes.

Defensible first-stage impact claims are accessibility, language inclusion, usability, comprehension, relevance, task completion, safe escalation, and repeat engagement. The team should not claim increased yields or national food-security effects without a longer controlled evaluation.

## 18. Final positioning

> **AgroVoice is a multilingual voice-to-action system that turns N-ATLAS into an accessible agricultural interface for Nigerians who prefer speaking to typing. A farmer speaks naturally. N-ATLAS listens. AgroVoice identifies what information is missing. Reviewed agricultural knowledge is retrieved. N-ATLAS generates the response. A safety layer checks it. The farmer receives a practical next step. The interaction is recorded, evaluated, and escalated to a human where necessary.**

The submission should revolve around three proofs:

1. **It works:** a real farmer speaks and receives a useful response.
2. **N-ATLAS powers it:** the official ASR and N-ATLAS language generation are visible in the critical path.
3. **Real people use it:** 70–90 documented interactions, language-specific results, real failures, and product improvements.

## References

[1]: https://ncair.nitda.gov.ng/naic/ "National AI Innovation Challenge (NAIC) 2026 — official challenge page"

[2]: https://www.frontiersin.org/journals/sustainable-food-systems/articles/10.3389/fsufs.2026.1829015/full "Enhancing access and mitigating challenges of agricultural extension services among small-scale farmers in Nigeria — Frontiers in Sustainable Food Systems"

[3]: https://huggingface.co/NCAIR1/N-ATLaS "N-ATLaS-LLM — official NCAIR1 model card on Hugging Face"

[4]: https://fmcide.gov.ng/nigeria-launches-landmark-ai-model-powered-by-awarri-to-advance-languages-and-ai-at-scale/ "Nigeria Launches Landmark AI Model Powered by Awarri to Advance Languages and AI at Scale — Federal Ministry of Communications, Innovation & Digital Economy"

**Prepared by:** Manus AI  
**Status:** Comprehensive strategic proposal and foundational build specification. Operational N-ATLAS endpoint, credentials, pilot partners, and observed metrics remain to be confirmed before submission.
