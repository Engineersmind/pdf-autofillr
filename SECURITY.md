# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` branch | Yes |
| Older branches | No |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Email **team@engineersmind.com** with:
- A description of the vulnerability
- Steps to reproduce
- Potential impact

You will receive a response within 5 business days. We will work with you to understand and resolve the issue before any public disclosure.

## Scope

In scope:
- `modules/mapper/` — the core PDF processing engine
- `modules/mapper/sdk/` — the Python SDK
- API server (`api_server.py`) — injection, auth bypass, path traversal

Out of scope:
- Issues in third-party dependencies (report directly to the dependency maintainer)
- LLM prompt injection (inherent to LLM usage; mitigate via input validation on your end)
