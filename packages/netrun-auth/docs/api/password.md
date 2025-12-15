# Password Manager API

Complete reference for password hashing and validation.

## Overview

The `PasswordManager` class provides:
- Argon2id password hashing (OWASP compliant)
- Configurable password strength requirements
- Password validation with clear error messages
- Secure password comparison

## PasswordManager Class

### Initialization

```python
from netrun_auth import PasswordManager, AuthConfig

config = AuthConfig(
    password_min_length=12,
    password_require_uppercase=True,
    password_require_numbers=True,
    password_require_special=True
)

password_manager = PasswordManager(config)
```

### Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `password_min_length` | `int` | 12 | Minimum password length |
| `password_require_uppercase` | `bool` | True | Require at least one uppercase letter |
| `password_require_numbers` | `bool` | True | Require at least one digit |
| `password_require_special` | `bool` | True | Require at least one special character |
| `password_expiry_days` | `int` | 90 | Password expiration (0 = no expiry) |

## Methods

### hash_password()

```python
def hash_password(self, password: str) -> str:
    """
    Hash password using Argon2id algorithm.

    Args:
        password: Plain-text password to hash

    Returns:
        str - Hashed password safe for database storage

    Raises:
        PasswordValidationError: If password fails validation

    Example:
        hashed = password_manager.hash_password("MySecure!Pass123")
        # Store hashed in database
        user.password_hash = hashed
        await db.save(user)

    Security Notes:
        - Uses Argon2id algorithm (winner of Password Hashing Competition)
        - 19 MB memory cost
        - 2 iterations
        - 4 parallelism
        - Takes ~1-2 seconds to hash (intentionally slow for security)
    """
```

**Returns**: `str` - Hashed password

**Example Hash Output**:

```
$argon2id$v=19$m=19456,t=2,p=4$...
```

### verify_password()

```python
def verify_password(self, password: str, password_hash: str) -> bool:
    """
    Verify plain-text password against stored hash.

    Args:
        password: Plain-text password to verify
        password_hash: Stored password hash from database

    Returns:
        bool - True if password matches, False otherwise

    Example:
        user = await db.get_user(user_id)

        if password_manager.verify_password(
            provided_password,
            user.password_hash
        ):
            # Password is correct
            login_user()
        else:
            # Password is incorrect
            raise HTTPException(status_code=401, detail="Invalid password")
    """
```

**Returns**: `bool`

### validate_password()

```python
def validate_password(self, password: str) -> List[str]:
    """
    Validate password strength.

    Returns list of validation errors (empty if valid).

    Args:
        password: Password to validate

    Returns:
        List[str] - List of validation error messages

    Raises: None

    Example:
        errors = password_manager.validate_password("weak")

        if errors:
            return {
                "valid": False,
                "errors": errors
            }

        # If no errors, password is valid
        hashed = password_manager.hash_password(password)
    """
```

**Returns**: `List[str]` - Empty list if valid, error messages if invalid

**Example Validation Errors**:

```python
errors = password_manager.validate_password("test")
# Returns:
# [
#     "Password must be at least 12 characters long",
#     "Password must contain at least one uppercase letter",
#     "Password must contain at least one number",
#     "Password must contain at least one special character"
# ]
```

### check_password_strength()

```python
def check_password_strength(self, password: str) -> dict:
    """
    Check password strength with detailed feedback.

    Args:
        password: Password to check

    Returns:
        dict with 'strength' and 'recommendations' keys

    Example:
        result = password_manager.check_password_strength(password)

        return {
            "strength": result["strength"],  # "weak", "fair", "good", "strong"
            "score": result["score"],        # 0-100
            "recommendations": result["recommendations"]
        }
    """
```

**Returns**: `dict` with keys:
- `strength`: "weak", "fair", "good", or "strong"
- `score`: 0-100 score
- `recommendations`: List of improvement suggestions

## Password Strength Requirements

### Default Requirements

```
Minimum 12 characters
At least 1 uppercase letter (A-Z)
At least 1 lowercase letter (a-z)
At least 1 number (0-9)
At least 1 special character (!@#$%^&*)
```

### Examples

**Valid**:
```
MySecurePass123!
W0nd3r!ul-Pss
Pr0tect@d2025
```

**Invalid**:
```
password123        # No uppercase, no special
Pass@123           # Only 8 characters
UPPERCASE123!      # No lowercase
NoNumbers!         # No numbers
NoSpecial123       # No special character
```

## Argon2id Hashing

### Why Argon2id?

```
✓ Winner of Password Hashing Competition (2015)
✓ Resistant to GPU and ASIC attacks
✓ Configurable memory and time costs
✓ Recommended by OWASP
✓ Industry standard (used by major platforms)
```

### Hashing Parameters

```python
# netrun-auth defaults (NIST-compliant)
Memory cost:   19 MB
Time cost:     2 iterations
Parallelism:   4 threads
Hash length:   32 bytes

Result: ~1-2 seconds to hash (slow is good for security)
```

### Hash Format

```
$argon2id$v=19$m=19456,t=2,p=4$<salt>$<hash>
                    ↑      ↑  ↑
                memory   time parallelism
```

## Integration Example

### User Registration

```python
from fastapi import FastAPI, HTTPException
from netrun_auth import PasswordManager, AuthConfig
from pydantic import BaseModel

app = FastAPI()
password_manager = PasswordManager(AuthConfig())

class RegisterRequest(BaseModel):
    email: str
    password: str

@app.post("/register")
async def register(request: RegisterRequest):
    """Register new user with password."""

    # 1. Validate password
    errors = password_manager.validate_password(request.password)

    if errors:
        return {
            "error": "Invalid password",
            "details": errors
        }, 400

    # 2. Hash password
    hashed_password = password_manager.hash_password(request.password)

    # 3. Store user in database
    # user = User(
    #     email=request.email,
    #     password_hash=hashed_password
    # )
    # await db.save(user)

    return {"message": "User registered successfully"}
```

### User Login

```python
class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login")
async def login(request: LoginRequest):
    """Login with email and password."""

    # 1. Fetch user from database
    # user = await db.get_user_by_email(request.email)
    # if not user:
    #     raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2. Verify password
    if not password_manager.verify_password(
        request.password,
        user.password_hash  # From database
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 3. Generate tokens
    # token_pair = await jwt_manager.generate_token_pair(user.user_id)

    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": "Bearer"
    }
```

### Password Change

```python
from netrun_auth.dependencies import get_current_user
from netrun_auth.types import User

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@app.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user)
):
    """Change user password."""

    # 1. Fetch user
    # current_user = await db.get_user(user.user_id)

    # 2. Verify current password
    if not password_manager.verify_password(
        request.current_password,
        current_user.password_hash
    ):
        raise HTTPException(status_code=401, detail="Current password incorrect")

    # 3. Validate new password
    errors = password_manager.validate_password(request.new_password)
    if errors:
        return {"error": "Invalid new password", "details": errors}, 400

    # 4. Prevent reuse (compare to current)
    if password_manager.verify_password(
        request.new_password,
        current_user.password_hash
    ):
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current"
        )

    # 5. Hash and update
    new_hash = password_manager.hash_password(request.new_password)
    # current_user.password_hash = new_hash
    # await db.save(current_user)

    return {"message": "Password changed successfully"}
```

## Password Reset Flow

```python
from datetime import datetime, timedelta, timezone

class PasswordResetRequest(BaseModel):
    email: str

@app.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest):
    """Initiate password reset."""

    # 1. Find user
    # user = await db.get_user_by_email(request.email)
    # if not user:
    #     # Don't reveal if email exists
    #     return {"message": "Password reset link sent"}

    # 2. Generate reset token (valid for 15 minutes)
    reset_token = jwt_manager.generate_reset_token(user.user_id)

    # 3. Send email with reset link
    # send_email(
    #     user.email,
    #     "Password Reset",
    #     f"https://app.com/reset?token={reset_token}"
    # )

    return {"message": "Password reset link sent"}

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@app.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Complete password reset."""

    # 1. Validate reset token
    try:
        user_id = jwt_manager.verify_reset_token(request.token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # 2. Validate new password
    errors = password_manager.validate_password(request.new_password)
    if errors:
        return {"error": "Invalid password", "details": errors}, 400

    # 3. Hash and update
    hashed = password_manager.hash_password(request.new_password)
    # user = await db.get_user(user_id)
    # user.password_hash = hashed
    # await db.save(user)

    return {"message": "Password reset successfully"}
```

## Security Best Practices

1. **Never Store Plain-text**: Always hash passwords
2. **Use Argon2id**: Industry standard algorithm
3. **Slow Hashing**: 1-2 seconds per hash is intentional
4. **Rate Limiting**: Limit login attempts (prevent brute force)
5. **Secure Comparison**: Use constant-time comparison
6. **No User Enumeration**: Don't reveal if email exists
7. **Password Expiry**: Force change every 90 days
8. **History**: Prevent reusing previous passwords
9. **2FA**: Add second factor for critical accounts
10. **HTTPS Only**: Never transmit passwords over HTTP

## Performance Considerations

```
Hashing time:        1-2 seconds (intentional)
Verification time:   1-2 seconds (intentional)
Validation time:     <1ms
Memory usage:        19 MB per hash operation
```

Slow hashing is intentional to prevent brute force attacks!

## Error Handling

```python
from netrun_auth.exceptions import PasswordValidationError

try:
    hashed = password_manager.hash_password("weak")
except PasswordValidationError as e:
    return {
        "error": "Invalid password",
        "details": e.validation_errors
    }
```

## Configuration Example

```python
from netrun_auth import AuthConfig, PasswordManager

# Strict configuration
strict_config = AuthConfig(
    password_min_length=16,
    password_require_uppercase=True,
    password_require_numbers=True,
    password_require_special=True,
    password_expiry_days=60
)
strict_manager = PasswordManager(strict_config)

# Standard configuration
standard_config = AuthConfig(
    password_min_length=12,
    password_require_uppercase=True,
    password_require_numbers=True,
    password_require_special=True,
    password_expiry_days=90
)
standard_manager = PasswordManager(standard_config)

# Relaxed configuration (not recommended)
relaxed_config = AuthConfig(
    password_min_length=8,
    password_require_uppercase=False,
    password_require_numbers=True,
    password_require_special=False
)
relaxed_manager = PasswordManager(relaxed_config)
```

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
