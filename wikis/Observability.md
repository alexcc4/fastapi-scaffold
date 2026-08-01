# Request Observability

This page documents the application liveness probe, request correlation,
timing, and slow-query logs.

## Check Application Liveness

- URL: `/ping`
- Method: `GET`

### Purpose

A load balancer or operations system checks whether the application process
can handle HTTP requests. This endpoint reports process liveness only. It does
not check MySQL or Redis and must not be treated as a dependency-readiness
probe.

### Authentication and Headers

- Authentication: none.
- `Content-Type`: not applicable.
- Other headers: callers may send `X-Request-ID`; the response includes
  `X-Request-ID` and `Server-Timing`.

### Path and Query Parameters

None.

### Request

**Request body: none.**

### Successful Response

- Status: `200 OK`.
- Meaning: the application process is responding to HTTP requests.

#### Successful Response Example

```json
{
  "status": "ok"
}
```

### Stable Business Errors

None.

### State Side Effects

None. The endpoint does not access MySQL or Redis and does not write an access
log entry. It still returns the request-observability headers.

## Request Correlation

A caller may provide `X-Request-ID`. A valid value is returned unchanged; the
application generates one when the header is missing or invalid. The response
also uses `Server-Timing` to report the time from the start of application
processing until response headers are produced.

The application access log records the request ID, method, path, status code,
and complete response duration. To reduce noise, `/ping` does not write an
access log entry, but it still returns the observability headers.

Logs do not record the query string, request body, cookies, authorization
header, or raw session token.

## Slow Queries

A successful SQL statement that exceeds the configured threshold is written
to a dedicated slow-query log and correlated with the current request ID. By
default, the record contains only the statement type, SQL fingerprint, length,
and duration.

Slow-query logs do not contain SQL text or parameters, preventing literals in
raw SQL from exposing sensitive data.
