# SNA AI Agent Engine

Core runtime for SNA AI's reusable, tool-using AI agents.

## Purpose

This repository is dedicated to the SNA AI Agent Engine. It is intentionally independent of any business vertical, UI, database, CRM, WhatsApp integration, or model provider.

## Current architecture

- Agent runtime
- Tool registry and schemas
- Reusable tool bundles
- Safe tool execution
- Agent state and conversation memory
- Permissions and guardrails
- Run logging / observability
- Model-provider adapter boundary
- Run persistence boundary
- Knowledge-provider boundary
- Resumable execution

## V1.6 — Reusable Tool System

V1.6 adds a reusable capability layer on top of the existing tool registry:

- ToolBundle packages related tools as a reusable capability set
- ToolSet defines a lightweight interface for custom tool providers
- ToolRegistry.register_many() registers bundles atomically
- Tool discovery can be filtered by category or permission
- Standard provider-neutral utility tools are available through standard_tool_bundle()
- Standard tools do not call external services and introduce no new runtime dependencies

Business-specific bundles can later provide CRM, calendar, communication, or other integrations without changing the agent runtime.

## Production integration boundary

The engine remains intentionally separate from business-specific AI employees, external integrations, authentication, tenant isolation, secrets management, deployment infrastructure, billing, and admin UI.
