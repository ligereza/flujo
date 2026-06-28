import os
import shutil
from pathlib import Path
from flujo.paths import datadrops_dir
from flujo.web.hub import scan_incoming_datadrops, HubRequestHandler

def test_datadrop_scan_incoming(tmp_path, monkeypatch):
    monkeypatch.setenv("FLUJO_WORKSPACE_ROOT", str(tmp_path))
    dd = datadrops_dir()
    incoming = dd / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    handler = HubRequestHandler.__new__(HubRequestHandler)
    handler.root = tmp_path
    listed_init = handler._list_datadrops()
    assert listed_init["pending_incoming"] == 0
    assert len(listed_init["datadrops"]) == 0
    mock_image = incoming / "test_flyer_rave.jpg"
    mock_image.write_bytes(b"dummy image bytes")
    listed_pending = handler._list_datadrops()
    assert listed_pending["pending_incoming"] == 1
    res = scan_incoming_datadrops()
    assert res["ok"] is True
    assert res["processed"] == 1
    assert "test_flyer_rave.jpg" in res["files"]
    listed_post = handler._list_datadrops()
    assert listed_post["pending_incoming"] == 0
    assert len(listed_post["datadrops"]) == 1
    manifest_info = listed_post["datadrops"][0]
    assert manifest_info["original_filename"] == "test_flyer_rave.jpg"
    assert manifest_info["type"] == "flyer"
    assert not mock_image.exists()
