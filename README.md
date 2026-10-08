# SNA AI Agent Engine

Reusable core runtime for SNA AI's tool-using agents.

## V0.1

This first version provides:

- Agent loop with configurable step limit.
- Tool registry with schemas and handlers.
- Tool execution with JSON parsing, unknown-tool handling, exception capture, and timeouts.
- In-memory run logging.
- Provider-neutral model interface.
- Deterministic tests with a fake model; no API key required.

## Example

See examples/basic_agent.py.

## Direction

This core stays independent of any business vertical. Real estate, construction, customer support, operations, and other AI employees should become integrations on top of this engine.
