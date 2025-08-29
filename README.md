# FastAPI REST Service

A minimalist yet production-ready FastAPI backend service with SQLAlchemy and Redis integration, featuring a complete JWT-based authentication system.

## Features

- JWT + Redis dual verification authentication system
- Async MySQL database operations (SQLAlchemy)
- Redis caching
- CLI tools for user management
- Automated testing with pytest
- Alembic database migrations
- Comprehensive exception handling
- Production-grade logging system

## Tech Stack

- Python 3.12+
- FastAPI
- MySQL 8.0+
- SQLAlchemy (Async)
- Redis
- Alembic
- pytest
- Typer (CLI)

## Getting Started

### Prerequisites

- Python 3.12+
- MySQL 8.0+
- Redis

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
   > Note: `uv pip install -r requirements.txt` is faster
3. Set up environment variables: `cp .env.example .env` and fill in the required values
4. Run database migrations: `alembic upgrade head`
5. Create initial user: `python app/cli.py create-user <username> --password <password>`
6. Start the development server: `uvicorn app.main:app --reload`

### Environment Configuration

Configure the following variables in your `.env` file:

```env
# Database
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_database_name

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT
JWT_SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=30

# Application
DEBUG=True
SECRET_KEY=your_app_secret_key
```

### Testing

> Note: Tests use a real database with test-specific configuration to ensure functionality

Run tests: `pytest` or `./run_tests.sh`

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Authentication

This service uses JWT tokens with Redis-based token management for secure authentication.

### Login Process

1. **OAuth2 Standard Endpoint**: `POST /api/v1/auth/token`
   - Standard OAuth2 password flow
   - Returns access token and token type

2. **Custom Login Endpoint**: `POST /api/v1/auth/login`
   - Custom login with additional user information
   - Returns access token and user details

### Protected Endpoints

Include the JWT token in the Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

### Example Usage

```bash
# Login and get token
curl -X POST "http://localhost:8000/api/v1/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=your_username&password=your_password"

# Use token to access protected endpoints
curl -X GET "http://localhost:8000/api/v1/auth/me" \
     -H "Authorization: Bearer <your_jwt_token>"

# Logout
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
     -H "Authorization: Bearer <your_jwt_token>"
```

## CLI Tools

The project includes CLI tools for user management:

```bash
# Create a new user
python app/cli.py create-user <username> --password <password> --name "Display Name"

# Get help
python app/cli.py --help
```

## Project Structure

```bash

app/
├── api/v1/          # API routes
├── cli/             # CLI tools
├── core/            # Core functionality (auth, config, deps)
├── db/              # Database and Redis connections
├── middleware/      # FastAPI middleware
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic schemas
└── services/        # Business logic services
```

## References

- [uv](https://docs.astral.sh/uv/getting-started/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
