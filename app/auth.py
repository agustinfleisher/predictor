"""
Auth routes: signup/login.
"""

from __future__ import annotations

import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, status

from .config import Settings, get_settings
from . import schemas, storage
from .security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.TokenResponse)
def signup(payload: schemas.UserCreate, settings: Settings = Depends(get_settings)):
    if storage.get_user_by_email(settings, payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    if storage.get_user_by_username(settings, payload.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    existing = storage.get_user_by_email(settings, payload.email)
    password_hash = hash_password(payload.password)
    user_id = storage.create_user(settings, payload.email, payload.username, password_hash)
    token = create_access_token({"sub": str(user_id)}, settings=settings)
    return schemas.TokenResponse(access_token=token)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.UserLogin, settings: Settings = Depends(get_settings)):
    identifier = payload.identifier
    user = storage.get_user_by_email(settings, identifier) or storage.get_user_by_username(settings, identifier)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": str(user["id"])}, settings=settings)
    return schemas.TokenResponse(access_token=token)


def _send_reset_email(settings: Settings, to_email: str, token: str):
    """
    Send reset email if SMTP configured; otherwise log to stdout.
    """
    reset_link = f"(reset link token: {token})"
    if settings.smtp_host and settings.smtp_port and settings.smtp_from:
        msg = EmailMessage()
        msg["Subject"] = "Password reset"
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.set_content(f"Use this token to reset your password: {token}\n\nIf you did not request this, ignore it.")
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                if settings.smtp_username and settings.smtp_password:
                    server.starttls()
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
        except Exception:
            # Fallback to stdout if sending fails
            print(f"[reset-email-fallback] To: {to_email} Token: {token}")
    else:
        print(f"[reset-email] To: {to_email} Token: {token}")


@router.post("/forgot_password")
def forgot_password(payload: schemas.ForgotPassword, settings: Settings = Depends(get_settings)):
    identifier = payload.identifier
    user = storage.get_user_by_email(settings, identifier) or storage.get_user_by_username(settings, identifier)
    if not user:
        # Do not reveal existence
        return {"status": "ok"}
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(minutes=settings.reset_token_minutes)).isoformat(timespec="seconds")
    storage.create_reset_token(settings, token, user_id=user["id"], expires_at=expires_at)
    _send_reset_email(settings, user["email"], token)
    return {"status": "ok"}


@router.post("/reset_password")
def reset_password(payload: schemas.ResetPassword, settings: Settings = Depends(get_settings)):
    rec = storage.get_reset_token(settings, payload.token)
    if not rec:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    expires = datetime.fromisoformat(rec["expires_at"])
    if expires < datetime.utcnow():
        storage.delete_reset_token(settings, payload.token)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")
    new_hash = hash_password(payload.new_password)
    storage.update_user_password(settings, rec["user_id"], new_hash)
    storage.delete_reset_token(settings, payload.token)
    return {"status": "password updated"}
