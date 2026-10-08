# SNA AI Agent Engine

Core runtime for SNA AI's reusable, tool-using AI agents.

## Purpose

This repository is now dedicated to the **SNA AI Agent Engine**. It is intentionally independent of any business vertical, UI, database, CRM, WhatsApp integration, or model provider.

## V0.4

V0.4 introduces the model and memory boundaries needed to keep the engine provider-neutral:

- Model provider adapter boundary
- Conversation memory abstraction
- Conversation context model
- No provider-specific or database-specific implementation yet

## Planned architecture

- Agent runtime
- Tool registry and schemas
- Safe tool execution
- Agent state and memory
- Permissions and guardrails
- Run logging / observability
- Model-provider adapters

Business-specific AI employees will be built later on top of this engine.

## Current status

V0.2 safety hardening is the next engine milestone: schema validation, permissions, and sensitive-action confirmation.
