# Authentication

## Authentication Flow

1. The user enters an internal username and password.
2. The frontend calls the login endpoint to obtain an opaque token and current
   user information.
3. The frontend stores the token unchanged and does not parse it.
4. Subsequent requests send the token through
   `Authorization: Bearer <token>`.
5. The server validates the Redis session, account status, and session version.
6. The frontend can restore login state through the current-user endpoint.
7. On logout, the server deletes the current Redis session.

## Capability Boundaries

The current version supports only internal usernames and passwords. The login
endpoint does not accept `auth_type` and does not reserve request fields for
WECHAT, PHONE, EMAIL, SSO, or other unimplemented methods. Design the
corresponding models and endpoints only after a project confirms the need.

## Obtain a Token

- URL: `/api/auth/token`
- Method: `POST`
- Content-Type: `application/x-www-form-urlencoded`
- Request:
  - `username`: Required internal login name. It is case-insensitive and
    normalized to lowercase by the server.
  - `password`: Required password.
- Response header:
  - `Cache-Control: no-store`
- Response:
  - `id`: User ID.
  - `username`: Internal login name.
  - `name`: User display name.
  - `created_at`: User creation time in `Asia/Shanghai` local time.
  - `updated_at`: User update time in `Asia/Shanghai` local time.
  - `access_token`: Opaque token with a `sess_` prefix. It is not a JWT and
    clients must not parse it.
  - `token_type`: Always `bearer`.

Request body example:

```text
username=scaffold.admin&password=<password>
```

Successful response example:

```json
{
  "id": 1,
  "username": "scaffold.admin",
  "name": "Scaffold Admin",
  "created_at": "2026-07-25T11:44:10.329974",
  "updated_at": "2026-07-25T11:44:10.329980",
  "access_token": "sess_example-token-value",
  "token_type": "bearer"
}
```

After login succeeds, the frontend can use the user information in the
response directly and does not need to request `/api/auth/me` immediately.

## Get the Current User

- URL: `/api/auth/me`
- Method: `GET`
- Request header:
  - `Authorization: Bearer <token>`

Successful response example:

```json
{
  "id": 1,
  "username": "scaffold.admin",
  "name": "Scaffold Admin",
  "created_at": "2026-07-25T11:44:10.329974",
  "updated_at": "2026-07-25T11:44:10.329980"
}
```

`username` is the login name and `name` is the display name. The frontend must
not use them interchangeably. The scaffold does not provide avatar, role, or
permission fields. Extend the project's user read model when those fields are
needed.

## Logout

- URL: `/api/auth/logout`
- Method: `POST`
- Request header:
  - `Authorization: Bearer <token>`
- Success status: `204 No Content`
- Response body: Empty

The frontend treats HTTP 204 as a successful logout. Reusing the same token to
request `/api/auth/me` after logout returns 401.

## Error Responses

| Scenario | HTTP status | `detail` |
|---|---:|---|
| Account missing, password incorrect, or account disabled | 401 | `Invalid or expired credentials` |
| Submitted username has an invalid format | 401 | `Invalid or expired credentials` |
| Token missing, expired, revoked, or version-invalidated | 401 | `Invalid or expired credentials` |
| Redis session store unavailable | 503 | `Session store unavailable` |
| Login form missing a required field | 422 | FastAPI validation response |

401 responses also include `WWW-Authenticate: Bearer`. All authentication
failures return the same message, so the frontend must not infer whether an
account exists or is disabled.

## Frontend Integration Steps

1. Use the README's `create-user` command on the backend to create a test
   account. Enter the password through the hidden interactive prompt.
2. Call `/api/auth/token` from the frontend using Form URL Encoded data.
3. Check the login response fields and store `access_token`.
4. Call `/api/auth/me` with the bearer token and verify the returned user.
5. Call `/api/auth/logout` and confirm that it returns 204.
6. Call `/api/auth/me` again and confirm that the old token returns 401.

The repository does not provide a fixed test account or plaintext test
password. OpenAPI remains authoritative for exact field types and validation
rules.

## Session and Security Semantics

- Redis keys contain only the token's SHA-256 digest. The raw token never
  enters the Redis keyspace, logs, or operational query output.
- Sessions are valid for seven days by default. The same account may be logged
  in on multiple clients at the same time.
- Password resets, account disabling, and account re-enabling invalidate all
  historical sessions for that account.
- Every authenticated request reads Redis and MySQL to check account status
  and session version immediately. Authentication is not a Redis-only check.

## Account Maintenance

Accounts can be created and maintained only through the Typer commands in the
README. Passwords and tokens being inspected are read through hidden
interactive prompts and are not accepted as plaintext command-line arguments.

The scaffold does not enforce a minimum password length. Add a password
strength policy to the project's account creation and reset flows when needed.

`inspect-session` diagnoses one session and displays only the digest
fingerprint, user ID, session version, database version, creation time, and
remaining TTL.
