"""
backend/auth.py
===============
Authentication module for PMS:
- PostgreSQL-backed User store
- bcrypt password hashing & verification
- pyjwt signed JWT generation and decoding
- require_admin_jwt & require_admin_auth dependencies
- POST /auth/login, GET/POST/DELETE /auth/users
"""

import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Any

import jwt
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

_raw_jwt = os.getenv("JWT_SECRET")
if not _raw_jwt:
    if os.getenv("RENDER") or os.getenv("ENVIRONMENT") == "production":
        logger.critical(
            "CRITICAL SECURITY WARNING: JWT_SECRET environment variable is not set in production! "
            "Configure JWT_SECRET in your Render/deployment dashboard environment variables."
        )
    _raw_jwt = "pms-super-secret-jwt-signing-key-2026"
JWT_SECRET: str = _raw_jwt
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7


# ---------------------------------------------------------------------------
# Password utilities (bcrypt)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with automatic salt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception as exc:
        logger.warning(f"Password verification error: {exc}")
        return False


# ---------------------------------------------------------------------------
# JWT utilities (pyjwt)
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=JWT_EXPIRATION_DAYS))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# FastApi Dependencies
# ---------------------------------------------------------------------------

def require_admin_jwt(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> dict:
    """
    Dependency that decodes the JWT and checks role == 'admin'.
    Rejects unauthorized or non-admin requests.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected 'Bearer <token>'."
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token."
        )

    role = payload.get("role")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privilege required."
        )
    return payload


def require_admin_auth(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> dict:
    """
    Hybrid admin dependency: accepts either a valid admin API key ('X-API-Key')
    or a valid admin JWT ('Authorization: Bearer <jwt>').
    """
    expected_key = (os.getenv("PMS_API_KEY") or "pms-admin-secret-key").strip()
    if x_api_key and secrets.compare_digest(x_api_key.strip(), expected_key):
        return {"auth_type": "api_key", "role": "admin"}

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
            if payload.get("role") == "admin":
                return {"auth_type": "jwt", "role": "admin", **payload}
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privilege required."
            )
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key. Provide a valid 'X-API-Key' header."
    )


# ---------------------------------------------------------------------------
# Admin User Seeding
# ---------------------------------------------------------------------------

def seed_initial_admin(db: Session):
    """Ensure at least one admin user exists in the database on startup and credentials match config."""
    try:
        admin_username = (os.getenv("ADMIN_USERNAME") or "admin").strip()
        admin_password = (os.getenv("ADMIN_PASSWORD") or "").strip()
        if not admin_password:
            if os.getenv("RENDER") or os.getenv("ENVIRONMENT") == "production":
                logger.critical(
                    "CRITICAL SECURITY WARNING: ADMIN_PASSWORD environment variable is not set in production! "
                    "Configure ADMIN_PASSWORD in your Render/deployment dashboard environment variables."
                )
            admin_password = "PmsAdmin#Secure2026!"
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            new_admin = User(
                username=admin_username,
                password_hash=hash_password(admin_password),
                role="admin",
            )
            db.add(new_admin)
            db.commit()
            logger.info(f"Initialized default admin user: {admin_username}")
        else:
            # Sync username and password if changed in environment
            admin_obj: Any = admin
            needs_update = False
            if admin_obj.username != admin_username:
                admin_obj.username = admin_username
                needs_update = True
            if not verify_password(admin_password, str(admin_obj.password_hash)):
                admin_obj.password_hash = hash_password(admin_password)
                needs_update = True
            if needs_update:
                db.commit()
                logger.info("Updated admin credentials to match current environment configuration")
    except Exception as exc:
        db.rollback()
        logger.warning(f"Note on seeding admin user: {exc}")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=4)
    role: Optional[str] = "employee"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user by username & password, verify with bcrypt, and return signed JWT.
    """
    user = db.query(User).filter(User.username == req.username.strip()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not registered.",
            headers={"X-Auth-Reason": "user_not_found"}
        )

    user_obj: Any = user
    if not verify_password(req.password, str(user_obj.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password.",
            headers={"X-Auth-Reason": "wrong_password"}
        )

    token = create_access_token({
        "sub": user_obj.username,
        "user_id": user_obj.id,
        "role": user_obj.role,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict()
    }


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    admin_auth: dict = Depends(require_admin_auth)
):
    """List all registered users. Requires admin authorization."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [u.to_dict() for u in users]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    req: UserCreateRequest,
    db: Session = Depends(get_db),
    admin_auth: dict = Depends(require_admin_auth)
):
    """Create a new user. Requires admin authorization."""
    clean_username = req.username.strip()
    existing = db.query(User).filter(User.username == clean_username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{clean_username}' already exists."
        )

    new_user = User(
        username=clean_username,
        password_hash=hash_password(req.password),
        role=req.role or "employee",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user.to_dict()


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin_auth: dict = Depends(require_admin_auth)
):
    """Delete a user. Cannot delete an admin user."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    target_obj: Any = target
    if target_obj.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete administrator account.")

    db.delete(target)
    db.commit()
    return {"message": f"User '{target_obj.username}' deleted successfully."}
