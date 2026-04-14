"""FileManager — rename and move operations with conflict handling (FR-01)."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zerobox.audit.service import AuditService
    from zerobox.classifier.models import Proposal
    from zerobox.config import FileManagerConfig

logger = logging.getLogger(__name__)


class FileManagerService:
    """Executes approved classification proposals (rename + move)."""

    def __init__(
        self,
        config: FileManagerConfig,
        audit: AuditService | None = None,
    ) -> None:
        self._config = config
        self._audit = audit

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, proposal: Proposal) -> Path:
        """Execute a single approved proposal and return the final target path.

        Raises:
            ValueError: If the proposal status is not ``"approved"``.
            FileNotFoundError: If the source file does not exist.
        """
        if proposal.status != "approved":
            msg = (
                f"Proposal {proposal.id} has status '{proposal.status}', "
                "expected 'approved'"
            )
            raise ValueError(msg)

        source = Path(proposal.original_path)
        if not source.exists():
            msg = f"Source file does not exist: {source}"
            raise FileNotFoundError(msg)

        target = (
            self._config.output_root / proposal.proposed_folder / proposal.proposed_name
        )
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            target = self._resolve_conflict(target)
            if target is None:
                # skip strategy — file left in place
                if self._audit:
                    self._audit.log(
                        action="file_skipped",
                        source=str(source),
                        target=str(
                            self._config.output_root
                            / proposal.proposed_folder
                            / proposal.proposed_name
                        ),
                        rule_id=proposal.matched_rule,
                    )
                logger.info("Skipped %s (conflict, strategy=skip)", source)
                return source

        shutil.move(str(source), str(target))

        if self._audit:
            self._audit.log(
                action="file_moved",
                source=str(source),
                target=str(target),
                rule_id=proposal.matched_rule,
            )

        logger.info("Moved %s → %s", source, target)
        return target

    def execute_batch(
        self,
        proposals: list[Proposal],
    ) -> list[tuple[Proposal, Path | None]]:
        """Execute multiple proposals, skipping non-approved and continuing on error."""
        results: list[tuple[Proposal, Path | None]] = []

        for proposal in proposals:
            if proposal.status != "approved":
                results.append((proposal, None))
                continue
            try:
                target = self.execute(proposal)
                results.append((proposal, target))
            except Exception:
                logger.exception("Failed to execute proposal %s", proposal.id)
                results.append((proposal, None))

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_conflict(self, target: Path) -> Path | None:
        """Return a non-conflicting path, or ``None`` for the skip strategy."""
        strategy = self._config.conflict_strategy

        if strategy == "overwrite":
            return target

        if strategy == "skip":
            return None

        # strategy == "rename": append _1, _2, … before the extension
        stem = target.stem
        suffix = target.suffix
        parent = target.parent
        counter = 1
        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1
