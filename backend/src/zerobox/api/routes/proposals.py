"""Proposal API routes (#17)."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from zerobox.api.dependencies import get_filemanager
from zerobox.classifier.models import Proposal
from zerobox.filemanager.service import FileManagerService

router = APIRouter()


# ------------------------------------------------------------------
# Pydantic models
# ------------------------------------------------------------------


class PatchProposalBody(BaseModel):
    """Request body for updating a proposal."""

    status: Literal["approved", "rejected", "corrected"]
    corrected_name: str | None = None
    corrected_folder: str | None = None


class ProposalResponse(BaseModel):
    """Serialisable proposal representation (Paths as strings)."""

    id: str
    original_path: str
    original_name: str
    proposed_name: str
    proposed_folder: str
    confidence: float
    matched_rule: str | None
    status: str


class ExecuteResultItem(BaseModel):
    """Single item in the execute-batch response."""

    proposal_id: str
    status: str
    target_path: str | None


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _proposal_to_dict(proposal: Proposal) -> dict:
    """Convert a Proposal dataclass to a plain dict with Path fields as strings."""
    d = asdict(proposal)
    d["original_path"] = str(d["original_path"])
    d["proposed_folder"] = str(d["proposed_folder"])
    return d


def _dict_to_proposal(d: dict) -> Proposal:
    """Reconstruct a Proposal dataclass from a stored dict."""
    return Proposal(
        id=d["id"],
        original_path=Path(d["original_path"]),
        original_name=d["original_name"],
        proposed_name=d["proposed_name"],
        proposed_folder=Path(d["proposed_folder"]),
        confidence=d["confidence"],
        matched_rule=d["matched_rule"],
        status=d["status"],
    )


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------


@router.get("", response_model=list[ProposalResponse])
async def list_proposals(
    request: Request,
    status: str | None = None,
) -> list[dict]:
    """Return all current proposals, optionally filtered by status."""
    proposals = list(request.app.state.proposals.values())
    if status is not None:
        proposals = [p for p in proposals if p["status"] == status]
    return proposals


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(request: Request, proposal_id: str) -> dict:
    """Return a single proposal by ID."""
    proposal = request.app.state.proposals.get(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.patch("/{proposal_id}", response_model=ProposalResponse)
async def update_proposal(
    request: Request,
    proposal_id: str,
    body: PatchProposalBody,
) -> dict:
    """Update a proposal's status (approve, reject, or correct)."""
    proposal = request.app.state.proposals.get(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if body.status == "corrected":
        if body.corrected_name is None or body.corrected_folder is None:
            raise HTTPException(
                status_code=422,
                detail="corrected_name and corrected_folder are required "
                "when status is 'corrected'",
            )
        proposal["proposed_name"] = body.corrected_name
        proposal["proposed_folder"] = body.corrected_folder

    proposal["status"] = body.status
    return proposal


@router.post("/execute", response_model=list[ExecuteResultItem])
async def execute_proposals(
    request: Request,
    filemanager: Annotated[FileManagerService, Depends(get_filemanager)],
) -> list[dict]:
    """Execute all approved proposals via the file manager."""
    all_proposals = request.app.state.proposals
    approved = [
        _dict_to_proposal(p)
        for p in all_proposals.values()
        if p["status"] == "approved"
    ]

    results = filemanager.execute_batch(approved)

    response: list[dict] = []
    for proposal, target in results:
        new_status = "approved" if target is not None else "rejected"
        # Update stored proposal status
        if proposal.id in all_proposals:
            all_proposals[proposal.id]["status"] = new_status
        response.append(
            {
                "proposal_id": proposal.id,
                "status": new_status,
                "target_path": str(target) if target is not None else None,
            }
        )

    return response
