"""
Auth routes: signup/login.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from .config import Settings, get_settings
from . import schemas, storage
from .security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.TokenResponse)
def signup(payload: schemas.UserCreate, settings: Settings = Depends(get_settings)):
    existing = storage.get_user_by_email(settings, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    password_hash = hash_password(payload.password)
    user_id = storage.create_user(settings, payload.email, password_hash)
    token = create_access_token({"sub": str(user_id)}, settings=settings)
    return schemas.TokenResponse(access_token=token)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.UserLogin, settings: Settings = Depends(get_settings)):
    user = storage.get_user_by_email(settings, payload.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": str(user["id"])}, settings=settings)
    return schemas.TokenResponse(access_token=token)
