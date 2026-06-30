from __future__ import annotations

import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from flujo.resolume.automator import (
    generate_show_automation,
    parse_smpte_setlist,
    parse_smpte_time,
)


def test_parse_smpte_time_accepts_valid_value() -> None:
    assert parse_smpte_time("01:02:03:24", fps=25) == (1, 2, 3, 24)


@pytest.mark.parametrize(
    ("value", "fps"),
    [("00:00:00:25", 25), ("00:00:00:30", 30)],
)
def test_parse_smpte_time_rejects_frame_out_of_range(value: str, fps: int) -> None:
    with pytest.raises(ValueError, match="fuera de rango"):
        parse_smpte_time(value, fps=fps)


def test_parse_smpte_setlist_from_intake_json_with_two_cues(tmp_path: Path) -> None:
    job = tmp_path / "job_intake"
    job.mkdir()
    payload = {
        "fps": 30,
        "songs": [
            {"name": "Intro", "timecode": "00:00:00:00", "layer": 2, "clip": 5},
            {"tema": "Tema 1", "inicio": "00:01:10:12", "capa": 3, "columna": 6},
        ],
    }
    (job / "intake.json").write_text(json.dumps(payload), encoding="utf-8")

    cues = parse_smpte_setlist(job)

    assert len(cues) == 2
    assert cues[0].title == "Intro"
    assert cues[0].smpte == "00:00:00:00"
    assert cues[0].layer == 2
    assert cues[0].clip == 5
    assert cues[1].title == "Tema 1"
    assert cues[1].smpte == "00:01:10:12"
    assert cues[1].layer == 3
    assert cues[1].clip == 6


def test_parse_smpte_setlist_from_brief_md_with_two_cues_and_defaults(tmp_path: Path) -> None:
    job = tmp_path / "job_brief"
    job.mkdir()
    (job / "brief.md").write_text(
        "\n".join(
            [
                "- 00:00:00:00 Intro apertura",
                "00:02:15:10 | Tema 2 | layer:1 | clip:4",
            ]
        ),
        encoding="utf-8",
    )

    cues = parse_smpte_setlist(job, fps=30)

    assert len(cues) == 2
    assert cues[0].title == "Intro apertura"
    assert cues[0].layer == 1
    assert cues[0].clip == 1
    assert cues[1].title == "Tema 2"
    assert cues[1].layer == 1
    assert cues[1].clip == 4


def test_generate_show_automation_writes_parseable_xml_with_expected_osc_defaults(tmp_path: Path) -> None:
    job = tmp_path / "job_xml"
    job.mkdir()
    (job / "intake.json").write_text(
        json.dumps(
            {
                "setlist": [
                    {"title": "Intro", "start": "00:00:00:00", "layer": 1, "clip": 1},
                    {"title": "Tema 2", "start": "00:00:10:05", "layer": 1, "clip": 2},
                ]
            }
        ),
        encoding="utf-8",
    )

    output = generate_show_automation(job)

    tree = ET.parse(output)
    root = tree.getroot()
    xml_text = output.read_text(encoding="utf-8")

    assert root.tag == "chataigneSession"
    assert root.find("./modules/timecode").attrib["source"] == "smpte"
    assert root.find("./modules/timecode").attrib["fps"] == "30"
    osc_output = root.find("./modules/oscOutput")
    assert osc_output is not None
    assert osc_output.attrib["host"] == "127.0.0.1"
    assert osc_output.attrib["port"] == "7000"
    assert "/composition/layers/1/clips/1/connect" in xml_text
    assert "/composition/layers/1/clips/2/connect" in xml_text
    assert 'value="1"' in xml_text


def test_parse_smpte_setlist_raises_clear_error_when_no_sources_exist(tmp_path: Path) -> None:
    job = tmp_path / "job_empty"
    job.mkdir()

    with pytest.raises(FileNotFoundError, match="intake.json ni brief.md"):
        parse_smpte_setlist(job)
