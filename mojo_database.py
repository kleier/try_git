"""
Mojo Dialer SQLite Database Manager
Handles schema creation, migrations, and data storage for Mojo Dialer data
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import os


class MojoDatabase:
    """SQLite database manager for Mojo Dialer data"""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str = "mojo_data.db"):
        """
        Initialize the database manager

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.ensure_schema()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def ensure_schema(self):
        """Create database schema if it doesn't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Schema version tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Contacts table - stores lead/contact information
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mojo_id TEXT UNIQUE,
                    first_name TEXT,
                    last_name TEXT,
                    full_name TEXT,
                    email TEXT,
                    phone TEXT,
                    mobile_phone TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    status TEXT,
                    lead_source TEXT,
                    list_name TEXT,
                    tags TEXT,  -- JSON array
                    custom_fields TEXT,  -- JSON object
                    created_date TIMESTAMP,
                    updated_date TIMESTAMP,
                    last_contact_date TIMESTAMP,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_to_fub BOOLEAN DEFAULT 0,
                    fub_person_id TEXT,
                    fub_synced_at TIMESTAMP,
                    raw_data TEXT  -- JSON of original import
                )
            """)

            # Lists table - stores Mojo Dialer lists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mojo_list_id TEXT UNIQUE,
                    list_name TEXT NOT NULL,
                    description TEXT,
                    contact_count INTEGER DEFAULT 0,
                    created_date TIMESTAMP,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    raw_data TEXT
                )
            """)

            # Call logs table - stores call history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS call_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mojo_call_id TEXT UNIQUE,
                    contact_id INTEGER,
                    mojo_contact_id TEXT,
                    phone_number TEXT,
                    call_date TIMESTAMP,
                    call_duration INTEGER,  -- seconds
                    call_result TEXT,  -- Contact, No Answer, Voicemail, DNC, etc.
                    call_type TEXT,  -- Inbound, Outbound, Power Dialer
                    agent_name TEXT,
                    notes TEXT,
                    disposition TEXT,
                    recording_url TEXT,
                    recording_duration INTEGER,
                    has_recording BOOLEAN DEFAULT 0,
                    has_transcript BOOLEAN DEFAULT 0,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_to_fub BOOLEAN DEFAULT 0,
                    fub_synced_at TIMESTAMP,
                    raw_data TEXT,
                    FOREIGN KEY (contact_id) REFERENCES contacts(id)
                )
            """)

            # Call recordings table - stores recording metadata and transcripts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS call_recordings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_log_id INTEGER NOT NULL,
                    recording_url TEXT,
                    local_file_path TEXT,
                    file_size INTEGER,
                    duration INTEGER,
                    format TEXT,  -- mp3, wav, etc.
                    transcript TEXT,  -- Full transcript
                    transcript_source TEXT,  -- Manual, Outdoo, AWS, etc.
                    sentiment_score REAL,  -- -1.0 to 1.0
                    sentiment_label TEXT,  -- Positive, Neutral, Negative
                    intent_classification TEXT,  -- Buyer, Seller, Just Looking, etc.
                    talk_time INTEGER,  -- Agent talk time in seconds
                    listen_time INTEGER,  -- Client talk time in seconds
                    talk_listen_ratio REAL,  -- talk_time / listen_time
                    ai_coaching_notes TEXT,  -- AI-generated coaching feedback
                    downloaded_at TIMESTAMP,
                    analyzed_at TIMESTAMP,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    raw_data TEXT,
                    FOREIGN KEY (call_log_id) REFERENCES call_logs(id)
                )
            """)

            # Analytics summary table - pre-computed metrics for dashboards
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary_date DATE NOT NULL,
                    agent_name TEXT,
                    total_calls INTEGER DEFAULT 0,
                    total_contacts INTEGER DEFAULT 0,
                    total_call_duration INTEGER DEFAULT 0,
                    contact_rate REAL,  -- percentage
                    avg_call_duration REAL,
                    avg_talk_listen_ratio REAL,
                    positive_sentiment_count INTEGER DEFAULT 0,
                    negative_sentiment_count INTEGER DEFAULT 0,
                    buyer_intent_count INTEGER DEFAULT 0,
                    seller_intent_count INTEGER DEFAULT 0,
                    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(summary_date, agent_name)
                )
            """)

            # Import history table - track data imports
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS import_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    import_type TEXT,  -- contacts, calls, recordings
                    source_file TEXT,
                    records_imported INTEGER,
                    records_updated INTEGER,
                    records_failed INTEGER,
                    import_status TEXT,  -- success, partial, failed
                    error_message TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_fub_id ON contacts(fub_person_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_call_logs_contact_id ON call_logs(contact_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_call_logs_date ON call_logs(call_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_call_logs_result ON call_logs(call_result)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recordings_call_log_id ON call_recordings(call_log_id)")

            # Record schema version
            cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))

            conn.commit()

    def insert_contact(self, contact_data: Dict[str, Any]) -> int:
        """
        Insert or update a contact record

        Args:
            contact_data: Dictionary containing contact information

        Returns:
            Contact ID (database primary key)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Convert lists/dicts to JSON strings
            tags = json.dumps(contact_data.get('tags', []))
            custom_fields = json.dumps(contact_data.get('custom_fields', {}))
            raw_data = json.dumps(contact_data)

            cursor.execute("""
                INSERT INTO contacts (
                    mojo_id, first_name, last_name, full_name, email, phone, mobile_phone,
                    address, city, state, zip_code, status, lead_source, list_name,
                    tags, custom_fields, created_date, updated_date, last_contact_date, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mojo_id) DO UPDATE SET
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    full_name=excluded.full_name,
                    email=excluded.email,
                    phone=excluded.phone,
                    mobile_phone=excluded.mobile_phone,
                    address=excluded.address,
                    city=excluded.city,
                    state=excluded.state,
                    zip_code=excluded.zip_code,
                    status=excluded.status,
                    lead_source=excluded.lead_source,
                    list_name=excluded.list_name,
                    tags=excluded.tags,
                    custom_fields=excluded.custom_fields,
                    updated_date=excluded.updated_date,
                    last_contact_date=excluded.last_contact_date,
                    raw_data=excluded.raw_data
            """, (
                contact_data.get('mojo_id'),
                contact_data.get('first_name'),
                contact_data.get('last_name'),
                contact_data.get('full_name'),
                contact_data.get('email'),
                contact_data.get('phone'),
                contact_data.get('mobile_phone'),
                contact_data.get('address'),
                contact_data.get('city'),
                contact_data.get('state'),
                contact_data.get('zip_code'),
                contact_data.get('status'),
                contact_data.get('lead_source'),
                contact_data.get('list_name'),
                tags,
                custom_fields,
                contact_data.get('created_date'),
                contact_data.get('updated_date'),
                contact_data.get('last_contact_date'),
                raw_data
            ))

            # Get the inserted/updated ID
            cursor.execute("SELECT id FROM contacts WHERE mojo_id = ?", (contact_data.get('mojo_id'),))
            row = cursor.fetchone()
            return row[0] if row else cursor.lastrowid

    def insert_call_log(self, call_data: Dict[str, Any]) -> int:
        """Insert or update a call log record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Find contact_id if we have mojo_contact_id
            contact_id = None
            if call_data.get('mojo_contact_id'):
                cursor.execute("SELECT id FROM contacts WHERE mojo_id = ?", (call_data.get('mojo_contact_id'),))
                row = cursor.fetchone()
                contact_id = row[0] if row else None

            raw_data = json.dumps(call_data)

            cursor.execute("""
                INSERT INTO call_logs (
                    mojo_call_id, contact_id, mojo_contact_id, phone_number, call_date,
                    call_duration, call_result, call_type, agent_name, notes, disposition,
                    recording_url, recording_duration, has_recording, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mojo_call_id) DO UPDATE SET
                    contact_id=excluded.contact_id,
                    phone_number=excluded.phone_number,
                    call_date=excluded.call_date,
                    call_duration=excluded.call_duration,
                    call_result=excluded.call_result,
                    call_type=excluded.call_type,
                    agent_name=excluded.agent_name,
                    notes=excluded.notes,
                    disposition=excluded.disposition,
                    recording_url=excluded.recording_url,
                    recording_duration=excluded.recording_duration,
                    has_recording=excluded.has_recording,
                    raw_data=excluded.raw_data
            """, (
                call_data.get('mojo_call_id'),
                contact_id,
                call_data.get('mojo_contact_id'),
                call_data.get('phone_number'),
                call_data.get('call_date'),
                call_data.get('call_duration'),
                call_data.get('call_result'),
                call_data.get('call_type'),
                call_data.get('agent_name'),
                call_data.get('notes'),
                call_data.get('disposition'),
                call_data.get('recording_url'),
                call_data.get('recording_duration'),
                call_data.get('has_recording', False),
                raw_data
            ))

            cursor.execute("SELECT id FROM call_logs WHERE mojo_call_id = ?", (call_data.get('mojo_call_id'),))
            row = cursor.fetchone()
            return row[0] if row else cursor.lastrowid

    def get_contacts_to_sync(self, limit: Optional[int] = None) -> List[Dict]:
        """Get contacts that haven't been synced to FUB yet"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT * FROM contacts
                WHERE synced_to_fub = 0
                AND (email IS NOT NULL OR phone IS NOT NULL)
                ORDER BY created_date DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def mark_contact_synced(self, contact_id: int, fub_person_id: str):
        """Mark a contact as synced to FUB"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE contacts
                SET synced_to_fub = 1, fub_person_id = ?, fub_synced_at = ?
                WHERE id = ?
            """, (fub_person_id, datetime.now().isoformat(), contact_id))

    def get_call_logs_to_sync(self, limit: Optional[int] = None) -> List[Dict]:
        """Get call logs that haven't been synced to FUB yet"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT cl.*, c.fub_person_id, c.email, c.phone, c.full_name
                FROM call_logs cl
                LEFT JOIN contacts c ON cl.contact_id = c.id
                WHERE cl.synced_to_fub = 0
                AND c.fub_person_id IS NOT NULL
                ORDER BY cl.call_date DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def mark_call_synced(self, call_id: int):
        """Mark a call log as synced to FUB"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE call_logs
                SET synced_to_fub = 1, fub_synced_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), call_id))

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total contacts
            cursor.execute("SELECT COUNT(*) FROM contacts")
            stats['total_contacts'] = cursor.fetchone()[0]

            # Synced contacts
            cursor.execute("SELECT COUNT(*) FROM contacts WHERE synced_to_fub = 1")
            stats['synced_contacts'] = cursor.fetchone()[0]

            # Total calls
            cursor.execute("SELECT COUNT(*) FROM call_logs")
            stats['total_calls'] = cursor.fetchone()[0]

            # Synced calls
            cursor.execute("SELECT COUNT(*) FROM call_logs WHERE synced_to_fub = 1")
            stats['synced_calls'] = cursor.fetchone()[0]

            # Calls with recordings
            cursor.execute("SELECT COUNT(*) FROM call_logs WHERE has_recording = 1")
            stats['calls_with_recordings'] = cursor.fetchone()[0]

            # Total recordings analyzed
            cursor.execute("SELECT COUNT(*) FROM call_recordings WHERE transcript IS NOT NULL")
            stats['transcribed_recordings'] = cursor.fetchone()[0]

            # Call results breakdown
            cursor.execute("""
                SELECT call_result, COUNT(*) as count
                FROM call_logs
                WHERE call_result IS NOT NULL
                GROUP BY call_result
            """)
            stats['call_results'] = {row[0]: row[1] for row in cursor.fetchall()}

            return stats

    def record_import(self, import_type: str, source_file: str,
                     records_imported: int, records_updated: int = 0,
                     records_failed: int = 0, status: str = "success",
                     error_message: Optional[str] = None,
                     started_at: Optional[datetime] = None,
                     completed_at: Optional[datetime] = None) -> int:
        """Record an import operation in history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO import_history (
                    import_type, source_file, records_imported, records_updated,
                    records_failed, import_status, error_message, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                import_type,
                source_file,
                records_imported,
                records_updated,
                records_failed,
                status,
                error_message,
                started_at.isoformat() if started_at else None,
                completed_at.isoformat() if completed_at else None
            ))

            return cursor.lastrowid
