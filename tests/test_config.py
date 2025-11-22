import importlib
import os

import pytest


def _load_settings():
    settings_module = importlib.import_module("mlit_mcp.settings")
    importlib.reload(settings_module)
    return settings_module.Settings()


def test_settings_require_api_key(monkeypatch):
    monkeypatch.delenv("MLIT_API_KEY", raising=False)
    with pytest.raises(Exception):
        _load_settings()


def test_settings_use_default_base_url(monkeypatch):
    monkeypatch.setenv("MLIT_API_KEY", "dummy-key")
    monkeypatch.delenv("MLIT_BASE_URL", raising=False)
    settings_module = importlib.import_module("mlit_mcp.settings")
    importlib.reload(settings_module)
    settings = settings_module.Settings()
    assert settings.base_url == "https://www.reinfolib.mlit.go.jp/ex-api/external/"

