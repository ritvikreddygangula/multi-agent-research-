---
paths:
  - "backend/**/*.py"
---

# LangGraph implementation rules

- Prefer a single shared state object for graph execution.
- Planner output should be normalized into a typed list of sub-questions before fan-out.
- Fan-out branches should be independent and composable.
- Fan-in aggregation should deduplicate repeated evidence and repeated themes.
- Preserve per-branch metadata: status, runtime, errors, tokens if available, and evidence.
- Add a validation or review step if it materially improves final quality.
- Keep the graph easy to diagram and explain.
- Minimize hidden side effects inside nodes.