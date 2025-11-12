"""
Simple Memory Module using SQLite
Stores document metadata and user corrections
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.config import DB_PATH, CORRECTIONS_FILE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleMemory:
    """SQLite-based memory for documents and corrections"""

    def __init__(self, db_path: Path = DB_PATH):
        """Initialize memory database"""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    detected_type TEXT,
                    source TEXT,
                    topics TEXT,  -- JSON array
                    upload_date TEXT,
                    file_size INTEGER,
                    num_pages INTEGER,
                    date_in_doc TEXT,  -- Date extracted from document
                    metadata TEXT,  -- JSON dict
                    indexed BOOLEAN DEFAULT 0
                )
            """)

            # Corrections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    original_answer TEXT,
                    corrected_answer TEXT NOT NULL,
                    correction_date TEXT,
                    notes TEXT
                )
            """)

            # Query log table (for learning)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    answer TEXT,
                    retrieved_docs TEXT,  -- JSON array of doc IDs
                    feedback INTEGER,  -- 1 = thumbs up, -1 = thumbs down
                    query_date TEXT
                )
            """)

            # Program profile table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS program_profiles (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    program_name TEXT,
                    indication TEXT,
                    stage TEXT,
                    our_orr REAL,
                    our_pfs REAL,
                    our_safety_profile TEXT,
                    target TEXT,
                    differentiators TEXT,
                    last_updated TEXT
                )
            """)

            # Performance indexes for scalability (supports 1000+ documents)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_date DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_detected_type ON documents(detected_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_indexed ON documents(indexed)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_type_date ON documents(detected_type, upload_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename)")
            logger.info("✓ Created performance indexes on documents table")

            conn.commit()
            logger.info(f"Initialized database at {self.db_path}")

    # Document operations

    def add_document(
        self,
        doc_id: str,
        filename: str,
        detected_type: str,
        source: str,
        topics: List[str],
        file_size: int,
        num_pages: int,
        date_in_doc: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Add document to memory"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO documents
                (id, filename, detected_type, source, topics, upload_date, file_size, num_pages, date_in_doc, metadata, indexed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                filename,
                detected_type,
                source,
                json.dumps(topics),
                datetime.now().isoformat(),
                file_size,
                num_pages,
                date_in_doc,
                json.dumps(metadata or {}),
                False
            ))
            conn.commit()
            logger.info(f"Added document: {filename} ({detected_type})")

    def mark_indexed(self, doc_id: str):
        """Mark document as indexed in vector store"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE documents SET indexed = 1 WHERE id = ?", (doc_id,))
            conn.commit()

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get document by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_doc_dict(cursor, row)
            return None

    def list_documents(
        self,
        doc_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """List documents with optional filters"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM documents WHERE 1=1"
            params = []

            if doc_type:
                query += " AND detected_type = ?"
                params.append(doc_type)

            if source:
                query += " AND source = ?"
                params.append(source)

            query += " ORDER BY upload_date DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_doc_dict(cursor, row) for row in rows]

    def search_documents(self, keyword: str, limit: int = 50) -> List[Dict]:
        """Search documents by keyword in filename or topics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            keyword_pattern = f"%{keyword}%"

            cursor.execute("""
                SELECT * FROM documents
                WHERE filename LIKE ? OR topics LIKE ? OR source LIKE ?
                ORDER BY upload_date DESC
                LIMIT ?
            """, (keyword_pattern, keyword_pattern, keyword_pattern, limit))

            rows = cursor.fetchall()
            return [self._row_to_doc_dict(cursor, row) for row in rows]

    def _row_to_doc_dict(self, cursor, row) -> Dict:
        """Convert database row to dictionary"""
        columns = [desc[0] for desc in cursor.description]
        doc_dict = dict(zip(columns, row))

        # Parse JSON fields
        if doc_dict.get("topics"):
            doc_dict["topics"] = json.loads(doc_dict["topics"])
        if doc_dict.get("metadata"):
            doc_dict["metadata"] = json.loads(doc_dict["metadata"])

        return doc_dict

    # Corrections operations

    def add_correction(
        self,
        query: str,
        original_answer: str,
        corrected_answer: str,
        notes: Optional[str] = None
    ):
        """Add user correction"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO corrections (query, original_answer, corrected_answer, correction_date, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                query,
                original_answer,
                corrected_answer,
                datetime.now().isoformat(),
                notes
            ))
            conn.commit()
            logger.info(f"Added correction for query: {query[:50]}...")

    def _escape_like(self, value: str) -> str:
        """Escape LIKE special characters to prevent injection"""
        # Escape % and _ characters
        return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

    def get_correction(self, query: str) -> Optional[Dict]:
        """Get correction for query (if exists)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Exact match first
            cursor.execute("""
                SELECT * FROM corrections
                WHERE query = ?
                ORDER BY correction_date DESC
                LIMIT 1
            """, (query,))

            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))

            # Fuzzy match (partial) - with escaped LIKE pattern
            escaped_query = self._escape_like(query)
            cursor.execute("""
                SELECT * FROM corrections
                WHERE ? LIKE '%' || query || '%' ESCAPE '\\' OR query LIKE '%' || ? || '%' ESCAPE '\\'
                ORDER BY correction_date DESC
                LIMIT 1
            """, (escaped_query, escaped_query))

            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))

            return None

    def list_corrections(self, limit: int = 50) -> List[Dict]:
        """List all corrections"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM corrections
                ORDER BY correction_date DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    # Query log operations

    def log_query(
        self,
        query: str,
        answer: str,
        retrieved_docs: List[str],
        feedback: Optional[int] = None
    ):
        """Log query and response"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO query_log (query, answer, retrieved_docs, feedback, query_date)
                VALUES (?, ?, ?, ?, ?)
            """, (
                query,
                answer,
                json.dumps(retrieved_docs),
                feedback,
                datetime.now().isoformat()
            ))
            conn.commit()

    def update_feedback(self, query_id: int, feedback: int):
        """Update feedback for logged query"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE query_log SET feedback = ? WHERE id = ?
            """, (feedback, query_id))
            conn.commit()

    def get_query_stats(self) -> Dict:
        """Get query statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total queries
            cursor.execute("SELECT COUNT(*) FROM query_log")
            total_queries = cursor.fetchone()[0]

            # Queries with feedback
            cursor.execute("SELECT COUNT(*) FROM query_log WHERE feedback IS NOT NULL")
            queries_with_feedback = cursor.fetchone()[0]

            # Positive feedback
            cursor.execute("SELECT COUNT(*) FROM query_log WHERE feedback = 1")
            positive_feedback = cursor.fetchone()[0]

            # Negative feedback
            cursor.execute("SELECT COUNT(*) FROM query_log WHERE feedback = -1")
            negative_feedback = cursor.fetchone()[0]

            return {
                "total_queries": total_queries,
                "queries_with_feedback": queries_with_feedback,
                "positive_feedback": positive_feedback,
                "negative_feedback": negative_feedback,
                "feedback_rate": queries_with_feedback / total_queries if total_queries > 0 else 0,
                "satisfaction_rate": positive_feedback / queries_with_feedback if queries_with_feedback > 0 else 0
            }

    # Utility

    def get_stats(self) -> Dict:
        """Get overall statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Document counts by type
            cursor.execute("""
                SELECT detected_type, COUNT(*) as count
                FROM documents
                GROUP BY detected_type
            """)
            docs_by_type = dict(cursor.fetchall())

            # Total documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]

            # Indexed documents
            cursor.execute("SELECT COUNT(*) FROM documents WHERE indexed = 1")
            indexed_docs = cursor.fetchone()[0]

            # Corrections count
            cursor.execute("SELECT COUNT(*) FROM corrections")
            total_corrections = cursor.fetchone()[0]

            return {
                "total_documents": total_docs,
                "indexed_documents": indexed_docs,
                "documents_by_type": docs_by_type,
                "total_corrections": total_corrections,
                "query_stats": self.get_query_stats()
            }


# Singleton instance
_memory_instance: Optional[SimpleMemory] = None


def get_memory() -> SimpleMemory:
    """Get or create memory singleton"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = SimpleMemory()
    return _memory_instance


if __name__ == "__main__":
    # Test memory
    print("Testing Simple Memory...")

    memory = get_memory()

    # Add test document
    memory.add_document(
        doc_id="test_001",
        filename="test_article.pdf",
        detected_type="publication",
        source="NEJM",
        topics=["NSCLC", "PD-1"],
        file_size=1024000,
        num_pages=10
    )

    # List documents
    docs = memory.list_documents()
    print(f"Documents: {len(docs)}")

    # Get stats
    stats = memory.get_stats()
    print(f"Stats: {stats}")

    print("✓ Memory test successful!")
