import sqlite3

from flujo.knowledge.operational_bridge import refresh_operational_bridge


def _rd(path):
    with sqlite3.connect(path) as con:
        con.executescript(
            """
            CREATE TABLE productoras (slug TEXT PRIMARY KEY, nombre TEXT, confirmado INTEGER, aliases TEXT);
            CREATE TABLE venues (id INTEGER PRIMARY KEY, nombre TEXT);
            CREATE TABLE productora_eventos (id INTEGER PRIMARY KEY, productora_slug TEXT, nombre TEXT, fecha TEXT, venue INTEGER, estado TEXT, fuente TEXT);
            INSERT INTO productoras VALUES ('demo-prod','Demo Producer',1,'[]');
            INSERT INTO venues VALUES (4,'Demo Venue');
            INSERT INTO productora_eventos VALUES (9,'demo-prod','Demo Event','2026-09-01',4,'observed','issue://9');
            """
        )


def _fondart(path):
    with sqlite3.connect(path) as con:
        con.executescript(
            """
            CREATE TABLE fondart_applications (application_id TEXT PRIMARY KEY, capture_id TEXT, source_folio TEXT, reported_year INTEGER, area_or_modality TEXT, project_title TEXT, responsible TEXT, amount_raw TEXT, amount_clp INTEGER, selected_status TEXT, partial INTEGER, source_url TEXT, source_text TEXT);
            INSERT INTO fondart_applications VALUES ('fa-1','cap-1','folio-1',2026,'Digital','Demo Garden','Demo Producer','$100',100,'selected',0,'https://example.test/fondart','long source text omitted from projection');
            """
        )


def _intake(path):
    with sqlite3.connect(path) as con:
        con.executescript(
            """
            CREATE TABLE intake_projects (run_id TEXT, project_id TEXT, title TEXT, status TEXT);
            CREATE TABLE fund_targets (run_id TEXT, fund_id TEXT, name TEXT, status TEXT, requirements_json TEXT, evidence_json TEXT);
            CREATE TABLE application_packages (run_id TEXT, application_id TEXT, project_id TEXT, fund_id TEXT, status TEXT, title TEXT, sections_json TEXT, evidence_json TEXT, gaps_json TEXT, outputs_json TEXT);
            CREATE TABLE mak_links (link_id INTEGER, run_id TEXT, project_id TEXT, relation TEXT, mak_path TEXT, artifact_id INTEGER, entity_kind TEXT, confidence TEXT, evidence_json TEXT);
            INSERT INTO intake_projects VALUES ('run-1','project-1','Demo Garden','candidate');
            INSERT INTO fund_targets VALUES ('run-1','fondart','Fondart','active','{}','{}');
            INSERT INTO application_packages VALUES ('run-1','app-1','project-1','fondart','draft','Demo Garden','{}','{}','{}','{}');
            INSERT INTO mak_links VALUES (1,'run-1','project-1','uses_tool','/home/mak/flujo/tools/demo.py',42,'tool','high','{"source":"fixture"}');
            """
        )


def test_bridge_materializes_operational_records_and_exact_links(tmp_path):
    rd = tmp_path / "rd.db"
    fondart = tmp_path / "fondart.sqlite"
    intake = tmp_path / "intake.sqlite"
    target = tmp_path / "master.db"
    _rd(rd)
    _fondart(fondart)
    _intake(intake)

    result = refresh_operational_bridge(target, rd, intake, fondart)

    assert result["source_rows_copied"] == 0
    with sqlite3.connect(target) as con:
        assert con.execute("SELECT COUNT(*) FROM operational_records").fetchone()[0] == 7
        assert con.execute("SELECT COUNT(*) FROM operational_links").fetchone()[0] == 4
        assert con.execute("SELECT COUNT(*) FROM operational_curation_links").fetchone()[0] == 1
        assert con.execute("SELECT venue_name FROM operational_records WHERE record_id='rd_event:9'").fetchone()[0] == 'Demo Venue'
        payload = con.execute("SELECT payload_json FROM operational_records WHERE record_id='fondart_application:fa-1'").fetchone()[0]
        assert 'long source text omitted' not in payload


def test_bridge_refresh_is_idempotent_and_replaces_derived_rows(tmp_path):
    rd = tmp_path / "rd.db"
    fondart = tmp_path / "fondart.sqlite"
    intake = tmp_path / "intake.sqlite"
    target = tmp_path / "master.db"
    _rd(rd)
    _fondart(fondart)
    _intake(intake)
    refresh_operational_bridge(target, rd, intake, fondart)
    refresh_operational_bridge(target, rd, intake, fondart)
    with sqlite3.connect(target) as con:
        assert con.execute("SELECT COUNT(*) FROM operational_records").fetchone()[0] == 7
        assert con.execute("SELECT COUNT(*) FROM operational_runs").fetchone()[0] == 1
