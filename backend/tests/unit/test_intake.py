"""Unit tests for the Intake module (T-05)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from zerobox.config import IntakeConfig
from zerobox.intake.models import IntakeFile
from zerobox.intake.service import IntakeService


def _make_config(input_folder: Path, file_types: list[str] | None = None) -> IntakeConfig:
    """Helper to create an IntakeConfig with a given input folder."""
    kwargs: dict = {"input_folder": input_folder}
    if file_types is not None:
        kwargs["file_types"] = file_types
    return IntakeConfig(**kwargs)


class TestIntakeService:
    """Tests for IntakeService.scan()."""

    def test_scan_matching_files(self, tmp_path: Path) -> None:
        """Scan returns IntakeFile objects for supported file types."""
        (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4 fake")
        (tmp_path / "photo.png").write_bytes(b"\x89PNG fake")

        config = _make_config(tmp_path)
        results = IntakeService(config).scan()

        assert len(results) == 2
        names = [r.path.name for r in results]
        assert "doc.pdf" in names
        assert "photo.png" in names

    def test_scan_filters_unsupported_types(self, tmp_path: Path) -> None:
        """Files with unsupported extensions are excluded."""
        (tmp_path / "report.pdf").write_bytes(b"pdf content")
        (tmp_path / "letter.docx").write_bytes(b"docx content")
        (tmp_path / "notes.txt").write_bytes(b"text content")

        config = _make_config(tmp_path)
        results = IntakeService(config).scan()

        assert len(results) == 1
        assert results[0].path.name == "report.pdf"

    def test_scan_case_insensitive_extensions(self, tmp_path: Path) -> None:
        """Extension matching is case-insensitive (.PDF, .Pdf, .pdf all match)."""
        (tmp_path / "upper.PDF").write_bytes(b"data")
        (tmp_path / "mixed.Pdf").write_bytes(b"data")
        (tmp_path / "lower.pdf").write_bytes(b"data")

        config = _make_config(tmp_path)
        results = IntakeService(config).scan()

        assert len(results) == 3

    def test_scan_empty_folder(self, tmp_path: Path) -> None:
        """An empty folder returns an empty list."""
        config = _make_config(tmp_path)
        results = IntakeService(config).scan()

        assert results == []

    def test_scan_nonexistent_folder_raises(self, tmp_path: Path) -> None:
        """A non-existent input folder raises FileNotFoundError."""
        missing = tmp_path / "does_not_exist"
        config = _make_config(missing)

        with pytest.raises(FileNotFoundError, match="does not exist"):
            IntakeService(config).scan()

    def test_scan_skips_subdirectories(self, tmp_path: Path) -> None:
        """Subdirectories inside the input folder are ignored."""
        (tmp_path / "valid.pdf").write_bytes(b"pdf")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.pdf").write_bytes(b"nested pdf")

        config = _make_config(tmp_path)
        results = IntakeService(config).scan()

        assert len(results) == 1
        assert results[0].path.name == "valid.pdf"

    def test_intake_file_fields_populated(self, tmp_path: Path) -> None:
        """IntakeFile fields are correctly populated from file metadata."""
        content = b"hello world 12345"
        f = tmp_path / "test.pdf"
        f.write_bytes(content)

        config = _make_config(tmp_path)
        results = IntakeService(config).scan()

        assert len(results) == 1
        sf = results[0]
        assert sf.path == f.resolve()
        assert sf.file_type == ".pdf"
        assert sf.size_bytes == len(content)
        assert isinstance(sf.modified_at, datetime)

    def test_scan_sorted_by_filename(self, tmp_path: Path) -> None:
        """Results are sorted by filename for deterministic output."""
        (tmp_path / "charlie.pdf").write_bytes(b"c")
        (tmp_path / "alpha.pdf").write_bytes(b"a")
        (tmp_path / "bravo.png").write_bytes(b"b")

        config = _make_config(tmp_path)
        results = IntakeService(config).scan()

        names = [r.path.name for r in results]
        assert names == ["alpha.pdf", "bravo.png", "charlie.pdf"]

    def test_scan_with_audit_service(self, tmp_path: Path) -> None:
        """When an audit service is provided, each file is logged."""
        (tmp_path / "a.pdf").write_bytes(b"pdf")
        (tmp_path / "b.png").write_bytes(b"png")

        audit = MagicMock()
        config = _make_config(tmp_path)
        results = IntakeService(config, audit=audit).scan()

        assert len(results) == 2
        assert audit.log.call_count == 2
        for call in audit.log.call_args_list:
            assert call.kwargs["action"] == "intake_discovered"
            assert "size_bytes" in call.kwargs["details"]
            assert "file_type" in call.kwargs["details"]

    def test_scan_without_audit_service(self, tmp_path: Path) -> None:
        """Scanning works fine without an audit service (None by default)."""
        (tmp_path / "file.pdf").write_bytes(b"data")

        config = _make_config(tmp_path)
        results = IntakeService(config).scan()

        assert len(results) == 1

    def test_scan_custom_file_types(self, tmp_path: Path) -> None:
        """Custom file_types config is respected."""
        (tmp_path / "image.bmp").write_bytes(b"bmp")
        (tmp_path / "doc.pdf").write_bytes(b"pdf")

        config = _make_config(tmp_path, file_types=[".bmp"])
        results = IntakeService(config).scan()

        assert len(results) == 1
        assert results[0].path.name == "image.bmp"
