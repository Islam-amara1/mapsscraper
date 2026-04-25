"""Database module for CRM."""
import sqlite3
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "crm.db"
DEFAULT_RESULTS_DIR = Path(__file__).parent.parent / "data" / "results"


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def get_connection() -> sqlite3.Connection:
    """Get database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS imports (
            source_file TEXT PRIMARY KEY,
            file_mtime REAL,
            row_count INTEGER,
            imported_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_name TEXT,
            contact_role TEXT,
            clinic_name TEXT,
            clinic_size TEXT,
            call_outcome TEXT CHECK(
                call_outcome IN ('interested', 'callback', 'not_interested')
                OR call_outcome IS NULL
                OR call_outcome = ''
            ),
            next_action TEXT,
            next_action_date TEXT,
            notes TEXT,
            source_file TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _needs_leads_migration(conn: sqlite3.Connection) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='leads' LIMIT 1"
    )
    row = cursor.fetchone()
    if not row or not row["sql"]:
        return False
    sql = row["sql"]
    # Old schema rejected blank outcomes due to strict CHECK.
    return "CHECK(call_outcome IN ('interested', 'callback', 'not_interested'))" in sql


def _migrate_leads_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_name TEXT,
            contact_role TEXT,
            clinic_name TEXT,
            clinic_size TEXT,
            call_outcome TEXT CHECK(
                call_outcome IN ('interested', 'callback', 'not_interested')
                OR call_outcome IS NULL
                OR call_outcome = ''
            ),
            next_action TEXT,
            next_action_date TEXT,
            notes TEXT,
            source_file TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Best-effort copy (skip rows that violate constraints).
    cursor.execute("""
        INSERT INTO leads_v2 (
            id, contact_name, contact_role, clinic_name, clinic_size,
            call_outcome, next_action, next_action_date, notes, source_file,
            created_at, updated_at
        )
        SELECT
            id, contact_name, contact_role, clinic_name, clinic_size,
            COALESCE(call_outcome, ''),
            next_action, next_action_date, notes, source_file,
            created_at, updated_at
        FROM leads
    """)
    cursor.execute("DROP TABLE leads")
    cursor.execute("ALTER TABLE leads_v2 RENAME TO leads")


def init_db() -> None:
    """Initialize CRM tables."""
    conn = get_connection()
    if _needs_leads_migration(conn):
        _migrate_leads_table(conn)
    _ensure_tables(conn)
    conn.commit()
    conn.close()


def add_lead(
    contact_name: str = "",
    contact_role: str = "",
    clinic_name: str = "",
    clinic_size: str = "",
    call_outcome: str = "",
    next_action: str = "",
    next_action_date: str = "",
    notes: str = "",
    source_file: str = "",
) -> int:
    """Add new lead."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO leads (
            contact_name, contact_role, clinic_name, clinic_size,
            call_outcome, next_action, next_action_date, notes, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (contact_name, contact_role, clinic_name, clinic_size,
         call_outcome or "", next_action, next_action_date or "", notes, source_file),
    )
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lead_id


def update_lead(
    lead_id: int,
    contact_name: str = None,
    contact_role: str = None,
    clinic_name: str = None,
    clinic_size: str = None,
    call_outcome: str = None,
    next_action: str = None,
    next_action_date: str = None,
    notes: str = None,
) -> None:
    """Update existing lead."""
    conn = get_connection()
    cursor = conn.cursor()
    fields = []
    values = []
    for field, value in [
        ("contact_name", contact_name),
        ("contact_role", contact_role),
        ("clinic_name", clinic_name),
        ("clinic_size", clinic_size),
        ("call_outcome", call_outcome),
        ("next_action", next_action),
        ("next_action_date", next_action_date),
        ("notes", notes),
    ]:
        if value is not None:
            fields.append(f"{field} = ?")
            if field in {"call_outcome"}:
                values.append(value or "")
            elif field in {"next_action_date"}:
                values.append(value or "")
            else:
                values.append(value)
    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(lead_id)
    cursor.execute(f"UPDATE leads SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_lead(lead_id: int) -> None:
    """Delete lead."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()


def get_all_leads() -> list:
    """Get all leads."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_leads_by_outcome(outcome: str) -> list:
    """Get leads filtered by outcome."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM leads WHERE call_outcome = ? ORDER BY created_at DESC",
        (outcome,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_upcoming_callbacks() -> list:
    """Get leads with upcoming callbacks."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM leads
        WHERE call_outcome = 'callback'
        AND next_action_date IS NOT NULL
        AND next_action_date != ''
        ORDER BY next_action_date ASC
        """,
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def is_imported(source_file: str) -> bool:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM imports WHERE source_file = ? LIMIT 1", (source_file,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def delete_leads_by_source(source_file: str) -> int:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leads WHERE source_file = ?", (source_file,))
    deleted = cursor.rowcount or 0
    conn.commit()
    conn.close()
    return deleted


def mark_imported(source_file: str, file_mtime: Optional[float], row_count: int) -> None:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO imports (source_file, file_mtime, row_count, imported_at)
        VALUES (?, ?, ?, ?)
        """,
        (source_file, file_mtime, row_count, _utc_now_iso()),
    )
    conn.commit()
    conn.close()


def _normalize_row_keys(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for k, v in row.items():
        if k is None:
            continue
        key = str(k).lstrip("\ufeff").strip()
        normalized[key] = v
    return normalized


def import_from_scraper_csv(csv_path: str, limit: Optional[int] = None, force: bool = False) -> int:
    """Import leads from scraper CSV output (idempotent by source_file)."""
    import csv

    init_db()
    csv_file = Path(csv_path)
    source_file = str(csv_file)
    if is_imported(source_file) and not force:
        return 0
    if force:
        delete_leads_by_source(source_file)

    count = 0
    with open(csv_file, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = _normalize_row_keys(row)
            clinic_name = (
                (row.get("clinic_name") or "").strip()
                or (row.get("name") or "").strip()
                or (row.get("business_name") or "").strip()
            )
            contact_name = (row.get("contact_name") or "").strip()
            contact_role = (row.get("contact_role") or "").strip()
            clinic_size = (row.get("clinic_size") or "").strip()
            call_outcome = (row.get("call_outcome") or "").strip()
            next_action = (row.get("next_action") or "").strip()
            next_action_date = (row.get("next_action_date") or "").strip()

            address = (row.get("address") or "").strip()
            phone = (row.get("phone") or "").strip()
            website = (row.get("website") or "").strip()
            maps_url = (row.get("google_maps_url") or "").strip()
            category = (row.get("category") or "").strip()

            notes = (row.get("notes") or "").strip()
            if not notes:
                parts = []
                if address:
                    parts.append(f"Address: {address}")
                if phone:
                    parts.append(f"Phone: {phone}")
                if website:
                    parts.append(f"Website: {website}")
                if maps_url:
                    parts.append(f"Maps: {maps_url}")
                if category:
                    parts.append(f"Category: {category}")
                notes = "\n".join(parts)

            add_lead(
                contact_name=contact_name,
                contact_role=contact_role,
                clinic_name=clinic_name,
                clinic_size=clinic_size,
                call_outcome=call_outcome,
                next_action=next_action,
                next_action_date=next_action_date,
                notes=notes,
                source_file=source_file,
            )
            count += 1
            if limit is not None and count >= limit:
                break

    try:
        file_mtime = csv_file.stat().st_mtime
    except OSError:
        file_mtime = None
    mark_imported(source_file, file_mtime, count)
    return count


def import_new_results(results_dir: Path = DEFAULT_RESULTS_DIR, force: bool = False) -> dict[str, int]:
    """Import any new CSVs from the scraper output directory."""
    init_db()
    results_dir = Path(results_dir)
    if not results_dir.exists():
        return {"files": 0, "rows": 0}

    files = sorted(
        (p for p in results_dir.glob("*.csv") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
    )
    imported_files = 0
    imported_rows = 0
    for p in files:
        rows = import_from_scraper_csv(str(p), force=force)
        if rows:
            imported_files += 1
            imported_rows += rows
    return {"files": imported_files, "rows": imported_rows}
