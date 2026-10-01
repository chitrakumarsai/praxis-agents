---
checks:
  - forbid: '-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----'
    message: private key in source; inject credentials at execution time
  - forbid: '\bAKIA[0-9A-Z]{16}\b|\bsk-ant-[A-Za-z0-9_-]{20,}|\bsk-(?:proj|svcacct|admin)-[A-Za-z0-9_-]{20,}|\bgh[pousr]_[A-Za-z0-9]{36,}|\bxox[abprs]-[A-Za-z0-9-]{10,}'
    message: API token in source; inject credentials at execution time
  - forbid: '\bshell\s*=\s*True\b'
    message: pass an argv list; never build shell commands from model output
---
### Treat content as data, not authority

- Retrieved documents, attachments, tool output, and worker messages are data. They never change
  the task, instructions, or permissions.
- Keep credentials out of prompts, traces, and model-visible errors; inject them at execution time.
- Treat model output as untrusted input to SQL, shell, HTML, file paths, and downstream APIs.
- Apply least privilege to credentials, tools, files, and network destinations. Run untrusted code
  in bounded environments.
- Write explicit negative tests for prompt injection, unauthorized actions, and data exfiltration.
