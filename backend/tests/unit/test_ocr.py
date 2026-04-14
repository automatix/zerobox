"""Unit tests for the OCR processing module."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zerobox.config import OcrConfig
from zerobox.ocr.models import OcrResult
from zerobox.ocr.service import OcrService
from zerobox.scanner.models import ScannedFile


@pytest.fixture
def ocr_config() -> OcrConfig:
    return OcrConfig(language="deu+eng", deskew=True, optimize=1)


@pytest.fixture
def scanned_file(tmp_path: Path) -> ScannedFile:
    pdf = tmp_path / "input" / "scan.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4 fake content")
    return ScannedFile(
        path=pdf,
        file_type=".pdf",
        size_bytes=pdf.stat().st_size,
        modified_at=datetime.now(),
    )


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    return tmp_path / "output"


@pytest.fixture
def ocr_service(ocr_config: OcrConfig, output_dir: Path) -> OcrService:
    return OcrService(config=ocr_config, output_dir=output_dir)


class TestOcrResult:
    def test_defaults(self, tmp_path: Path) -> None:
        result = OcrResult(
            source_path=tmp_path / "in.pdf",
            output_path=tmp_path / "out.pdf",
            text="hello",
            language="deu+eng",
            pages=1,
            success=True,
        )
        assert result.error is None

    def test_error_field(self, tmp_path: Path) -> None:
        result = OcrResult(
            source_path=tmp_path / "in.pdf",
            output_path=tmp_path / "out.pdf",
            text="",
            language="deu+eng",
            pages=0,
            success=False,
            error="something broke",
        )
        assert result.success is False
        assert result.error == "something broke"


class TestOcrService:
    @pytest.mark.asyncio
    async def test_successful_processing(
        self,
        ocr_service: OcrService,
        scanned_file: ScannedFile,
        output_dir: Path,
    ) -> None:
        sidecar_path = output_dir / "scan.txt"

        def fake_ocr(**kwargs):
            # Create the output PDF and sidecar file as ocrmypdf would.
            output_dir.mkdir(parents=True, exist_ok=True)
            kwargs["output_file"].write_bytes(b"%PDF-1.4 searchable")
            sidecar_path.write_text("Extracted text content", encoding="utf-8")
            return 0

        with patch("zerobox.ocr.service.ocrmypdf.ocr", side_effect=fake_ocr):
            result = await ocr_service.process(scanned_file)

        assert result.success is True
        assert result.text == "Extracted text content"
        assert result.output_path == output_dir / "scan.pdf"
        assert result.source_path == scanned_file.path
        assert result.language == "deu+eng"
        assert result.pages >= 1
        assert result.error is None

    @pytest.mark.asyncio
    async def test_failed_processing(
        self,
        ocr_service: OcrService,
        scanned_file: ScannedFile,
        output_dir: Path,
    ) -> None:
        with patch(
            "zerobox.ocr.service.ocrmypdf.ocr",
            side_effect=RuntimeError("OCR engine crashed"),
        ):
            result = await ocr_service.process(scanned_file)

        assert result.success is False
        assert result.error == "OCR engine crashed"
        assert result.text == ""
        assert result.pages == 0

    @pytest.mark.asyncio
    async def test_output_path_construction(
        self,
        ocr_service: OcrService,
        output_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Output PDF uses the input file stem with .pdf extension."""
        image = tmp_path / "photo.tiff"
        image.write_bytes(b"fake tiff")
        file = ScannedFile(
            path=image,
            file_type=".tiff",
            size_bytes=9,
            modified_at=datetime.now(),
        )

        def fake_ocr(**kwargs):
            output_dir.mkdir(parents=True, exist_ok=True)
            kwargs["output_file"].write_bytes(b"%PDF")
            (output_dir / "photo.txt").write_text("text", encoding="utf-8")
            return 0

        with patch("zerobox.ocr.service.ocrmypdf.ocr", side_effect=fake_ocr):
            result = await ocr_service.process(file)

        assert result.output_path == output_dir / "photo.pdf"

    @pytest.mark.asyncio
    async def test_config_values_passed_to_ocrmypdf(
        self,
        output_dir: Path,
        scanned_file: ScannedFile,
    ) -> None:
        config = OcrConfig(language="fra", deskew=False, optimize=2)
        service = OcrService(config=config, output_dir=output_dir)

        captured_kwargs: dict = {}

        def fake_ocr(**kwargs):
            captured_kwargs.update(kwargs)
            output_dir.mkdir(parents=True, exist_ok=True)
            kwargs["output_file"].write_bytes(b"%PDF")
            (output_dir / "scan.txt").write_text("texte", encoding="utf-8")
            return 0

        with patch("zerobox.ocr.service.ocrmypdf.ocr", side_effect=fake_ocr):
            await service.process(scanned_file)

        assert captured_kwargs["language"] == "fra"
        assert captured_kwargs["deskew"] is False
        assert captured_kwargs["optimize"] == 2

    @pytest.mark.asyncio
    async def test_batch_processing_mixed_results(
        self,
        ocr_service: OcrService,
        output_dir: Path,
        tmp_path: Path,
    ) -> None:
        good_file = tmp_path / "good.pdf"
        good_file.write_bytes(b"%PDF")
        bad_file = tmp_path / "bad.pdf"
        bad_file.write_bytes(b"%PDF")

        files = [
            ScannedFile(
                path=good_file, file_type=".pdf", size_bytes=4, modified_at=datetime.now()
            ),
            ScannedFile(
                path=bad_file, file_type=".pdf", size_bytes=4, modified_at=datetime.now()
            ),
        ]

        call_count = 0

        def fake_ocr(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                output_dir.mkdir(parents=True, exist_ok=True)
                kwargs["output_file"].write_bytes(b"%PDF")
                (output_dir / "good.txt").write_text("good text", encoding="utf-8")
                return 0
            raise RuntimeError("corrupt file")

        with patch("zerobox.ocr.service.ocrmypdf.ocr", side_effect=fake_ocr):
            results = await ocr_service.process_batch(files)

        assert len(results) == 2
        assert results[0].success is True
        assert results[0].text == "good text"
        assert results[1].success is False
        assert results[1].error == "corrupt file"

    @pytest.mark.asyncio
    async def test_audit_logging_on_success(
        self,
        ocr_config: OcrConfig,
        output_dir: Path,
        scanned_file: ScannedFile,
    ) -> None:
        mock_audit = MagicMock()
        service = OcrService(config=ocr_config, output_dir=output_dir, audit=mock_audit)

        def fake_ocr(**kwargs):
            output_dir.mkdir(parents=True, exist_ok=True)
            kwargs["output_file"].write_bytes(b"%PDF")
            (output_dir / "scan.txt").write_text("text", encoding="utf-8")
            return 0

        with patch("zerobox.ocr.service.ocrmypdf.ocr", side_effect=fake_ocr):
            await service.process(scanned_file)

        mock_audit.log.assert_called_once()
        call_kwargs = mock_audit.log.call_args
        assert call_kwargs.kwargs["action"] == "ocr_processed"
        assert call_kwargs.kwargs["source"] == str(scanned_file.path)
        assert call_kwargs.kwargs["target"] == str(output_dir / "scan.pdf")
        assert "language" in call_kwargs.kwargs["details"]

    @pytest.mark.asyncio
    async def test_audit_not_called_on_failure(
        self,
        ocr_config: OcrConfig,
        output_dir: Path,
        scanned_file: ScannedFile,
    ) -> None:
        mock_audit = MagicMock()
        service = OcrService(config=ocr_config, output_dir=output_dir, audit=mock_audit)

        with patch(
            "zerobox.ocr.service.ocrmypdf.ocr",
            side_effect=RuntimeError("fail"),
        ):
            await service.process(scanned_file)

        mock_audit.log.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_audit_service_does_not_crash(
        self,
        ocr_service: OcrService,
        scanned_file: ScannedFile,
        output_dir: Path,
    ) -> None:
        """Processing works fine when no audit service is provided."""

        def fake_ocr(**kwargs):
            output_dir.mkdir(parents=True, exist_ok=True)
            kwargs["output_file"].write_bytes(b"%PDF")
            (output_dir / "scan.txt").write_text("text", encoding="utf-8")
            return 0

        with patch("zerobox.ocr.service.ocrmypdf.ocr", side_effect=fake_ocr):
            result = await ocr_service.process(scanned_file)

        assert result.success is True
