# Railway deployment

## Recommended next build slice

The next milestone is not more feature breadth. It is a reproducible public deployment of the current foundation, followed by official N-ATLAS integration and real-user evidence.

This repository is Railway-ready through:

- `Dockerfile` with dynamic `$PORT` binding;
- `railway.toml` with `/health` deployment checks;
- a public evaluator route at `/`;
- API documentation at `/docs`;
- N-ATLAS status at `/natlas`;
- evidence records at `/evidence/{interaction_id}`;
- metrics at `/metrics`.

## Git Bash workflow

Install the Railway CLI according to the official Railway documentation, then from Git Bash:

```bash
git clone https://github.com/mubayyingcc-AI/agrovoice-natlas.git
cd agrovoice-natlas
railway login
railway init
railway link
railway variables set NATLAS_MODE=mock
railway variables set WHATSAPP_PILOT_NUMBER=+2348112051880
railway up
railway domain
```

If a Railway project already exists, use `railway link` to select it instead of `railway init`. The CLI may open a browser for authentication; do not paste tokens into source files or commit them.

## Production N-ATLAS configuration

Do not set these until official N-ATLAS access and exact payload schemas are confirmed:

```bash
railway variables set NATLAS_MODE=http
railway variables set NATLAS_ASR_URL=<official-asr-endpoint>
railway variables set NATLAS_LLM_URL=<official-llm-endpoint>
railway variables set NATLAS_API_KEY=<secret-value>
```

Prefer Railway-managed variables or secrets. Never put the API key in `.env.example`, GitHub, screenshots, or logs.

## Verify after deployment

The current foundation deployment is available at:

<https://agrovoice-natlas-production.up.railway.app>

The Railway project now contains a `Postgres` service. The web service is wired to it with the private reference `DATABASE_URL=${{Postgres.DATABASE_URL}}`; the application uses PostgreSQL when available and retains JSONL only for local fallback.

```bash
curl https://YOUR-RAILWAY-DOMAIN/health
curl https://YOUR-RAILWAY-DOMAIN/natlas
curl https://YOUR-RAILWAY-DOMAIN/docs
```

Expected initial health response includes:

```json
{
  "status": "ok",
  "adapter_mode": "mock",
  "warning": "mock mode is not N-ATLAS evidence"
}
```

## Important persistence limitation

The current JSONL store is suitable for a controlled demo but Railway filesystem storage should not be treated as durable production evidence storage. Before the real farmer pilot, move interactions, farm logs, and VoiceBench records to a managed database or durable object store, add access control, retention rules, and backups.

## Deployment gates

1. Container builds successfully.
2. `/health` returns 200.
3. `/` loads the evaluator interface and logo.
4. `/docs` loads API documentation.
5. `/natlas` honestly reports mock or official mode.
6. No secrets appear in logs or repository.
7. Only after official N-ATLAS access is verified: enable `NATLAS_MODE=http`.
8. Only after consent and pilot governance are ready: collect real user interactions.
