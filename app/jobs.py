"""
Job submission and retrieval routes.
"""

from __future__ import annotations

import uuid
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from . import schemas, services, storage
from .config import Settings, get_settings
from .deps import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=Dict[str, str])
def submit_job(
    payload: schemas.JobRequest,
    user=Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    job_id = str(uuid.uuid4())
    storage.create_job(settings, job_id=job_id, user_id=user["id"], request_json=payload.dict())
    try:
        result = services.run_job(payload, max_tickers=settings.max_tickers, max_days=settings.max_days)
        storage.update_job(settings, job_id, status="succeeded", result_json=result)
    except services.JobError as exc:
        storage.update_job(settings, job_id, status="failed", error=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        storage.update_job(settings, job_id, status="failed", error="Internal error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return {"job_id": job_id}


@router.get("", response_model=list[schemas.JobStatus])
def list_jobs(user=Depends(get_current_user), settings: Settings = Depends(get_settings)):
    jobs = []
    for row in storage.list_jobs(settings, user_id=user["id"], limit=20):
        jobs.append(
            schemas.JobStatus(
                id=row["id"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
    return jobs


@router.get("/{job_id}", response_model=schemas.JobSummary)
def job_result(job_id: str, user=Depends(get_current_user), settings: Settings = Depends(get_settings)):
    rec = storage.get_job(settings, job_id)
    if not rec or rec["user_id"] != user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if rec["status"] != "succeeded":
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail=f"Job status: {rec['status']}")
    result = rec["result_json"] or {}
    return schemas.JobSummary(
        job_id=job_id,
        status=rec["status"],
        summary=result.get("summary", {}),
        equity_curve=result.get("equity_curve", []),
        trades_head=result.get("trades_head", []),
    )
