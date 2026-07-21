"""Unit tests for the backend entry point (#146)."""

import sys

from zerobox import __main__ as entry


class TestEnsureWritableStreams:
    def test_noop_when_streams_present(self):
        before_out, before_err = sys.stdout, sys.stderr

        entry.ensure_writable_streams()

        assert sys.stdout is before_out
        assert sys.stderr is before_err

    def test_redirects_none_streams_to_log_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZEROBOX_CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(sys, "stdout", None)
        monkeypatch.setattr(sys, "stderr", None)

        entry.ensure_writable_streams()
        try:
            assert sys.stdout is not None
            assert sys.stderr is not None
            print("frozen sidecar says hi")
            assert "frozen sidecar says hi" in (tmp_path / "zerobox-backend.log").read_text(
                encoding="utf-8"
            )
        finally:
            sys.stdout.close()


class TestMain:
    def test_runs_uvicorn_with_app_object_not_string(self, monkeypatch):
        """Regression for #146: a factory string would hide the app from PyInstaller."""
        calls = {}

        def fake_run(app, **kwargs):
            calls["app"] = app
            calls["kwargs"] = kwargs

        monkeypatch.setattr(entry.uvicorn, "run", fake_run)

        entry.main()

        assert not isinstance(calls["app"], str)
        assert callable(getattr(calls["app"], "__call__", None))  # ASGI app instance
        assert calls["kwargs"]["host"] == "127.0.0.1"
        assert calls["kwargs"]["port"] == 8000
