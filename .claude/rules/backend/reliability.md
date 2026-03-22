---
paths:
  - "backend/**/*.py"
---

# Reliability rules

- Wrap model calls with retry and timeout policies where feasible.
- Fail soft on individual branch failures.
- Capture structured error details for each sub-question.
- Log enough metadata to debug a bad research run.
- Never swallow exceptions silently.
- Partial success is better than full failure when safe.