# Gemini + n8n integration setup (test environment)

These integrations are opt-in. No provider request is made by the status endpoint or by default configuration.

## Server-side environment variables

Set only on the **test Vercel project**:

- `GEMINI_API_KEY`: API key from Google AI Studio. Keep it server-side; never put it in frontend code or commit it to Git.
- `GEMINI_MODEL`: optional model name; defaults to `gemini-2.5-flash`.
- `GEMINI_EXECUTION_ENABLED`: leave unset/false until you have checked current Gemini free-tier availability, quota and billing settings. Set to `true` only after approving real API calls.
- `N8N_WEBHOOK_URL`: HTTPS webhook URL from your self-hosted/test n8n instance.
- `N8N_ALLOW_WORKFLOW_EXECUTION`: leave unset/false until you have reviewed the workflow and confirmed it cannot send messages or perform other live side effects without your approval. Set to `true` only when ready.

Do not set these on the legacy Vercel project. Do not put secrets in `public/index.html`, GitHub, client-side configuration, or chat.

## Endpoints

All endpoints below require a signed-in user and a workspace:

- `GET /api/integrations/status`: reports configured/enabled flags only; it never calls a provider and never returns credentials.
- `POST /api/integrations/gemini/run`: JSON body `{"agent_id":"<agent UUID>","task":"<task>" }`. Requires the agent to belong to the current workspace and be active.
- `POST /api/integrations/n8n/dispatch`: JSON body `{"event":"lead.qualified","payload":{"lead_id":"demo"}}`. This can trigger whatever the n8n workflow does, so leave disabled until that workflow is reviewed.

## Cost and side-effect safety

The code does not attempt to determine Google billing status. Free-tier availability and model quotas can change by account, region, and model. Do not enable Gemini execution until the Google AI Studio project has been checked for applicable free-tier quota and billing controls. The n8n webhook may run arbitrary workflow actions; keep it disabled until reviewed. No real outbound messages should be added to the workflow without separate explicit approval.

## Validation

Unit tests use mocked HTTP responses and do not call Gemini, n8n, or Supabase. They validate the disabled-by-default gates, tenant scoping, HTTPS validation, and secret non-disclosure.
