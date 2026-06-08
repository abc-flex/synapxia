# Security Deployment Guide

This document explains how to deploy the secured API and UI to Vercel with proper security configuration.

## Overview

The security implementation (PR #25) adds:
- ✅ JWT authentication on all API endpoints (except /login, /register, /health)
- ✅ Role-based access control (RBAC) via privilege matrix
- ✅ Frontend route guards and auto-logout on auth errors
- ✅ Rate limiting on login attempts

**These features require specific environment variables to work in production.**

---

## API Deployment (Vercel Functions)

### Required Environment Variables

All variables must be set in the Vercel dashboard under **Settings → Environment Variables**.

#### 1. **SECRET_KEY** (CRITICAL!)

Used to sign JWT tokens. If this changes, all existing tokens become invalid.

```bash
# Generate a secure random key:
openssl rand -hex 32

# Example output (32-char hex string):
a7f3e2d9c1b4f6e8a2d5c3f1e9b7a4d6

# Set in Vercel:
SECRET_KEY = a7f3e2d9c1b4f6e8a2d5c3f1e9b7a4d6
```

**⚠️ NEVER commit SECRET_KEY to git**
**⚠️ NEVER share SECRET_KEY in logs or error messages**
**⚠️ Regenerate and rotate periodically in production**

#### 2. **CORS_ORIGINS**

Comma-separated list of allowed frontend origins. Without this, CORS will fail.

```bash
# For production:
CORS_ORIGINS = https://your-ui-domain.vercel.app

# For multiple environments:
CORS_ORIGINS = https://your-ui-domain.vercel.app,https://staging-ui.vercel.app

# NEVER use wildcard (*) in production with credentials=True
```

**Why:** The API now sets `allow_credentials=True` for explicit origins, which allows the JWT Bearer token to be sent cross-origin.

#### 3. **POSTGRES_URL** (or Neon Integration)

Database connection string. Set via:
- Option A: Vercel PostgreSQL integration (recommended) - auto-injected
- Option B: Manual Neon database connection string

```bash
# If using Neon database:
POSTGRES_URL = postgresql://user:password@region.neon.tech/database?sslmode=require
```

#### 4. **APP_ENV**

```bash
# For production:
APP_ENV = production

# This disables SQL echo logging (security + performance)
```

### Environment Variable Checklist

- [ ] `SECRET_KEY` - 32-char hex string (generated with `openssl rand -hex 32`)
- [ ] `CORS_ORIGINS` - Frontend URL (e.g., `https://synapxia.vercel.app`)
- [ ] `POSTGRES_URL` - Database connection string
- [ ] `APP_ENV` - Set to `production`

### Verification Steps

After deploying to Vercel:

```bash
# 1. Test unauthenticated access (should fail with 401)
curl https://your-api.vercel.app/api/users/
# Expected: {"detail":"Not authenticated"}

# 2. Test login (should return JWT)
curl -X POST https://your-api.vercel.app/api/auth/login \
  -d "username=admin&password=Admin123!"
# Expected: {"access_token":"eyJ...", "token_type":"bearer", "user":{...}}

# 3. Test authenticated access (should work)
TOKEN=$(curl ... | jq -r '.access_token')
curl -H "Authorization: Bearer $TOKEN" \
  https://your-api.vercel.app/api/users/
# Expected: [{"id":1, "username":"admin", ...}, ...]
```

---

## UI Deployment (Vercel Static + Edge Functions)

### Required Environment Variables

Set in Vercel dashboard under **Settings → Environment Variables**.

#### 1. **PUBLIC_API_BASE_URL**

The deployed API URL. Frontend calls this to authenticate and fetch data.

```bash
# For production:
PUBLIC_API_BASE_URL = https://your-api.vercel.app

# ⚠️ Must match CORS_ORIGINS on the API side!
# ⚠️ No trailing slash
```

#### 2. **SITE_URL** (Optional)

Used by Astro for canonical links and sitemaps.

```bash
SITE_URL = https://your-ui.vercel.app
```

### Environment Variable Checklist

- [ ] `PUBLIC_API_BASE_URL` - API URL (e.g., `https://synapxia-api.vercel.app`)
- [ ] `SITE_URL` - UI URL (e.g., `https://synapxia.vercel.app`)

### Verification Steps

After deploying to Vercel:

```bash
# 1. Test redirect to login (unauthenticated)
curl https://your-ui.vercel.app/admin/users
# Expected: Redirect to /login (or 307 status)

# 2. Test login page loads
curl https://your-ui.vercel.app/login
# Expected: 200 OK with HTML containing login form

# 3. Test login functionality (manual browser test)
# - Open https://your-ui.vercel.app/login
# - Enter admin / Admin123!
# - Should redirect to /dashboard
# - Should see list of users
```

---

## Deployment Checklist

### Before Deploying API

- [ ] Generate `SECRET_KEY` with `openssl rand -hex 32`
- [ ] Set `SECRET_KEY` in Vercel dashboard
- [ ] Set `CORS_ORIGINS` to frontend URL (no trailing slash)
- [ ] Set `APP_ENV = production`
- [ ] Verify `POSTGRES_URL` (via Neon integration or manual)
- [ ] Push code to GitHub (triggers Vercel build)
- [ ] Wait for Vercel build to complete
- [ ] Test API endpoints with curl (see verification steps above)

### Before Deploying UI

- [ ] Set `PUBLIC_API_BASE_URL` to API URL (no trailing slash)
- [ ] Verify it matches `CORS_ORIGINS` on API side
- [ ] Set `SITE_URL` (optional but recommended)
- [ ] Push code to GitHub (triggers Vercel build)
- [ ] Wait for Vercel build to complete
- [ ] Test login page and protected routes (see verification steps above)

---

## Security Best Practices

### JWT Token Management

1. **SECRET_KEY Rotation**
   - Rotate every 90 days in production
   - Use Vercel versioning to keep old secret for grace period
   - Existing tokens continue to work with old secret during grace period

2. **Token Expiry**
   - Default: 60 minutes (see `ACCESS_TOKEN_EXPIRE_MINUTES` in `api/app/auth/routes.py`)
   - Users must re-login after 60 minutes
   - Implement refresh tokens in Phase 2 (optional)

3. **CORS with Credentials**
   - API only allows credentials when explicit origins provided
   - Wildcard origins automatically disable credentials (CORS spec compliance)
   - This prevents accidental exposure of tokens

### Environment Variables

1. **Never Commit Secrets**
   ```bash
   # ✅ DO: Use Vercel dashboard
   # ✅ DO: Use `vercel env` CLI
   # ❌ DON'T: Commit SECRET_KEY to git
   # ❌ DON'T: Include in commit messages
   ```

2. **Audit Trail**
   - Vercel logs all env var changes
   - Check Vercel Settings → Audit Logs
   - Monitor for unauthorized changes

3. **Multiple Environments**
   ```bash
   # Vercel allows per-environment secrets
   # - Production
   # - Preview (staging)
   # - Development
   
   # Set different SECRET_KEY, CORS_ORIGINS for each
   ```

### Database Security

1. **Connection Pooling**
   - Neon/Vercel Postgres handles this automatically
   - Connection pool recycled every 60-90 minutes

2. **SSL/TLS**
   - `POSTGRES_URL` must use `sslmode=require`
   - All connections encrypted in transit

3. **Backups**
   - Neon provides automated daily backups
   - Retention: 7 days (default)
   - Configure in Neon dashboard

---

## Troubleshooting

### Problem: API returns "Cannot connect to database"

**Cause**: `POSTGRES_URL` not set or invalid

**Solution**:
1. Check Vercel dashboard for `POSTGRES_URL` var
2. If using Neon, verify integration is linked
3. Test connection manually:
   ```bash
   psql $POSTGRES_URL -c "SELECT 1"
   ```

### Problem: Frontend stuck on login page, returns 403 Forbidden

**Cause**: User lacks privilege for requested resource

**Solution**:
1. Verify user is logged in (check localStorage `auth_token`)
2. Verify user profile has required privilege
3. Check API logs for privilege denial messages

### Problem: CORS error in browser console

**Cause**: `CORS_ORIGINS` doesn't match frontend URL

**Solution**:
1. Get exact frontend URL from browser address bar
2. Add to `CORS_ORIGINS` on API
3. Redeploy API
4. Clear browser cache and retry

### Problem: JWT token rejected with 401 Unauthorized

**Cause**: `SECRET_KEY` rotated or mismatched between deployments

**Solution**:
1. Ensure `SECRET_KEY` is same in all API instances
2. Check Vercel logs for JWT decode errors
3. Force user logout and re-login with `window.location.href = '/login'`

### Problem: Rate limiting locks user during testing

**Cause**: 5 failed login attempts trigger 15-minute lockout

**Solution**:
1. Use incognito/private window for each test
2. Or wait 15 minutes before retrying
3. Or use correct credentials (admin / Admin123!)

---

## Rollback Procedure

If security deployment causes issues:

1. **Revert API Vercel deployment**:
   - Go to Vercel dashboard
   - Click "Deployments"
   - Find last known-good deployment
   - Click "Promote to Production"

2. **Revert UI Vercel deployment**:
   - Same process as API

3. **Investigate root cause**:
   - Check Vercel logs
   - Verify environment variables
   - Check API health endpoint: `/health`

---

## Post-Deployment Monitoring

### Daily Checks

```bash
# 1. Check API health
curl https://your-api.vercel.app/health
# Expected: {"status":"healthy","database":"connected"}

# 2. Check login is accessible
curl https://your-ui.vercel.app/login
# Expected: 200 OK

# 3. Monitor failed logins (if logging implemented)
# Check API logs for 401 errors from /api/auth/login
```

### Weekly Checks

- [ ] Review Vercel audit logs for env var changes
- [ ] Check database backups are completing
- [ ] Monitor error rates in Vercel analytics
- [ ] Test refresh token workflow (Phase 2)

### Monthly Checks

- [ ] Review user access logs
- [ ] Plan SECRET_KEY rotation
- [ ] Update CORS_ORIGINS if adding new deployments
- [ ] Audit privilege matrix (are correct users in correct roles?)

---

## References

- [Vercel Environment Variables](https://vercel.com/docs/projects/environment-variables)
- [Neon Connection Strings](https://neon.tech/docs/connect/connection-string)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [CORS Specification](https://fetch.spec.whatwg.org/#cors-protocol)
