# Wiki

This directory documents the business semantics that callers need to
understand. The Wiki is the human-readable integration contract and OpenAPI is
the exact machine-readable contract. Every public operation has its own
business-action section in the corresponding resource Wiki, including its
request, successful response, stable errors, and state side effects.

The current Wiki covers `POST /api/auth/token`, `GET /api/auth/me`,
`POST /api/auth/logout`, and `GET /ping`.

## APIs and Foundation

- [Internal Account Authentication](Auth.md): sign-in, current user, session
  invalidation, and account maintenance.
- [Request Observability](Observability.md): application liveness probe,
  request ID, timing, and slow-query logs.
- [API Documentation Template](API_TEMPLATE.md): use when documenting a new
  public operation.
