# SNA AI Agent Engine

Core runtime for SNA AI's reusable, tool-using AI agents.

## Purpose

This repository is dedicated to the **SNA AI Agent Engine**. It is intentionally independent of any business vertical, UI, database, CRM, WhatsApp integration, or model provider.

## V0.5 — Persistent Memory & Resumable Runs

V0.5 defines the persistence boundary without introducing a database:

- `RunStore` persistence contract
- `InMemoryRunStore` implementation for local development and tests
- Agent state persistence across execution steps
- Stable `run_id` for the lifetime of a run
- Resumable step-limited runs
- Persisted messages, tool logs, events, status, and output
- Explicit protection against resuming missing or completed runs

The storage layer is intentionally database-neutral. A future Supabase/Postgres/Redis/etc. implementation can satisfy the same `RunStore` contract without changing the agent runtime.

## Current architecture

- Agent runtime
- Tool registry and schemas
- Safe tool execution
- Agent state and conversation memory
- Permissions and guardrails
- Run logging / observability
- Model-provider adapter boundary
- Run persistence boundary
- Resumable execution

## V0.4

V0.4 introduced the model and memory boundaries needed to keep the engine provider-neutral:

- Model provider adapter boundary
- Conversation memory abstraction
- Conversation context model
- No provider-specific or database-specific implementation

Business-specific AI employees will be built later on top of this engine.

## V0.6 — Agent Configuration & Runtime Context

V0.6 separates agent behavior from execution data:

- `AgentConfig` controls system prompt, step limit, tool timeout, permissions, and sensitive-action confirmation
- `RuntimeContext` carries request-scoped business, user, channel, session, and metadata context
- Runtime context is kept separate from conversation messages at the API boundary
- Agents remain vertical-neutral and provider-neutral
- Existing run persistence and resumability continue to work unchanged

Business-specific employees can later supply their own configuration and runtime context without changing the engine core.

## V0.7 — Agent Lifecycle & Execution Policies

V0.7 adds runtime safety limits and lifecycle controls:

- Configurable maximum total tool calls per run
- Configurable maximum consecutive tool errors
- Explicit `policy_limit` run status when a safety limit stops execution
- Explicit run cancellation for saved runs
- Cancelled runs cannot be resumed accidentally
- Existing step limits remain the primary execution boundary

These policies are engine-level controls and remain independent of any business vertical or external integration.

## V0.8 — Tool & Persistence Hardening

The reusable engine core is now complete for its pre-integration stage:

- Capability metadata on tools (category, retryable)
- Hardened tool registry with duplicate and schema checks
- Configurable retry policy for retryable tools
- Durable local JsonFileRunStore
- Stable public package API through core/__init__.py
- Python package metadata in pyproject.toml
- Automated CI tests across Python 3.10, 3.11, and 3.12
- No external database or provider is required to run the core engine

## Production integration boundary

The engine is ready for the next layer of work, which is intentionally outside the core:

1. Connect a real model provider.
2. Add a durable production database adapter such as Postgres/Supabase.
3. Build vertical-specific tools and knowledge.
4. Add channel adapters such as WhatsApp, web chat, email, or voice.
5. Add authentication, tenant isolation, secrets management, and deployment infrastructure.
6. Add business-specific observability, billing, and admin UI.

Those integrations should be built on top of the engine rather than inside it.

The next milestone can add a durable storage adapter (for example Postgres/Supabase) only when persistence requirements are defined. No existing SNA AI database is required by the engine.
