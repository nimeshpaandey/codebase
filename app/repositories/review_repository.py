import sqlite3
import os
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.schemas.finding import Finding, Category, Severity

class ReviewRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS findings (
                    id TEXT PRIMARY KEY,
                    review_id TEXT NOT NULL,
                    title TEXT,
                    category TEXT,
                    severity TEXT,
                    confidence REAL,
                    file TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    source TEXT,
                    evidence TEXT,
                    explanation TEXT,
                    suggestion TEXT,
                    autofix TEXT,
                    FOREIGN KEY(review_id) REFERENCES reviews(id)
                )
            """)
            
            # Auto-migrate columns if table existed with older schema
            cursor.execute("PRAGMA table_info(findings)")
            columns = [row[1] for row in cursor.fetchall()]
            if "start_line" not in columns:
                cursor.execute("ALTER TABLE findings ADD COLUMN start_line INTEGER")
            if "end_line" not in columns:
                cursor.execute("ALTER TABLE findings ADD COLUMN end_line INTEGER")
            if "autofix" not in columns:
                cursor.execute("ALTER TABLE findings ADD COLUMN autofix TEXT")
                
            cursor.execute("PRAGMA table_info(reviews)")
            review_cols = [row[1] for row in cursor.fetchall()]
            if "created_at" not in review_cols:
                cursor.execute("ALTER TABLE reviews ADD COLUMN created_at TIMESTAMP")
                
            conn.commit()

    def save_review(self, review_id: str, status: str, findings: List[Finding]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO reviews (id, status) VALUES (?, ?)", (review_id, status))
            
            for f in findings:
                cursor.execute("""
                    INSERT OR REPLACE INTO findings (
                        id, review_id, title, category, severity, confidence,
                        file, start_line, end_line, source, evidence,
                        explanation, suggestion, autofix
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f.id,
                    review_id,
                    f.title,
                    f.category.value if isinstance(f.category, Category) else str(f.category),
                    f.severity.value if isinstance(f.severity, Severity) else str(f.severity),
                    f.confidence,
                    f.file,
                    f.start_line,
                    f.end_line,
                    f.source,
                    f.evidence,
                    f.explanation,
                    f.suggestion,
                    f.autofix
                ))
            conn.commit()

    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            review_row = cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
            if not review_row:
                return None
                
            findings_rows = cursor.execute("SELECT * FROM findings WHERE review_id = ?", (review_id,)).fetchall()
            
            findings = []
            for row in findings_rows:
                row_dict = dict(row)
                row_dict.pop("review_id", None)
                findings.append(Finding(**row_dict))
                
            return {
                "review_id": review_row["id"],
                "status": review_row["status"],
                "findings": findings
            }

    def list_reviews(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute("SELECT id, status, created_at FROM reviews ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
