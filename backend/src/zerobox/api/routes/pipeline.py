"""Pipeline API routes (#16)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from zerobox.api.dependencies import get_pipeline
from zerobox.classifier.models import Proposal
from zerobox.pipeline.service import PipelineService

router = APIRouter()


# ------------------------------------------------------------------
# Response models
# ------------------------------------------------------------------


class ProposalSchema(BaseModel):
    """Serialized representation of a classifier Proposal."""

    id: str
    original_path: str
    original_name: str
    proposed_name: str
    proposed_folder: str
    confidence: float
    matched_rule: str | None
    status: Literal["pending", "approved", "rejected", "corrected"]


class RunResponse(BaseModel):
    """Response for POST /pipeline/run."""

    status: str
    proposals: list[ProposalSchema]


class ExecutionResult(BaseModel):
    """Single result entry for run-and-execute."""

    proposal: ProposalSchema
    target_path: str | None


class RunAndExecuteResponse(BaseModel):
    """Response for POST /pipeline/run-and-execute."""

    status: str
    results: list[ExecutionResult]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _serialize_proposal(proposal: Proposal) -> ProposalSchema:
    """Convert a Proposal dataclass to its Pydantic response schema."""
    return ProposalSchema(
        id=proposal.id,
        original_path=str(proposal.original_path),
        original_name=proposal.original_name,
        proposed_name=proposal.proposed_name,
        proposed_folder=str(proposal.proposed_folder),
        confidence=proposal.confidence,
        matched_rule=proposal.matched_rule,
        status=proposal.status,
    )


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------


@router.post("/run", response_model=RunResponse)
async def run_pipeline(
    pipeline: PipelineService = Depends(get_pipeline),
) -> RunResponse:
    """Run the processing pipeline up to the review point.

    Discovers files, runs OCR, classifies documents, and returns
    a list of pending proposals for user review.
    """
    proposals = await pipeline.run()
    return RunResponse(
        status="completed",
        proposals=[_serialize_proposal(p) for p in proposals],
    )


@router.post("/run-and-execute", response_model=RunAndExecuteResponse)
async def run_and_execute_pipeline(
    auto_approve: bool = Query(default=False),
    pipeline: PipelineService = Depends(get_pipeline),
) -> RunAndExecuteResponse:
    """Run the full pipeline and execute file operations.

    When *auto_approve* is ``True``, every proposal is automatically
    approved before execution.
    """
    results = await pipeline.run_and_execute(auto_approve=auto_approve)
    return RunAndExecuteResponse(
        status="completed",
        results=[
            ExecutionResult(
                proposal=_serialize_proposal(proposal),
                target_path=str(target_path) if target_path is not None else None,
            )
            for proposal, target_path in results
        ],
    )
