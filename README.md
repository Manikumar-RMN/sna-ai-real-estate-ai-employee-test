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

## Next

The next milestone can add a durable storage adapter (for example Postgres/Supabase) only when persistence requirements are defined. No existing SNA AI database is required by the engine.
