# Multi-Agent Research Platform - Claude Project Instructions

This repository is a production-style full-stack application with:
- Django REST backend
- React frontend
- JWT authentication
- Research orchestration pipeline
- Existing specialized agents: planner, researcher, synthesizer

## Core goal for this codebase

Evolve the current sequential multi-agent workflow into a more production-ready research engine with:
1. LangGraph-based orchestration
2. Parallel execution of planner-generated sub-questions
3. Strong typed shared state
4. Retry, timeout, and fallback behavior
5. Per-subquestion traceability
6. Cleaner backend/frontend contracts
7. Better UI for intermediate progress and final citations
8. Proper automated tests

## What “good” looks like here

When making changes, optimize for:
- clear architecture over hacks
- deterministic state transitions
- small composable functions
- explicit schemas and typed payloads
- graceful failure handling
- readable diffs
- production realism suitable for interviews and demos

## Non-negotiable engineering constraints

- Do not rewrite the whole app when an incremental migration is possible.
- Preserve existing authentication and app flow unless a change is necessary.
- Prefer introducing LangGraph behind the service layer first.
- Keep agent prompts modular and versionable.
- Do not hardcode research outputs or rely on brittle string parsing when structured data is feasible.
- Add tests for all new orchestration behavior.
- Avoid hidden magic. Every node and edge in the graph should have a clear reason to exist.
- Keep prompts concise, robust, and role-specific.
- Prefer Pydantic schemas for intermediate state and outputs where feasible.
- Add logging and trace metadata for each research run and sub-question.

## Migration strategy

Default migration sequence:
1. Understand current orchestration flow
2. Introduce a typed LangGraph state model
3. Wrap existing planner/researcher/synthesizer behavior as graph nodes
4. Add sub-question fan-out / fan-in
5. Add retries, timeouts, and partial-failure handling
6. Add citation/trace metadata
7. Update API response shape only as needed
8. Update frontend to render richer progress/results
9. Add unit + integration tests
10. Clean up legacy orchestration code only after parity is confirmed

## Desired backend architecture

Prefer this shape:
- `research/graphs/` for LangGraph graph definitions
- `research/nodes/` for graph node implementations
- `research/schemas/` for request/response/state models
- `research/services/` for orchestration entrypoints used by views
- `research/prompts/` for versioned agent prompts
- `research/utils/` for parsing, retries, normalization, and citations

## Desired graph capabilities

The graph should support:
- topic intake
- planner node
- planner output normalization
- sub-question parallel research branches
- aggregation / dedupe
- synthesis
- quality review or validation
- final response shaping

## Parallel execution expectations

If the planner produces multiple sub-questions:
- execute them independently where possible
- capture per-branch result, status, error, and latency
- continue when some branches fail unless failure threshold is exceeded
- aggregate successful branches into synthesis context
- surface partial results transparently

## Frontend expectations

When backend improvements affect UI:
- keep the interface clean and minimal
- expose progress stages
- show sub-question breakdown where useful
- display citations / evidence snippets if available
- show partial-failure states cleanly without crashing

## Testing expectations

Always add or update:
- node-level tests
- graph flow tests
- serializer/schema tests
- API endpoint tests
- at least one end-to-end happy path

## When uncertain

Prefer the option that:
- improves architecture clarity
- is easier to explain in an interview
- reduces brittle prompt coupling
- keeps future features easy to add