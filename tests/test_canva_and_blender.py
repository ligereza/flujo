import os
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from flujo.export.canva import upload_to_canva

def test_canva_upload_missing_token(tmp_path, monkeypatch):
    monkeypatch.delenv("CANVA_API_TOKEN", raising=False)
    dummy_file = tmp_path / "dummy.png"
    dummy_file.write_bytes(b"dummy")
    
    res = upload_to_canva(dummy_file, "dummy.png")
    assert res["ok"] is False
    assert "CANVA_API_TOKEN" in res["error"]

def test_canva_upload_success(tmp_path, monkeypatch):
    monkeypatch.setenv("CANVA_API_TOKEN", "mock_canva_token_abc123")
    dummy_file = tmp_path / "dummy.png"
    dummy_file.write_bytes(b"dummy")
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "asset_canva_xyz987"}
    
    import requests
    monkeypatch.setattr(requests, "post", lambda url, headers, data: mock_response)
    
    res = upload_to_canva(dummy_file, "dummy.png")
    assert res["ok"] is True
    assert res["data"]["id"] == "asset_canva_xyz987"
