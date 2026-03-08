# Agent Guardrails

Security-sensitive backend surfaces are frozen by default.

Do not modify any of the following unless explicitly requested by the user:
- `backend/config.py`
- Backend auth/session flows in `backend/app.py`
- CSRF behavior
- Rate limiting (`flask-limiter` config/decorators)
- CORS policy and API security headers

If a task appears UI-only, treat backend security controls as out of scope.
