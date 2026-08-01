# Authentication

The current scaffold supports only internal username/password authentication.
Clients must store and send the opaque token unchanged; they must not parse it
as a JWT. The scaffold does not include RBAC, SSO, refresh tokens, or an
application-specific user system. Add those capabilities only after a project
confirms that it needs them.

## Obtain a Token

- URL: `/api/auth/token`
- Method: `POST`

### Purpose

An internal user signs in with a username and password and receives an opaque
token together with the current user information.

### Authentication and Headers

- Authentication: none.
- `Content-Type`: `application/x-www-form-urlencoded`.
- Other headers: none are required; a successful response includes
  `Cache-Control: no-store`.

### Path and Query Parameters

None.

### Request

- `username`: required string. Internal usernames are case-insensitive and are
  normalized to lowercase by the server.
- `password`: required string.
- Other optional OAuth2 form fields do not participate in the current
  username/password authentication flow. The endpoint does not accept
  `auth_type`.

#### Request Body Example

```text
username=scaffold.admin.example&password=<password>
```

### Successful Response

- Status: `200 OK`.
- Meaning: returns the current user and issues an opaque token prefixed with
  `sess_`.
- `id`: user ID.
- `username`: normalized internal username.
- `name`: user display name.
- `created_at`, `updated_at`: timezone-naive `Asia/Shanghai` local timestamps.
- `access_token`: opaque token; clients must not parse it.
- `token_type`: always `bearer`.

#### Successful Response Example

```json
{
  "id": 1,
  "username": "scaffold.admin.example",
  "name": "Scaffold Admin",
  "created_at": "2026-07-25T11:44:10.329974",
  "updated_at": "2026-07-25T11:44:10.329980",
  "access_token": "<opaque-token>",
  "token_type": "bearer"
}
```

After a successful sign-in, the frontend may use the user information in this
response directly. It does not need to request `/api/auth/me` immediately.

### Stable Business Errors

| Status | `detail` | Trigger |
| --- | --- | --- |
| `401` | `Invalid or expired credentials` | The account does not exist, the password is incorrect, the account is disabled, or the username format is invalid |
| `503` | `Session store unavailable` | The Redis session store is unavailable |

A form missing required fields returns `422`; use the current OpenAPI document
for its exact shape. A `401` response also includes
`WWW-Authenticate: Bearer` and does not reveal whether the account exists or
is disabled.

### State Side Effects

A successful sign-in creates a Redis session with a TTL. The raw token is
returned only to the caller; the Redis key contains only the token's SHA-256
digest.

## Get the Current User

- URL: `/api/auth/me`
- Method: `GET`

### Purpose

An authenticated user restores the signed-in state and obtains the current
user information from the database.

### Authentication and Headers

- Authentication: `Authorization: Bearer <opaque-token>`.
- `Content-Type`: not applicable.
- Other headers: none.

### Path and Query Parameters

None.

### Request

**Request body: none.**

### Successful Response

- Status: `200 OK`.
- Meaning: returns the current user without issuing a new token.
- `username` is the login identifier and `name` is the display name. Frontends
  must not treat them as interchangeable.

#### Successful Response Example

```json
{
  "id": 1,
  "username": "scaffold.admin.example",
  "name": "Scaffold Admin",
  "created_at": "2026-07-25T11:44:10.329974",
  "updated_at": "2026-07-25T11:44:10.329980"
}
```

The scaffold does not include avatar, role, or permission fields. A project
that needs them should extend its own user read model.

### Stable Business Errors

| Status | `detail` | Trigger |
| --- | --- | --- |
| `401` | `Invalid or expired credentials` | The token is missing, invalid, expired, revoked, version-mismatched, or belongs to a disabled account |
| `503` | `Session store unavailable` | The Redis session store is unavailable |

A `401` response also includes `WWW-Authenticate: Bearer`.

### State Side Effects

None. Each request reads the Redis session and the current MySQL account state.
It does not extend the session lifetime.

## Log Out

- URL: `/api/auth/logout`
- Method: `POST`

### Purpose

An authenticated user revokes the Redis session associated with the current
token.

### Authentication and Headers

- Authentication: `Authorization: Bearer <opaque-token>`.
- `Content-Type`: not applicable.
- Other headers: none.

### Path and Query Parameters

None.

### Request

**Request body: none.**

### Successful Response

- Status: `204 No Content`.
- Meaning: the current session has been deleted from Redis.

#### Successful Response Example

**Response body: none.**

### Stable Business Errors

| Status | `detail` | Trigger |
| --- | --- | --- |
| `401` | `Invalid or expired credentials` | The token is missing, invalid, expired, revoked, version-mismatched, or belongs to a disabled account |
| `503` | `Session store unavailable` | The Redis session store is unavailable |

A `401` response also includes `WWW-Authenticate: Bearer`.

### State Side Effects

Success deletes the current Redis session. Other sessions for the same account
remain valid. Reusing the old token on a protected endpoint returns `401`.

## Authentication Flow

1. The user enters an internal username and password.
2. The frontend requests an opaque token and the current user information.
3. The frontend stores the token unchanged and does not parse it.
4. Later requests send `Authorization: Bearer <opaque-token>`.
5. The server validates the Redis session, account state, and session version.
6. The frontend may request the current-user endpoint to restore signed-in
   state.
7. On logout, the server deletes the current Redis session.

## Frontend Integration Steps

1. Use the README `create-user` command to create a test account. Enter the
   password through the hidden prompt.
2. Submit `/api/auth/token` as a URL-encoded form.
3. Validate the response fields and store `access_token`.
4. Call `/api/auth/me` with the bearer token and verify the user information.
5. Call `/api/auth/logout` and verify the `204` response.
6. Call `/api/auth/me` again and verify that the old token returns `401`.

The repository does not provide a fixed test account or plaintext test
password. Use the current OpenAPI document for exact field types and
validation rules.

## Session and Security Semantics

- Redis keys contain only the token's SHA-256 digest. Raw tokens do not enter
  the Redis keyspace, logs, or operational query results.
- Sessions are valid for seven days by default. An account may be signed in on
  multiple clients at the same time.
- Password resets, account disabling, and account re-enabling invalidate all
  historical sessions for that account.
- Every authenticated request reads Redis and MySQL to verify the current
  account state and session version. Authentication is not a Redis-only check.

## Account Maintenance

Accounts are created and maintained only through the Typer commands documented
in the README. Passwords and tokens being inspected are entered through hidden
prompts and are not accepted as plaintext command-line arguments.

The scaffold does not enforce a minimum password length. Projects that require
a password-strength policy should add it to their own account creation and
password reset flows.

`inspect-session` diagnoses one session and displays only its digest
fingerprint, user ID, session version, database version, creation time, and
remaining TTL.
