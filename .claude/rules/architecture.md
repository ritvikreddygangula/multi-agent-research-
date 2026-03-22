# Architecture rules

- Keep orchestration separate from transport.
- Django views should remain thin.
- Business logic belongs in services, graph modules, nodes, and schemas.
- Introduce clear modules rather than expanding one giant file.
- Prefer typed state and structured responses over raw dictionaries where possible.
- Add migration notes in code comments only where they genuinely help future maintainers.
- Every new abstraction must simplify either testing, reasoning, or extensibility.