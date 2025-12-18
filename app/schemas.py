"""
Pydantic schemas for requests/responses.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, validator


Task = Literal["classification", "regression"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class JobRequest(BaseModel):
    tickers: List[str]
    start: date
    end: date
    task: Task = "classification"
    horizon: int = 1
    model_kind: str = "random_forest"
    train_window: int = 252 * 2
    test_window: int = 63
    expanding: bool = True
    entry_threshold: float = 0.0
    cost_perc: float = 0.0005
    slippage_perc: float = 0.0005
    data_source: Literal["yfinance"] = "yfinance"

    @validator("tickers")
    def tickers_required(cls, v: List[str]) -> List[str]:
        cleaned = [t.strip().upper() for t in v if t.strip()]
        if not cleaned:
            raise ValueError("At least one ticker is required")
        return cleaned

    @validator("end")
    def end_not_before_start(cls, v: date, values: Dict[str, Any]) -> date:
        start = values.get("start")
        if start and v < start:
            raise ValueError("end date must be >= start date")
        return v


class JobStatus(BaseModel):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime


class JobSummary(BaseModel):
    job_id: str
    status: str
    summary: Dict[str, Any]
    equity_curve: List[Dict[str, Any]]
    trades_head: List[Dict[str, Any]]
