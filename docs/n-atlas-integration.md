# N-ATLAS integration evidence

## Current status

**Foundation / pre-integration.** The repository contains an auditable provider-neutral adapter and a mock mode. Mock outputs are not N-ATLAS evidence. Official N-ATLAS credentials, endpoint schemas, model identifiers, audio formats, and deployment terms must be confirmed before production claims are made.

## Critical path

```text
audio -> official N-ATLAS ASR -> transcript -> intent/context -> approved knowledge -> official N-ATLAS LLM -> safety validator -> response
```

## Adapter boundary

`app/adapters.py` is the only module that calls the external model service. When access is granted, configure:

```text
NATLAS_MODE=http
NATLAS_ASR_URL=<official endpoint>
NATLAS_LLM_URL=<official endpoint>
NATLAS_API_KEY=<secret, never commit>
```

The adapter must capture, where returned by the official service:

- model identifier;
- request or trace identifier;
- language;
- timestamp;
- latency;
- provider error status;
- redacted request and response metadata.

## Evidence routes

- `/natlas` gives the evaluator-facing integration-status page.
- `/health` shows the current adapter mode and whether configuration is present.
- `/evidence/{interaction_id}` returns one stored, consented interaction record.
- `/metrics` returns aggregates calculated from stored records.

## What must be added after access

1. Implement the exact official ASR request and response format.
2. Implement the exact official LLM request and response format.
3. Test Hausa and Yoruba separately.
4. Save redacted traces and screenshots.
5. Add integration tests that call a controlled test endpoint or official sandbox.
6. Keep mock-mode tests so development does not depend on paid or rate-limited access.

Never expose API keys or raw personal data in screenshots, logs, GitHub, or the challenge submission.
