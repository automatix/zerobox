"""Tests for FileManagerService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from zerobox.classifier.models import Proposal
from zerobox.config import FileManagerConfig
from zerobox.filemanager.service import FileManagerService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_proposal(
    tmp_path: Path,
    *,
    status: str = "approved",
    proposed_name: str = "invoice_2024.pdf",
    proposed_folder: str = "invoices",
    matched_rule: str | None = "rule-1",
) -> Proposal:
    src = tmp_path / "inbox" / "scan001.pdf"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("fake-pdf-content")
    return Proposal(
        id="p-1",
        original_path=src,
        original_name=src.name,
        proposed_name=proposed_name,
        proposed_folder=Path(proposed_folder),
        confidence=0.95,
        matched_rule=matched_rule,
        status=status,
    )


def _make_service(
    tmp_path: Path,
    *,
    conflict_strategy: str = "rename",
    audit: MagicMock | None = None,
) -> FileManagerService:
    config = FileManagerConfig(
        output_root=tmp_path / "archive",
        conflict_strategy=conflict_strategy,
    )
    return FileManagerService(config=config, audit=audit)


# ------------------------------------------------------------------
# execute — happy path
# ------------------------------------------------------------------


class TestExecuteHappyPath:
    def test_moves_file_to_correct_target(self, tmp_path: Path) -> None:
        proposal = _make_proposal(tmp_path)
        svc = _make_service(tmp_path)

        result = svc.execute(proposal)

        expected = tmp_path / "archive" / "invoices" / "invoice_2024.pdf"
        assert result == expected
        assert expected.exists()
        assert expected.read_text() == "fake-pdf-content"
        assert not proposal.original_path.exists()

    def test_creates_target_directory_structure(self, tmp_path: Path) -> None:
        proposal = _make_proposal(tmp_path, proposed_folder="a/b/c")
        svc = _make_service(tmp_path)

        result = svc.execute(proposal)

        assert result.parent == tmp_path / "archive" / "a" / "b" / "c"
        assert result.exists()

    def test_returned_path_reflects_actual_location(self, tmp_path: Path) -> None:
        proposal = _make_proposal(tmp_path)
        svc = _make_service(tmp_path)

        result = svc.execute(proposal)

        assert result.exists()
        assert result.read_text() == "fake-pdf-content"


# ------------------------------------------------------------------
# execute — validation
# ------------------------------------------------------------------


class TestExecuteValidation:
    @pytest.mark.parametrize("status", ["pending", "rejected", "corrected"])
    def test_raises_value_error_for_non_approved(
        self, tmp_path: Path, status: str
    ) -> None:
        proposal = _make_proposal(tmp_path, status=status)
        svc = _make_service(tmp_path)

        with pytest.raises(ValueError, match="expected 'approved'"):
            svc.execute(proposal)

    def test_raises_file_not_found_for_missing_source(self, tmp_path: Path) -> None:
        proposal = _make_proposal(tmp_path)
        proposal.original_path.unlink()  # remove the file
        svc = _make_service(tmp_path)

        with pytest.raises(FileNotFoundError):
            svc.execute(proposal)


# ------------------------------------------------------------------
# execute — conflict strategies
# ------------------------------------------------------------------


class TestConflictRename:
    def test_appends_suffix_on_conflict(self, tmp_path: Path) -> None:
        proposal = _make_proposal(tmp_path)
        svc = _make_service(tmp_path, conflict_strategy="rename")

        # Pre-create conflicting file
        target = tmp_path / "archive" / "invoices" / "invoice_2024.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("existing")

        result = svc.execute(proposal)

        expected = tmp_path / "archive" / "invoices" / "invoice_2024_1.pdf"
        assert result == expected
        assert result.exists()
        # Original conflicting file untouched
        assert target.read_text() == "existing"

    def test_increments_suffix_until_unique(self, tmp_path: Path) -> None:
        proposal = _make_proposal(tmp_path)
        svc = _make_service(tmp_path, conflict_strategy="rename")

        parent = tmp_path / "archive" / "invoices"
        parent.mkdir(parents=True, exist_ok=True)
        (parent / "invoice_2024.pdf").write_text("v0")
        (parent / "invoice_2024_1.pdf").write_text("v1")

        result = svc.execute(proposal)

        assert result == parent / "invoice_2024_2.pdf"
        assert result.exists()


class TestConflictOverwrite:
    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        proposal = _make_proposal(tmp_path)
        svc = _make_service(tmp_path, conflict_strategy="overwrite")

        target = tmp_path / "archive" / "invoices" / "invoice_2024.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("old-content")

        result = svc.execute(proposal)

        assert result == target
        assert target.read_text() == "fake-pdf-content"


class TestConflictSkip:
    def test_leaves_file_in_place(self, tmp_path: Path) -> None:
        proposal = _make_proposal(tmp_path)
        svc = _make_service(tmp_path, conflict_strategy="skip")

        target = tmp_path / "archive" / "invoices" / "invoice_2024.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("existing")

        result = svc.execute(proposal)

        # Source file still exists
        assert proposal.original_path.exists()
        # Target file unchanged
        assert target.read_text() == "existing"
        # Returned path is the source (file was not moved)
        assert result == proposal.original_path


# ------------------------------------------------------------------
# execute — audit logging
# ------------------------------------------------------------------


class TestAuditLogging:
    def test_logs_file_moved_action(self, tmp_path: Path) -> None:
        audit = MagicMock()
        proposal = _make_proposal(tmp_path)
        svc = _make_service(tmp_path, audit=audit)

        svc.execute(proposal)

        audit.log.assert_called_once_with(
            action="file_moved",
            source=str(proposal.original_path),
            target=str(tmp_path / "archive" / "invoices" / "invoice_2024.pdf"),
            rule_id="rule-1",
        )

    def test_logs_file_skipped_on_skip_conflict(self, tmp_path: Path) -> None:
        audit = MagicMock()
        proposal = _make_proposal(tmp_path)
        svc = _make_service(tmp_path, conflict_strategy="skip", audit=audit)

        target = tmp_path / "archive" / "invoices" / "invoice_2024.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("existing")

        svc.execute(proposal)

        audit.log.assert_called_once_with(
            action="file_skipped",
            source=str(proposal.original_path),
            target=str(target),
            rule_id="rule-1",
        )

    def test_works_without_audit_service(self, tmp_path: Path) -> None:
        proposal = _make_proposal(tmp_path)
        svc = _make_service(tmp_path, audit=None)

        # Should not raise
        result = svc.execute(proposal)
        assert result.exists()


# ------------------------------------------------------------------
# execute_batch
# ------------------------------------------------------------------


class TestExecuteBatch:
    def test_processes_multiple_proposals(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)

        proposals = []
        for i in range(3):
            src = tmp_path / "inbox" / f"scan{i}.pdf"
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_text(f"content-{i}")
            proposals.append(
                Proposal(
                    id=f"p-{i}",
                    original_path=src,
                    original_name=src.name,
                    proposed_name=f"doc_{i}.pdf",
                    proposed_folder=Path("docs"),
                    confidence=0.9,
                    matched_rule=None,
                    status="approved",
                )
            )

        results = svc.execute_batch(proposals)

        assert len(results) == 3
        for proposal, target in results:
            assert target is not None
            assert target.exists()

    def test_skips_non_approved_proposals(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)

        src = tmp_path / "inbox" / "scan.pdf"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("content")

        proposals = [
            Proposal(
                id="p-pending",
                original_path=src,
                original_name=src.name,
                proposed_name="doc.pdf",
                proposed_folder=Path("docs"),
                confidence=0.9,
                matched_rule=None,
                status="pending",
            ),
        ]

        results = svc.execute_batch(proposals)

        assert len(results) == 1
        assert results[0][1] is None
        # Source untouched
        assert src.exists()

    def test_continues_on_failure(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)

        # First proposal: source doesn't exist (will fail)
        bad = Proposal(
            id="p-bad",
            original_path=tmp_path / "nonexistent.pdf",
            original_name="nonexistent.pdf",
            proposed_name="bad.pdf",
            proposed_folder=Path("docs"),
            confidence=0.9,
            matched_rule=None,
            status="approved",
        )

        # Second proposal: valid
        src = tmp_path / "inbox" / "good.pdf"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("good-content")
        good = Proposal(
            id="p-good",
            original_path=src,
            original_name=src.name,
            proposed_name="good.pdf",
            proposed_folder=Path("docs"),
            confidence=0.9,
            matched_rule=None,
            status="approved",
        )

        results = svc.execute_batch([bad, good])

        assert len(results) == 2
        assert results[0][1] is None  # failed
        assert results[1][1] is not None  # succeeded
        assert results[1][1].exists()
