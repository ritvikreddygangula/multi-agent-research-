---
paths:
  - "backend/**/*.py"
---

# Django API rules

- Keep request validation explicit.
- Keep response shapes stable and documented in serializers or schemas.
- Do not bury orchestration logic inside views.
- Use service-layer entrypoints from API views.
- Handle external API failures gracefully and return meaningful error payloads.
- Keep imports organized and module responsibilities clean.