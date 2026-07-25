# Resource Name

This document explains how frontend and product consumers use the resource.
The live `/docs` and `/openapi.json` endpoints are authoritative for fields,
types, required values, and status codes.

## Purpose

Explain the business problem this resource solves and the situations in which
the page uses it.

## Endpoints

- `METHOD /api/resource`: Describe the operation's purpose in one sentence.
- For core frontend integration endpoints, include the content type, headers,
  complete request, successful response, and error statuses. For ordinary
  endpoints, retain only the information needed to understand the business
  behavior.

## Business Rules

- Document only rules that are not evident from field names and types.
- Explain important state changes, resource relationships, and authorization
  prerequisites.

## Frontend Considerations

- Explain loading, empty, unavailable, and special interaction states.
- State how the frontend determines success, failure, and state changes.

## Error Handling

- List business errors that require dedicated frontend handling and describe
  the corresponding user message.
- Refer directly to `/docs` for generic validation errors.

## Example (Optional)

Core integration endpoints may maintain representative JSON synchronized with
the response model and tests. For other endpoints, include one minimal example
only when it clarifies business semantics. Never include fixed test
credentials, real tokens, or secrets, and do not create separate example
files.
