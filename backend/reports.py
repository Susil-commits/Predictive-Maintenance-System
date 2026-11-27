"""
PostgreSQL-backed Diagnostic Reports router for PMS.

Replaces browser-local report storage so saved diagnostic reports and Cloudinary
links are accessible across sessions, browsers, and administrative consoles.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .auth import require_admin_auth, require_authenticated_user
from .database import get_db
from .models import DiagnosticReportRecord

router = APIRouter(prefix="/reports", tags=["Reports"])


class DiagnosticReportCreate(BaseModel):
    predictionId: str | None = None
    risk: str = Field(..., min_length=1, max_length=16)
    probability: float | None = None
    inputData: dict[str, Any] = Field(default_factory=dict)
    shapFactors: list[dict[str, Any]] = Field(default_factory=list)
    cloudinaryUrl: str | None = None
    userName: str | None = None
    userDesignation: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_diagnostic_report(
    payload: DiagnosticReportCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_authenticated_user),
):
    """Persists a diagnostic evaluation report for the authenticated user."""
    role = str(current_user.get("role", "employee"))
    username = str(current_user.get("sub", "unknown"))
    user_id = str(current_user.get("user_id", username))
    user_name = (payload.userName or "").strip() or ("Administrator" if role == "admin" else username)
    user_desig = (payload.userDesignation or "").strip() or str(
        current_user.get("designation") or ("System Administrator" if role == "admin" else "Maintenance Specialist")
    )

    record = DiagnosticReportRecord(
        report_id=f"report-{uuid.uuid4().hex[:12]}",
        prediction_id=payload.predictionId,
        user_id=user_id,
        username=username,
        user_name=user_name,
        user_designation=user_desig,
        risk=payload.risk.upper(),
        probability=payload.probability,
        input_data=payload.inputData,
        shap_factors=payload.shapFactors,
        cloudinary_url=payload.cloudinaryUrl,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.to_dict()


@router.get("")
def list_diagnostic_reports(
    user_id: str | None = Query(None, description="Optional user_id filter (admin only)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_authenticated_user),
):
    """Lists saved diagnostic reports (all users for admin; self-scoped for employees)."""
    query = db.query(DiagnosticReportRecord)
    if current_user.get("role") == "admin":
        if user_id:
            query = query.filter(DiagnosticReportRecord.user_id == user_id)
    else:
        caller_id = str(current_user.get("user_id", ""))
        query = query.filter(DiagnosticReportRecord.user_id == caller_id)

    rows = query.order_by(desc(DiagnosticReportRecord.saved_at)).limit(limit).all()
    return [r.to_dict() for r in rows]


@router.delete("/{report_id}")
def delete_diagnostic_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_authenticated_user),
):
    """Deletes a persisted diagnostic report (allowed for report owner or admin)."""
    record = db.query(DiagnosticReportRecord).filter(DiagnosticReportRecord.report_id == report_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    record_any: Any = record
    if current_user.get("role") != "admin" and str(record_any.user_id) != str(current_user.get("user_id", "")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this report.")

    db.delete(record)
    db.commit()
    return {"message": f"Report '{report_id}' deleted."}


@router.delete(
    "",
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
def clear_all_diagnostic_reports(
    db: Session = Depends(get_db),
    admin_auth: dict = Depends(require_admin_auth),
):
    """Clears all persisted diagnostic reports. Requires admin authorization."""
    deleted = db.query(DiagnosticReportRecord).delete()
    db.commit()
    return {"message": f"Cleared {deleted} diagnostic reports."}
