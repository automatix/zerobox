"""Classifier service — orchestrates LLM provider and rules (FR-03)."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from zerobox.classifier.models import ClassificationContext, Proposal

if TYPE_CHECKING:
    from zerobox.audit.service import AuditService
    from zerobox.classifier.models import UserCorrection
    from zerobox.classifier.providers.base import LLMProvider
    from zerobox.intake.models import IntakeFile
    from zerobox.rules.models import Rule
    from zerobox.rules.service import RuleService

logger = logging.getLogger(__name__)


class ClassifierService:
    """Orchestrates LLM provider and rule engine to produce classification proposals."""

    def __init__(
        self,
        provider: LLMProvider,
        rules: RuleService,
        audit: AuditService | None = None,
    ) -> None:
        self._provider = provider
        self._rules = rules
        self._audit = audit

    async def classify(self, text: str, file: IntakeFile) -> Proposal:
        """Classify a single document and return a proposal.

        Args:
            text: OCR-extracted text from the scanned document.
            file: Metadata about the ingested file.

        Returns:
            A pending proposal with the classification result.
        """
        context = ClassificationContext(
            original_path=file.path,
            original_name=file.path.name,
            file_type=file.file_type,
        )

        matched_rules = self._rules.match_rules(text)
        result = await self._provider.classify(text, matched_rules, context)

        proposal = Proposal(
            id=uuid.uuid4().hex[:12],
            original_path=file.path,
            original_name=file.path.name,
            proposed_name=result.proposed_name,
            proposed_folder=Path(result.proposed_folder),
            confidence=result.confidence,
            matched_rule=result.matched_rule_id,
            status="pending",
        )

        if self._audit is not None:
            self._audit.log(
                action="classified",
                source=str(file.path),
                details={
                    "proposal_id": proposal.id,
                    "proposed_name": proposal.proposed_name,
                    "proposed_folder": str(proposal.proposed_folder),
                    "confidence": proposal.confidence,
                    "matched_rule": proposal.matched_rule,
                },
            )

        return proposal

    async def learn_from_correction(
        self,
        text: str,
        correction: UserCorrection,
        profile_id: str,
    ) -> Rule:
        """Extract a rule from a user correction and add it to a profile.

        Args:
            text: OCR-extracted text from the document.
            correction: The user's correction details.
            profile_id: Which rule profile to add the new rule to.

        Returns:
            The newly created rule.
        """
        rule = await self._provider.extract_rule(text, correction)
        rule.profile_id = profile_id
        self._rules.add_rule(profile_id, rule)

        if self._audit is not None:
            self._audit.log(
                action="rule_learned",
                source=profile_id,
                details={
                    "profile_id": profile_id,
                    "rule_id": rule.id,
                    "correction": (
                        f"{correction.original_proposal_name} -> {correction.corrected_name}"
                    ),
                },
            )

        return rule

    async def classify_batch(
        self,
        text_file_pairs: list[tuple[str, IntakeFile]],
    ) -> list[Proposal]:
        """Classify multiple documents sequentially.

        If a single classification fails, the error is logged and processing
        continues with the remaining files.

        Args:
            text_file_pairs: List of (ocr_text, intake_file) tuples.

        Returns:
            List of proposals for successfully classified files.
        """
        proposals: list[Proposal] = []
        for text, file in text_file_pairs:
            try:
                proposal = await self.classify(text, file)
                proposals.append(proposal)
            except Exception:
                logger.exception("Classification failed for %s", file.path)
        return proposals
