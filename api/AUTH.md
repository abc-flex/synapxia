# FastAPI-Users Authentication Implementation

## Overview

This document describes the authentication system implemented using FastAPI-Users with SQLModel integration for the SynapxIA API.

## Features

✅ **JWT-based Authentication** - Stateless token authentication
✅ **Password Hashing** - Bcrypt password hashing with passlib
✅ **User Registration** - New user registration with validation
✅ **Login/Logout** - Standard authentication endpoints
✅ **Password Change** - Users can change their passwords
✅ **Profile-based Access** - Integration with existing profile/privilege system
✅ **Superuser Support** - Admin users with elevated privileges
✅ **Last Login Tracking** - Automatic recording of last login timestamp

## Architecture

### Components

1. **`auth/routes.py`** - Authentication endpoints and JWT token management
2. **`auth/schemas.py`** - Pydantic schemas for auth requests/responses
3. **`admin/internal/models.py`** - Extended User model with `is_superuser` field
4. **`db/sql/1-admin-ddl.sql`** - Updated user table with `is_superuser` column
5. **`db/sql/0-migrations-fastapi-users.sql`** - Migration to update existing databases

### Modified Files

The following existing files were extended:
- `app/admin/internal/models.py` - Added `is_superuser` field to User model
- `app/main.py` - Imported and registered auth routes
- `pyproject.toml` - Added FastAPI-Users dependencies

## Endpoints

### Authentication Endpoints

#### POST `/api/auth/login`
Login and get JWT access token.

**Request:**
```json
{
  "username": "admin",
  "password": "Admin123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@synapxia.org",
    "first_name": "Platform",
    "last_name": "Administrator",
    "profile": "ADMINISTRATOR",
    "unit": "GEN_AI"
  }
}
```

#### POST `/api/auth/register`
Register a new user.

**Request:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "profile": "COLLABORATOR",
  "unit": "ENG"
}
```

**Response:**
```json
{
  "id": 2,
  "username": "john_doe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "profile": "COLLABORATOR",
  "unit": "ENG",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2026-03-09T10:30:00+00:00",
  "last_login_at": null
}
```

#### GET `/api/auth/me`
Get current authenticated user profile.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@synapxia.org",
  "first_name": "Platform",
  "last_name": "Administrator",
  "profile": "ADMINISTRATOR",
  "unit": "GEN_AI",
  "is_active": true,
  "is_superuser": true,
  "created_at": "2026-03-09T10:00:00+00:00",
  "last_login_at": "2026-03-09T10:35:12+00:00"
}
```

#### POST `/api/auth/change-password`
Change password for current user.

**Request:**
```json
{
  "old_password": "Admin123!",
  "new_password": "NewSecurePass456!"
}
```

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

#### POST `/api/auth/logout`
Logout endpoint (client-side token removal recommended).

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

## Usage Examples

### Using cURL

#### Login
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=Admin123!"
```

#### Get current user
```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Register new user
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "new@example.com",
    "password": "SecurePass123!",
    "first_name": "New",
    "last_name": "User",
    "profile": "COLLABORATOR",
    "unit": "ENG"
  }'
```

### Using Python requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Login
response = requests.post(
    f"{BASE_URL}/api/auth/login",
    data={"username": "admin", "password": "Admin123!"}
)
data = response.json()
access_token = data["access_token"]

# Get current user
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
print(response.json())

# Change password
response = requests.post(
    f"{BASE_URL}/api/auth/change-password",
    json={
        "old_password": "Admin123!",
        "new_password": "NewSecurePass456!"
    },
    headers=headers
)
print(response.json())
```

## Database Setup

### 1. Create new database with auth support

If creating a fresh database, use the updated DDL that includes the `is_superuser` column:

```bash
psql -U postgres -d synapxia -f db/sql/1-admin-ddl.sql
psql -U postgres -d synapxia -f db/sql/1-admin-insert.sql
```

### 2. Migrate existing database

If you have an existing database, run the migration:

```bash
psql -U postgres -d synapxia -f db/sql/0-migrations-fastapi-users.sql
```

### 3. Generate password hash

To create a bcrypt hash for a password:

```bash
cd api
python hash_password.py
```

Or in Python:
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed = pwd_context.hash("your_password_here")
print(hashed)
```

## Configuration

### Environment Variables

Add the following to your `.env` file:

```env
# Authentication
SECRET_KEY=your-super-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_SCHEMA=synapxia
```

**Important:** Change `SECRET_KEY` in production to a secure random value.

## Security Considerations

1. **SECRET_KEY** - Must be changed in production. Generate a secure key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **HTTPS** - Always use HTTPS in production for token transmission

3. **Token Expiration** - Access tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 minutes)

4. **Password Requirements** - Minimum 8 characters (enforced in registration)

5. **Bcrypt Hashing** - Passwords are hashed with bcrypt (cost factor: 12) and never stored in plain text

## Integration with Existing Privilege System

The authentication system integrates seamlessly with SynapxIA's existing privilege system:

```python
from app.auth.routes import get_current_active_user
from app.admin.internal.models import User
from fastapi import Depends

@app.get("/protected-endpoint")
async def protected_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    # User is authenticated
    # Use current_user.profile and unit for authorization
    # Query privileges table for detailed access control
    return {"user": current_user.username}
```

## Troubleshooting

### "Could not validate credentials"
- Ensure the token is valid and not expired
- Check that `SECRET_KEY` matches between token generation and validation
- Verify the Authorization header format: `Bearer <token>`

### "Incorrect username or password"
- Verify username/email and password are correct
- User account must be active (`is_active == True`)

### "User not found" during login
- Check that user exists in database
- Username is case-sensitive
- Can login with either username or email

### Database migration issues
- Ensure the `is_superuser` column was added successfully
- Check column exists: `SELECT is_superuser FROM users LIMIT 1;`
- If missing, run migration manually

## Future Enhancements

- [ ] Email verification for new registrations
- [ ] Refresh token support for longer sessions
- [ ] OAuth2/OIDC integration
- [ ] Two-factor authentication (2FA)
- [ ] Password reset via email
- [ ] Audit logging for authentication events
- [ ] Rate limiting on login attempts
