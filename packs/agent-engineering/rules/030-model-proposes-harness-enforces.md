### The model proposes; the harness enforces

- Enforce permissions, budgets, deadlines, cancellation, and stopping in code, outside the model.
  Prompt wording is not a sandbox.
- A model-produced field such as `approved: true` is never authorization.
- Validate tool arguments and authorization in trusted code before every execution.
- A permission denial or policy block stops that action. Never route around it with another tool.
