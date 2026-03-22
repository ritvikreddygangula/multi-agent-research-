# Testing rules

- Every orchestration refactor must come with tests.
- Prefer deterministic tests with mocked LLM responses.
- Test happy path, partial-failure path, and malformed planner-output path.
- Frontend tests should verify loading, rendered results, and degraded states.
- Do not remove existing tests unless they are replaced with stronger ones.