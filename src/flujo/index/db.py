from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from ..paths import repo_root

def db_path() -> Path:
    p = repo_root() / "data" / "flujo.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def init_db(conn=None):
    close = False
    if conn is None:
        conn = sqlite3.connect(db_path())
        close = True
    conn.execute("""
    CREATE TABLE IF NOT EXISTS flyers (
        id INTEGER PRIMARY KEY,
        project_path TEXT UNIQUE,
        name TEXT,
        shortcode TEXT,
        instagram_url TEXT,
        owner TEXT,
        status TEXT,
        media_type TEXT,
        file_count INTEGER,
        date_utc TEXT,
        updated_at TEXT
    )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shortcode ON flyers(shortcode)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON flyers(status)")
    conn.commit()
    if close:
        conn.close()

def rebuild_index() -> dict:
    from ..paths import flyer_base
    base = flyer_base()
    conn = sqlite3.connect(db_path())
    init_db(conn)
    conn.execute("DELETE FROM flyers")
    n = 0
    if base.exists():
        for proj in base.iterdir():
            if not proj.is_dir(): continue
            mf = proj / "manifest.json"
            if not mf.exists(): continue
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
                ig = data.get("instagram", {}) if isinstance(data.get("instagram"), dict) else {}
                conn.execute("""
                    INSERT INTO flyers (project_path, name, shortcode, instagram_url, owner, status, media_type, file_count, date_utc, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))
                """, (
                    str(proj),
                    data.get("name", proj.name),
                    ig.get("shortcode", ""),
                    ig.get("url", ""),
                    ig.get("owner", ""),
                    data.get("status", ""),
                    ig.get("media_type", ""),
                    ig.get("file_count", 0),
                    ig.get("date_utc", ""),
                ))
                n += 1
            except Exception:
                continue
    conn.commit()
    conn.close()
    return {"indexed": n, "db": str(db_path())}

def list_flyers(status: str | None = None, limit: int = 100):
    conn = sqlite3.connect(db_path())
    init_db(conn)
    conn.row_factory = sqlite3.Row
    if status:
        rows = conn.execute("SELECT * FROM flyers WHERE status = ? ORDER BY date_utc DESC LIMIT ?", (status, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM flyers ORDER BY date_utc DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def find_duplicates():
    conn = sqlite3.connect(db_path())
    init_db(conn)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT shortcode, COUNT(*) as c, GROUP_CONCAT(project_path, '|') as paths
        FROM flyers WHERE shortcode != '' GROUP BY shortcode HAVING c > 1
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
