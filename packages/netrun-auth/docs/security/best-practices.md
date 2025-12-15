# Security Best Practices

Security guidelines for using netrun-auth in production.

## 1. Token Security

### Access Token Management

```
✓ Short expiry (15 minutes default)
✓ Limited claims (only necessary data)
✓ Signed with RS256 (asymmetric)
✓ Validated on every request
✗ Never store in localStorage (XSS vulnerable)
✗ Never expose in logs or error messages
```

**Best Practice**:

```python
# Correct: Store in httponly, secure cookie
response.set_cookie(
    "access_token",
    token,
    httponly=True,      # Prevents JavaScript access
    secure=True,        # HTTPS only
    samesite="strict"   # CSRF protection
)

# Incorrect: localStorage (vulnerable to XSS)
# localStorage.setItem("token", token)  # DON'T DO THIS
```

### Refresh Token Handling

```
✓ 30-day expiry (configurable)
✓ Single-use (invalidated on refresh)
✓ Stored securely (httponly cookie)
✓ Never exposed to frontend
✓ Rotated on each use
```

**Implementation**:

```python
@app.post("/auth/refresh")
async def refresh_token(request: Request):
    """Refresh access token using refresh token."""

    # Get refresh token from secure httponly cookie
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    # Validate and refresh
    new_token_pair = await jwt_manager.refresh_token(refresh_token)

    # Set new tokens in secure cookies
    response = JSONResponse(content={"token_type": "Bearer"})
    response.set_cookie(
        "access_token",
        new_token_pair.access_token,
        httponly=True,
        secure=True,
        samesite="strict"
    )
    response.set_cookie(
        "refresh_token",
        new_token_pair.refresh_token,
        httponly=True,
        secure=True,
        samesite="strict"
    )

    return response
```

## 2. Password Security

### Requirements

```
Minimum 12 characters (OWASP recommendation)
1 uppercase letter
1 lowercase letter
1 number
1 special character
```

**Configuration**:

```python
config = AuthConfig(
    password_min_length=12,
    password_require_uppercase=True,
    password_require_numbers=True,
    password_require_special=True,
    password_expiry_days=90
)
```

### Hashing Algorithm

```
Algorithm: Argon2id
Memory: 19 MB (resistant to GPU attacks)
Time: 2 iterations
Parallelism: 4 threads
Result: 1-2 seconds per hash (intentionally slow)
```

**Why Slow?**: Prevents brute force attacks. Attackers would need seconds to try millions of passwords.

### Password Reset

```python
# Never reveal if email exists
@app.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Request password reset."""

    # Don't reveal if email exists (prevents user enumeration)
    if user := await db.get_user_by_email(request.email):
        # Send reset email
        await send_reset_email(user)

    # Always return same message
    return {"message": "If email exists, reset link sent"}
```

## 3. Authentication Flow Security

### CSRF Protection

```python
from fastapi.middleware.csrf import CsrfProtectionMiddleware

app.add_middleware(
    CsrfProtectionMiddleware,
    secret="your-csrf-secret"
)
```

### State Parameter Validation

```python
@app.get("/auth/oauth-callback")
async def oauth_callback(code: str, state: str, request: Request):
    """Validate state to prevent CSRF."""

    # Verify state matches what we sent
    stored_state = request.session.get("oauth_state")

    if state != stored_state:
        raise HTTPException(status_code=400, detail="Invalid state")

    # Proceed with token exchange
```

### PKCE for Public Clients

```python
# Generate code verifier and challenge
code_verifier = generate_random_string(128)
code_challenge = base64url(sha256(code_verifier))

# Include in authorization request
auth_url = f"{provider_url}?code_challenge={code_challenge}&code_challenge_method=S256"

# Include in token request
token = await oauth_client.get_token(
    code=code,
    code_verifier=code_verifier  # Secret only in backend
)
```

## 4. Rate Limiting

### Brute Force Protection

```python
config = AuthConfig(
    rate_limit_enabled=True,
    rate_limit_requests_per_minute=60,
    rate_limit_burst_size=5
)

app.add_middleware(
    AuthenticationMiddleware,
    jwt_manager=jwt_manager,
    redis_client=redis_client,
    config=config
)
```

### Login Attempt Throttling

```python
@app.post("/login")
async def login(request: LoginRequest):
    """Login with rate limiting."""

    user_ip = request.client.host

    # Check rate limit
    login_attempts = await redis.get(f"login_attempts:{user_ip}")

    if login_attempts and int(login_attempts) > 5:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts, try again in 15 minutes",
            headers={"Retry-After": "900"}
        )

    # Attempt login
    try:
        # ... validate credentials ...
        return token_pair
    except AuthenticationError:
        # Increment attempt counter
        await redis.incr(f"login_attempts:{user_ip}")
        await redis.expire(f"login_attempts:{user_ip}", 900)  # 15 min TTL

        raise HTTPException(status_code=401, detail="Invalid credentials")
```

## 5. HTTPS and Transport Security

### Enforce HTTPS

```python
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(HTTPSRedirectMiddleware)
```

### Security Headers

```python
from fastapi.middleware import Middleware
from starlette.middleware.headers import ServerErrorMiddleware

app.add_middleware(
    ServerErrorMiddleware,
    handler=lambda r, e: JSONResponse({"detail": "Internal server error"})
)

# Add security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    return response
```

## 6. API Key Security

### Generation

```python
import secrets

# Generate cryptographically secure API key
api_key = secrets.token_urlsafe(32)  # 32 bytes = 256-bit

# Hash before storing in database
hashed = password_manager.hash_password(api_key)
```

### Validation

```python
@app.get("/protected")
async def protected(request: Request):
    """Validate API key from header."""

    api_key = request.headers.get("X-API-Key")

    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Get stored hash from database
    stored_hash = await db.get_api_key_hash(api_key_id)

    # Constant-time comparison
    if not password_manager.verify_password(api_key, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Proceed with request
```

### Rotation

```python
@app.post("/api-keys/rotate")
async def rotate_api_key(key_id: str, user: User = Depends(get_current_user)):
    """Rotate API key."""

    # Verify ownership
    key = await db.get_api_key(key_id)
    if key.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Generate new key
    new_key = secrets.token_urlsafe(32)
    hashed = password_manager.hash_password(new_key)

    # Update in database
    await db.update_api_key(key_id, hash=hashed)

    # Return new key (only time it's visible)
    return {"api_key": new_key}
```

## 7. Multi-Tenant Security

### Tenant Isolation

```python
@app.get("/organizations/{org_id}/data")
async def get_org_data(
    org_id: str,
    user: User = Depends(get_current_user)
):
    """Ensure user belongs to organization."""

    # Verify user's organization matches
    if user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not authorized for this organization")

    # Query data scoped to organization
    data = await db.get_org_data(org_id)

    return data
```

### Cross-Tenant Token Prevention

```python
# When generating tokens, include organization_id
token_pair = await jwt_manager.generate_token_pair(
    user_id=user_id,
    organization_id=organization_id,  # Critical for scoping
    roles=roles
)

# Validate on every request
@app.get("/protected")
async def protected(auth: AuthContext = Depends(get_auth_context)):
    """User's org_id is embedded in validated token."""

    # org_id is cryptographically signed
    print(auth.organization_id)  # Safe to use
```

## 8. Audit Logging

### Event Logging

```python
import logging
from datetime import datetime, timezone

logger = logging.getLogger("auth_audit")

@app.post("/login")
async def login(request: LoginRequest):
    """Log login attempts."""

    try:
        token_pair = await authenticate_user(request)

        logger.info(
            "Authentication success",
            extra={
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ip_address": request.client.host,
                "user_agent": request.headers.get("user-agent")
            }
        )

        return token_pair

    except AuthenticationError as e:
        logger.warning(
            "Authentication failed",
            extra={
                "email": request.email,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ip_address": request.client.host,
                "reason": str(e)
            }
        )

        raise HTTPException(status_code=401, detail="Invalid credentials")
```

### Database Audit Trail

```python
@app.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    user: User = Depends(require_roles("admin"))
):
    """Log administrative actions."""

    # Perform action
    await db.deactivate_user(user_id)

    # Log to audit table
    await db.log_audit(
        action="user_deactivated",
        actor_id=user.user_id,
        target_id=user_id,
        timestamp=datetime.now(timezone.utc),
        details={"reason": "admin_action"}
    )

    return {"message": "User deactivated"}
```

## 9. Dependency Management

### Keep Dependencies Updated

```bash
# Regular security audits
pip list --outdated

# Update dependencies
pip install --upgrade -r requirements.txt

# Check for known vulnerabilities
pip install safety
safety check
```

### Pin Versions

```
requirements.txt:
netrun-auth==1.0.0          # Pin exact version
fastapi==0.104.1
pydantic==2.5.0
cryptography==41.0.7       # Security-critical, pin exact
```

## 10. Compliance Standards

### NIST SP 800-63B

- [x] Strong authentication mechanisms (RS256)
- [x] Token expiration (15 min access, 30 day refresh)
- [x] Secure password requirements (Argon2id)
- [x] Rate limiting (prevent brute force)

### OWASP Top 10

- [x] A01:2021 Broken Access Control (RBAC implemented)
- [x] A02:2021 Cryptographic Failures (RS256, HTTPS)
- [x] A03:2021 Injection (parametrized queries)
- [x] A04:2021 Insecure Design (security by design)
- [x] A05:2021 Security Misconfiguration (secure defaults)
- [x] A06:2021 Vulnerable Components (updated dependencies)
- [x] A07:2021 Authentication Failures (strong auth)
- [x] A08:2021 Software/Data Integrity Failures (signed JWTs)
- [x] A09:2021 Logging/Monitoring Failures (audit logs)
- [x] A10:2021 SSRF (input validation)

### SOC2

- [x] Access controls implemented
- [x] Audit logging enabled
- [x] Encryption in transit (HTTPS)
- [x] Encryption at rest (password hashing)
- [x] Change management via versioning

## Security Checklist

Before deploying to production:

- [ ] All tokens use HTTPS only
- [ ] Access tokens expire in 15 minutes or less
- [ ] Refresh tokens single-use and rotated
- [ ] Password hashing uses Argon2id
- [ ] Rate limiting enabled
- [ ] CSRF protection implemented
- [ ] Security headers configured
- [ ] Audit logging enabled
- [ ] API keys hashed in database
- [ ] Admin actions logged
- [ ] Multi-tenant data isolation tested
- [ ] Dependencies updated and audited
- [ ] Error messages don't leak information
- [ ] User enumeration not possible
- [ ] HTTPS enforced
- [ ] CORS configured restrictively

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
