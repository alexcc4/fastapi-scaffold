# Request Observability

## Request Correlation

Callers may provide `X-Request-ID`. A valid value is returned unchanged; the
application generates one when the value is missing or invalid. The response
also uses `Server-Timing` to report the time from the start of application
processing until the response headers are produced.

The application access log records the request ID, method, path, status code,
and complete response duration. To reduce noise, `/ping` does not write an
access log entry but still returns the observability headers.

Logs never record the query string, request body, cookies, authorization
header, or raw session token.

## Slow Queries

Successful SQL statements that exceed the configured threshold are written to
a dedicated slow-query log and correlated with the current request ID. By
default, the log shows only the statement type, SQL fingerprint, length, and
duration.

The slow-query log does not record SQL text or parameters, preventing literals
in raw SQL from exposing sensitive data.
