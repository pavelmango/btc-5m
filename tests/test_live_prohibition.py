"""
Test suite verifying live-path prohibition and strict safety invariants.
"""
import pytest
from config.settings import settings, assert_paper_only
from scripts.verify_no_live import run_audit

def test_live_mode_default_is_false():
    assert settings.LIVE_MODE is False
    assert settings.ENVIRONMENT == "paper"

def test_assert_paper_only_guard():
    # Must succeed when False
    assert_paper_only()

    # Must raise RuntimeError if tampered
    original = settings.LIVE_MODE
    try:
        settings.LIVE_MODE = True
        with pytest.raises(RuntimeError) as exc_info:
            assert_paper_only()
        assert "FATAL SAFETY VIOLATION" in str(exc_info.value)
    finally:
        settings.LIVE_MODE = original

def test_static_codebase_zero_live_paths():
    exit_code = run_audit(".")
    assert exit_code == 0, "Audit failed: live trading paths or credentials found in codebase"
