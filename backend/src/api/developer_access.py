"""Public developer access-request API."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.db import get_database_manager
from src.services.developer_access import developer_access_service


router = APIRouter(prefix="/api/developer-access", tags=["developer-access"])

AllowedSurface = Literal["api", "cli", "python_sdk", "typescript_sdk", "mcp"]
AccessLevel = Literal["read", "write", "custom"]


class DeveloperAccessRequestCreate(BaseModel):
    requester_name: str = Field(..., min_length=2, max_length=255)
    requester_email: str = Field(..., min_length=5, max_length=320)
    organization: str | None = Field(default=None, max_length=255)
    use_case: str = Field(..., min_length=20, max_length=5000)
    requested_surfaces: list[AllowedSurface] = Field(..., min_length=1)
    requested_access_level: AccessLevel = "read"
    requested_ips: list[str] = Field(default_factory=list, max_length=20)
    expected_rpm: int | None = Field(default=None, ge=1, le=100000)


class DeveloperAccessRequestResponse(BaseModel):
    id: str
    status: str
    requester_name: str
    requester_email: str
    requested_access_level: str
    requested_surfaces: list[str]
    requested_ips: list[str]
    expected_rpm: int | None = None
    created_at: str
    message: str


@router.post("/requests", response_model=DeveloperAccessRequestResponse, status_code=201)
async def create_developer_access_request(
    body: DeveloperAccessRequestCreate,
    request: Request,
):
    manager = get_database_manager()
    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="Developer access service unavailable",
        )

    async with manager.session() as session:
        record = await developer_access_service.create_request(
            session,
            requester_name=body.requester_name.strip(),
            requester_email=body.requester_email.strip().lower(),
            organization=body.organization.strip() if body.organization else None,
            use_case=body.use_case.strip(),
            requested_surfaces=list(body.requested_surfaces),
            requested_access_level=body.requested_access_level,
            requested_ips=[item.strip() for item in body.requested_ips if item.strip()],
            expected_rpm=body.expected_rpm,
            request_ip=getattr(request.state, "client_ip", None),
        )

    return DeveloperAccessRequestResponse(
        **{
            key: record[key]
            for key in (
                "id",
                "status",
                "requester_name",
                "requester_email",
                "requested_access_level",
                "requested_surfaces",
                "requested_ips",
                "expected_rpm",
                "created_at",
            )
        },
        message=(
            "Developer access request submitted. Approval is manual and the owner "
            "will review the requested access level and IP allowlist."
        ),
    )
