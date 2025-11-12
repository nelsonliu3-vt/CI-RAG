"""
Program Profile Module
Manages user's program context for personalized impact analysis
"""

import sqlite3
import logging
from typing import Dict, Optional
from datetime import datetime

from core.config import DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProgramProfile:
    """Manages program profile for personalized CI analysis"""

    def __init__(self, db_path=DB_PATH):
        """Initialize program profile manager"""
        self.db_path = db_path

    def save_profile(
        self,
        program_name: str,
        indication: Optional[str] = None,
        stage: Optional[str] = None,
        our_orr: Optional[float] = None,
        our_pfs: Optional[float] = None,
        our_safety_profile: Optional[str] = None,
        target: Optional[str] = None,
        differentiators: Optional[str] = None
    ):
        """
        Save or update program profile (single profile per database)

        Only program_name is required - all other fields are optional.
        You can provide just a drug name (e.g., "Keytruda") or mechanism (e.g., "EGFR conditional TCE").

        Args:
            program_name: Name of your program/drug or mechanism (REQUIRED)
            indication: Target indication (e.g., "2L NSCLC") - OPTIONAL
            stage: Development stage (e.g., "Phase 2") - OPTIONAL
            our_orr: Our program's ORR (%) if available - OPTIONAL
            our_pfs: Our program's PFS (months) if available - OPTIONAL
            our_safety_profile: Description of our safety profile - OPTIONAL
            target: Molecular target (e.g., "KRAS G12C") - OPTIONAL
            differentiators: Key differentiators vs competition - OPTIONAL
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO program_profiles
                (id, program_name, indication, stage, our_orr, our_pfs,
                 our_safety_profile, target, differentiators, last_updated)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                program_name,
                indication,
                stage,
                our_orr,
                our_pfs,
                our_safety_profile,
                target,
                differentiators,
                datetime.now().isoformat()
            ))
            conn.commit()
            logger.info(f"Saved program profile: {program_name}")

    def get_profile(self) -> Optional[Dict]:
        """
        Get current program profile

        Returns:
            Dictionary with profile data or None if not set
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM program_profiles WHERE id = 1")
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                profile = dict(zip(columns, row))
                return profile

            return None

    def has_profile(self) -> bool:
        """Check if program profile exists"""
        return self.get_profile() is not None

    def format_profile_context(self) -> str:
        """
        Format program profile as context for LLM

        Returns:
            Formatted string describing the program
        """
        profile = self.get_profile()

        if not profile:
            return "No program profile set. Using general CI analysis mode."

        # Start with program name (always present)
        parts = [f"**Program**: {profile['program_name']}"]

        # Add optional fields only if they exist and are not empty
        if profile.get('indication'):
            parts.append(f"**Indication**: {profile['indication']}")

        if profile.get('stage'):
            parts.append(f"**Stage**: {profile['stage']}")

        if profile.get('target'):
            parts.append(f"**Target**: {profile['target']}")

        if profile.get('our_orr') is not None:
            parts.append(f"**Our ORR**: {profile['our_orr']}%")

        if profile.get('our_pfs') is not None:
            parts.append(f"**Our PFS**: {profile['our_pfs']} months")

        if profile.get('our_safety_profile'):
            parts.append(f"**Our Safety Profile**: {profile['our_safety_profile']}")

        if profile.get('differentiators'):
            parts.append(f"**Key Differentiators**: {profile['differentiators']}")

        return "\n".join(parts)

    def delete_profile(self):
        """Delete program profile"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM program_profiles WHERE id = 1")
            conn.commit()
            logger.info("Deleted program profile")

    def link_document_to_program(self, doc_id: str, doc_type: str = "program_document"):
        """
        Link a document to the current program profile

        Args:
            doc_id: Document ID from the documents table
            doc_type: Type of document (e.g., "program_document", "slide_deck", "paper")
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Update document metadata to mark it as program-related
            cursor.execute("""
                UPDATE documents
                SET metadata = json_set(
                    COALESCE(metadata, '{}'),
                    '$.is_program_doc', 1,
                    '$.program_doc_type', ?
                )
                WHERE doc_id = ?
            """, (doc_type, doc_id))
            conn.commit()
            logger.info(f"Linked document {doc_id} to program as {doc_type}")

    def unlink_document_from_program(self, doc_id: str):
        """
        Unlink a document from the program profile

        Args:
            doc_id: Document ID to unlink
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Remove program markers from metadata
            cursor.execute("""
                UPDATE documents
                SET metadata = json_remove(
                    metadata,
                    '$.is_program_doc',
                    '$.program_doc_type'
                )
                WHERE doc_id = ?
            """, (doc_id,))
            conn.commit()
            logger.info(f"Unlinked document {doc_id} from program")

    def get_program_documents(self):
        """
        Get all documents linked to the program

        Returns:
            List of document dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Query documents marked as program documents
            cursor.execute("""
                SELECT id as doc_id, filename, detected_type, source, upload_date,
                       file_size, num_pages, indexed, metadata
                FROM documents
                WHERE json_extract(metadata, '$.is_program_doc') = 1
                ORDER BY upload_date DESC
            """)

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            documents = []
            for row in rows:
                doc = dict(zip(columns, row))
                documents.append(doc)

            return documents


# Singleton instance
_profile_instance: Optional[ProgramProfile] = None


def get_program_profile() -> ProgramProfile:
    """Get or create program profile singleton"""
    global _profile_instance
    if _profile_instance is None:
        _profile_instance = ProgramProfile()
    return _profile_instance


if __name__ == "__main__":
    # Test program profile
    print("Testing Program Profile...")

    profile = get_program_profile()

    # Save test profile
    profile.save_profile(
        program_name="AZ-123 (KRAS G12C inhibitor)",
        indication="2L+ NSCLC (KRAS G12C mutant)",
        stage="Phase 2",
        our_orr=52.0,
        our_pfs=9.5,
        our_safety_profile="Grade ≥3 AEs: 58%, Disc rate: 8%",
        target="KRAS G12C",
        differentiators="Better tolerability, longer PFS vs sotorasib"
    )

    # Get and display
    saved_profile = profile.get_profile()
    print(f"✓ Saved profile: {saved_profile['program_name']}")

    # Format for LLM
    context = profile.format_profile_context()
    print(f"\n✓ Formatted context:\n{context}")

    print("\n✓ Program profile test successful!")
