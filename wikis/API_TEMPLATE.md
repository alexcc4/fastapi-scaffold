# Resource Name

This document explains how frontend clients, internal callers, and product
stakeholders use the resource. The Wiki is the human-readable integration
contract and OpenAPI is the exact machine-readable contract. This document
must cover every public OpenAPI operation belonging to the resource.

Copy the complete structure below for each public operation. Give every
operation its own level-two section with a business-action title, for example
`## Create a Resource`. The first two non-empty lines after the title must be
the URL and Method metadata shown below. Use an ASCII colon, inline code, and
an uppercase method. Remove instructions that do not apply and never combine
multiple operations into one operation section.

## Resource Purpose

Explain the business problem solved by this resource and when callers use it.

## Operation Name

- URL: `/path`
- Method: `METHOD`

### Purpose

Explain what the operation does, who may call it, and what callers may rely on
after it succeeds.

### Authentication and Headers

- Authentication: state whether the operation uses a bearer token or none.
- `Content-Type`: state the actual type when there is a request body; otherwise
  write `not applicable`.
- Other headers: list required or returned headers; write `none` when there are
  none.

Sensitive values in operation example blocks use this closed allowlist:

- JSON or form values: `<password>`, `<new-password>`, `<opaque-token>`
- Usernames: values matching `[a-z0-9._-]+\.example`

No other secret field may contain a non-placeholder value in an operation
example block.

### Path and Query Parameters

For every parameter, document its name, type, whether it is required, and its
business meaning. Write `None` when there are no path or query parameters.

### Request

When OpenAPI declares a request body, document each field, its type, whether it
is required, and any constraint that is not obvious from its type. Include a
JSON or form request-body example. When there is no request body, include the
following marker and remove the empty example:

**Request body: none.**

#### Request Body Example

JSON request body:

```json
{
  "username": "user.example",
  "password": "<password>"
}
```

Use the actual encoded-field form for a form request:

```text
username=user.example&password=<password>
```

Add an `#### Integration Example` only for service-to-service operations where
a complete request has genuine integration value. Do not duplicate curl for
ordinary frontend APIs.

### Successful Response

- Status: `2xx`.
- Meaning: explain what the success status guarantees.

Explain complex response fields and fields whose meaning is not obvious from
their names. Do not repeat self-explanatory fields.

#### Successful Response Example

Provide the complete response body synchronized with the current response
model and tests. Never omit fields with an ellipsis. When there is no response
body, include:

**Response body: none.**

```json
{
  "id": 1,
  "username": "user.example"
}
```

### Stable Business Errors

List the business errors that callers must handle consistently. Include the
HTTP status, exact `detail`, and trigger for each error. Generic request
validation errors may link to OpenAPI instead of copying every framework-
generated variant.

| Status | `detail` | Trigger |
| --- | --- | --- |
| `4xx` | `Exact stable detail` | Explain the triggering condition |

### State Side Effects

Explain session invalidation, resource-state changes, and when they take
effect. Write `None` for a read-only operation with no side effects.
