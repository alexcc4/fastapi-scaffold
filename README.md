# FastAPI REST Service

A minimalist yet production-ready FastAPI backend service with SQLAlchemy and Redis integration. Features third-party authentication via Clerk.

## Features

- User authentication and authorization (via Clerk)
- Async MySQL with SQLAlchemy
- Redis caching
- Automated testing with pytest
- Alembic migrations
- Exception handling

## Tech Stack

- Python 3.12+
- FastAPI
- MySQL 8.0+
- SQLAlchemy (Async)
- Redis
- Alembic
- pytest

## Getting Started

### Prerequisites

- Python 3.12+
- MySQL 8.0+
- Redis
- Clerk account (for authentication)

### Installation

- Clone the repository
- Install dependencies: `pip install -r requirements.txt`:
  > Note: `uv pip install -r requirements.txt` is faster 
- Set up environment variables: `cp .env.example .env`: fill in the blanks
- Run database migrations: `alembic init alembic`
- Run the development server: `uvicorn app.main:app --reload`


### Testing

> Note: Tests use a real database with a test-specific URL to ensure functionality

- Run tests: `pytest` or `./run_tests.sh`

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Debug Authentication(Optional)

This service uses Clerk for authentication. Frontend applications need to:

1. Implement Clerk authentication flow
2. Pass the Clerk session token in Authorization header
3. Handle 401/403 responses appropriately

### Requirements

- Clerk account

### Frontend
- cd frontend
- install node.js
- install dependencies: `npm install`
- `cp .env.example .env`: set the clerk publishable key and secret
- run frontend: `npm run dev`
- open `http://localhost:3000` in browser: get the session_id

### Backend
- set the CLERK_SECRET_KEY in .env

### Last Step
- use the session_id to get the user info: `curl -X GET "http://localhost:8000/api/v1/auth/login" -H "Authorization: Bearer {session_id}"`


## References

- [uv](https://docs.astral.sh/uv/getting-started/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Clerk](https://clerk.com/)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
