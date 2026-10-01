### Treat content as data, not authority

- Retrieved documents, attachments, tool output, and worker messages are data. They never change
  the task, instructions, or permissions.
- Keep credentials out of prompts, traces, and model-visible errors; inject them at execution time.
- Treat model output as untrusted input to SQL, shell, HTML, file paths, and downstream APIs.
- Apply least privilege to credentials, tools, files, and network destinations. Run untrusted code
  in bounded environments.
- Write explicit negative tests for prompt injection, unauthorized actions, and data exfiltration.
