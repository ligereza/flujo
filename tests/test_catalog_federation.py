import sqlite3

from flujo.knowledge.catalog_federation import federate, inspect_database


def _source(path):
    with sqlite3.connect(path) as con:
        con.executescript(
            """
            CREATE TABLE fondart_applications (id INTEGER PRIMARY KEY, project_title TEXT);
            CREATE TABLE deadlines (id INTEGER PRIMARY KEY, due_at TEXT);
            INSERT INTO fondart_applications(project_title) VALUES ('Demo project');
            INSERT INTO deadlines(due_at) VALUES ('2026-10-01');
            """
        )


def test_inspection_is_structural_and_classifies_tables(tmp_path):
    source = tmp_path / "fondart.sqlite"
    _source(source)

    inspected = inspect_database(source)

    assert inspected.source_kind == "funding_corpus"
    assert inspected.table_count == 2
    assert inspected.row_count == 2
    by_name = {table["name"]: table for table in inspected.tables}
    assert by_name["fondart_applications"]["semantic_kind"] == "funding"
    assert by_name["deadlines"]["semantic_kind"] == "calendar"


def test_federation_copies_no_source_rows_and_is_repeatable(tmp_path):
    source = tmp_path / "portable-ssd-index.sqlite"
    target = tmp_path / "master.sqlite"
    _source(source)

    inspected = inspect_database(source)
    first = federate([inspected], target)
    second = federate([inspect_database(source)], target)

    assert first["source_rows_copied"] == 0
    assert second["sources"] == 1
    with sqlite3.connect(target) as con:
        assert con.execute("SELECT COUNT(*) FROM catalog_sources").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM catalog_tables").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM catalog_links").fetchone()[0] == 2


def test_refresh_replaces_schema_metadata_without_orphans(tmp_path):
    source = tmp_path / "fondart.sqlite"
    target = tmp_path / "master.sqlite"
    _source(source)
    federate([inspect_database(source)], target)
    with sqlite3.connect(source) as con:
        con.execute("CREATE TABLE repositories (id INTEGER PRIMARY KEY, url TEXT)")
    federate([inspect_database(source)], target)

    with sqlite3.connect(target) as con:
        assert con.execute("SELECT COUNT(*) FROM catalog_sources").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM catalog_tables").fetchone()[0] == 3
        assert con.execute("SELECT COUNT(*) FROM catalog_tables WHERE source_id NOT IN (SELECT source_id FROM catalog_sources)").fetchone()[0] == 0
