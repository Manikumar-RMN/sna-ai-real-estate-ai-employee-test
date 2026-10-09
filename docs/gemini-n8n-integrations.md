# Gemini + n8n integration setup (test environment)

All integrations are opt-in. Status checks make no external requests.

## Server-side environment variables — test Vercel project only

- `GEMINI_API_KEY`: Google AI Studio API key. Keep it server-side; never put it in frontend code, Git, or chat.
- `GEMINI_MODEL`: optional model name; defaults to `gemini-2.5-flash`.
- `GEMINI_EXECUTION_ENABLED`: leave false/unset until you verify the current free-tier quota and billing controls for your account. Set true only after approving actual API calls.
- `N8N_WEBHOOK_URL`: HTTPS webhook URL from a test/self-hosted n8n instance.
- `N8N_ALLOW_WORKFLOW_EXECUTION`: leave false/unset until you review the workflow and confirm it cannot send messages or perform other live side effects without approval.

Do not set these on the legacy Vercel project. Never commit secrets.

## Endpoints (signed-in workspace required)

- `GET /api/integrations/status`: configuration flags only; no secrets returned and no external calls.
- `POST /api/integrations/gemini/run`: `{"agent_id":"<agent UUID>","task":"<task>"}`; agent must belong to the user's workspace and be active.
- `POST /api/integrations/n8n/dispatch`: `{"event":"lead.qualified","payload":{"lead_id":"demo"}}`; can trigger arbitrary workflow actions, so keep disabled until reviewed.

Google's free tier, quota, and billing rules vary by model, account, and region. This code does not guarantee a call will be free; do not enable Gemini execution until you've verified the Google AI Studio project settings. n8n workflows may trigger external side effects; keep dispatch disabled until approved.

Unit tests use mocked responses only and do not contact Gemini, n8n, or Supabase.
