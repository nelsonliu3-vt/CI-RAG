"""
Entity Store Module
Manages structured competitive intelligence entities in SQLite database
"""

import sqlite3
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from core.config import DATABASE_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EntityStore:
    """Store and query competitive intelligence entities"""

    def __init__(self, db_path: str = DATABASE_PATH):
        """Initialize entity store with database connection"""
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create entity tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Companies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                aliases TEXT,  -- JSON array
                role TEXT,  -- sponsor, competitor, partner
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Assets (drugs) table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                company_id INTEGER,
                mechanism TEXT,
                indication TEXT,
                phase TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)

        # Trials table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trial_id TEXT UNIQUE NOT NULL,  -- NCT number or internal ID
                asset_id INTEGER,
                phase TEXT,
                indication TEXT,
                status TEXT,  -- ongoing, completed, planned
                n_patients INTEGER,
                start_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (asset_id) REFERENCES assets(id)
            )
        """)

        # Data points table (versioned)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trial_id INTEGER NOT NULL,
                doc_id TEXT,  -- Links back to documents table
                metric_type TEXT NOT NULL,  -- ORR, PFS, OS, AE, etc.
                value REAL,
                confidence_interval TEXT,
                n_patients INTEGER,
                unit TEXT,
                data_maturity TEXT,  -- interim, final, updated
                subgroup TEXT,  -- overall or subgroup description
                date_reported DATE NOT NULL,
                supersedes_id INTEGER,  -- Links to previous version of this data point
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trial_id) REFERENCES trials(id),
                FOREIGN KEY (supersedes_id) REFERENCES data_points(id)
            )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_company ON assets(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trials_asset ON trials(asset_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_datapoints_trial ON data_points(trial_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_datapoints_date ON data_points(date_reported)")

        conn.commit()
        conn.close()

        logger.info("Entity database initialized")

    def add_company(self, name: str, aliases: List[str] = None, role: str = "competitor") -> int:
        """Add or get company (thread-safe with INSERT OR IGNORE)"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Use INSERT OR IGNORE for atomic upsert
            cursor.execute(
                "INSERT OR IGNORE INTO companies (name, aliases, role) VALUES (?, ?, ?)",
                (name, json.dumps(aliases or []), role)
            )

            # Always SELECT to get ID (works whether inserted or already existed)
            cursor.execute("SELECT id FROM companies WHERE name = ?", (name,))
            result = cursor.fetchone()

            if not result:
                raise ValueError(f"Failed to add company: {name}")

            company_id = result[0]
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Added company: {name} (ID: {company_id})")

            return company_id

        finally:
            conn.close()

    def add_asset(self, name: str, company_name: str, mechanism: str = None,
                  indication: str = None, phase: str = None) -> int:
        """Add or get asset (thread-safe with INSERT OR IGNORE)"""
        # Get or create company first (outside transaction)
        company_id = self.add_company(company_name)

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Use INSERT OR IGNORE for atomic upsert
            # Note: We use name + company_id as unique constraint
            cursor.execute(
                "INSERT OR IGNORE INTO assets (name, company_id, mechanism, indication, phase) VALUES (?, ?, ?, ?, ?)",
                (name, company_id, mechanism, indication, phase)
            )

            # Always SELECT to get ID
            cursor.execute(
                "SELECT id FROM assets WHERE name = ? AND company_id = ?",
                (name, company_id)
            )
            result = cursor.fetchone()

            if not result:
                raise ValueError(f"Failed to add asset: {name} for company {company_name}")

            asset_id = result[0]
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Added asset: {name} for {company_name} (ID: {asset_id})")

            return asset_id

        finally:
            conn.close()

    def add_trial(self, trial_id: str, asset_name: str, company_name: str,
                  phase: str = None, indication: str = None, status: str = None,
                  n_patients: int = None) -> int:
        """Add or get trial (thread-safe with INSERT OR IGNORE)"""
        # Get or create asset first (outside transaction)
        asset_id = self.add_asset(asset_name, company_name)

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Use INSERT OR IGNORE for atomic upsert
            cursor.execute(
                """INSERT OR IGNORE INTO trials (trial_id, asset_id, phase, indication, status, n_patients)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (trial_id, asset_id, phase, indication, status, n_patients)
            )

            # Always SELECT to get ID
            cursor.execute("SELECT id FROM trials WHERE trial_id = ?", (trial_id,))
            result = cursor.fetchone()

            if not result:
                raise ValueError(f"Failed to add trial: {trial_id}")

            trial_db_id = result[0]
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Added trial: {trial_id} (ID: {trial_db_id})")

            return trial_db_id

        finally:
            conn.close()

    def add_data_point(self, trial_id: str, metric_type: str, value: float,
                       date_reported: str, doc_id: str = None,
                       confidence_interval: str = None, n_patients: int = None,
                       unit: str = None, data_maturity: str = None,
                       subgroup: str = "overall") -> Optional[int]:
        """
        Add data point and detect if it updates previous data

        Returns:
            data_point_id or None if trial not found
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Get trial database ID
            cursor.execute("SELECT id FROM trials WHERE trial_id = ?", (trial_id,))
            result = cursor.fetchone()

            if not result:
                logger.warning(f"Trial {trial_id} not found, cannot add data point")
                return None

            trial_db_id = result[0]

            # Check for previous data point of same type for this trial
            cursor.execute(
                """SELECT id, value, date_reported FROM data_points
                   WHERE trial_id = ? AND metric_type = ? AND subgroup = ?
                   ORDER BY date_reported DESC LIMIT 1""",
                (trial_db_id, metric_type, subgroup)
            )
            previous = cursor.fetchone()

            supersedes_id = None
            if previous:
                prev_id, prev_value, prev_date = previous
                # Check if this is newer data
                if date_reported > prev_date:
                    supersedes_id = prev_id
                    logger.info(f"Data point updates previous: {metric_type} {prev_value} → {value} "
                              f"(trial {trial_id})")

            # Insert new data point
            cursor.execute(
                """INSERT INTO data_points
                   (trial_id, doc_id, metric_type, value, confidence_interval, n_patients,
                    unit, data_maturity, subgroup, date_reported, supersedes_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (trial_db_id, doc_id, metric_type, value, confidence_interval, n_patients,
                 unit, data_maturity, subgroup, date_reported, supersedes_id)
            )
            data_point_id = cursor.lastrowid
            conn.commit()

            return data_point_id

        finally:
            conn.close()

    def get_trial_history(self, trial_id: str, metric_type: str = None) -> List[Dict[str, Any]]:
        """Get historical data for a trial"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if metric_type:
                cursor.execute(
                    """SELECT * FROM data_points dp
                       JOIN trials t ON dp.trial_id = t.id
                       WHERE t.trial_id = ? AND dp.metric_type = ?
                       ORDER BY dp.date_reported ASC""",
                    (trial_id, metric_type)
                )
            else:
                cursor.execute(
                    """SELECT * FROM data_points dp
                       JOIN trials t ON dp.trial_id = t.id
                       WHERE t.trial_id = ?
                       ORDER BY dp.date_reported ASC""",
                    (trial_id,)
                )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_competitor_assets(self, company_name: str) -> List[Dict[str, Any]]:
        """Get all assets for a competitor"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """SELECT a.* FROM assets a
                   JOIN companies c ON a.company_id = c.id
                   WHERE c.name = ?""",
                (company_name,)
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def detect_update(self, trial_id: str, metric_type: str, new_value: float,
                      new_date: str) -> Optional[Dict[str, Any]]:
        """
        Check if new data updates existing data

        Returns:
            Dict with update info if update detected, None otherwise
        """
        history = self.get_trial_history(trial_id, metric_type)

        if not history:
            return None  # No previous data

        # Get most recent data point before new_date
        previous_data = [h for h in history if h['date_reported'] < new_date]

        if not previous_data:
            return None

        latest_previous = previous_data[-1]

        # Calculate change
        old_value = latest_previous['value']
        change = new_value - old_value
        pct_change = (change / old_value) * 100 if old_value != 0 else 0

        return {
            "is_update": True,
            "trial_id": trial_id,
            "metric_type": metric_type,
            "old_value": old_value,
            "new_value": new_value,
            "change": change,
            "pct_change": pct_change,
            "old_date": latest_previous['date_reported'],
            "new_date": new_date,
            "old_n": latest_previous.get('n_patients'),
            "new_n": None  # Will be filled by caller
        }

    def get_stats(self) -> Dict[str, int]:
        """Get entity database statistics"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            stats = {}

            cursor.execute("SELECT COUNT(*) FROM companies")
            stats['total_companies'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM assets")
            stats['total_assets'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM trials")
            stats['total_trials'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM data_points")
            stats['total_data_points'] = cursor.fetchone()[0]

            # Get data points with updates
            cursor.execute("SELECT COUNT(*) FROM data_points WHERE supersedes_id IS NOT NULL")
            stats['updated_data_points'] = cursor.fetchone()[0]

            return stats

        finally:
            conn.close()


# Singleton instance
_entity_store_instance: Optional[EntityStore] = None


def get_entity_store(db_path: str = DATABASE_PATH) -> EntityStore:
    """Get or create entity store singleton"""
    global _entity_store_instance
    if _entity_store_instance is None:
        _entity_store_instance = EntityStore(db_path)
    return _entity_store_instance


if __name__ == "__main__":
    # Test entity store
    print("Testing Entity Store...")

    store = get_entity_store()

    # Add test company
    company_id = store.add_company("Competitor Pharma", aliases=["CompPharma", "CP Inc"])

    # Add test asset
    asset_id = store.add_asset(
        "Drug-ABC",
        "Competitor Pharma",
        mechanism="KRAS G12C inhibitor",
        indication="NSCLC",
        phase="Phase 2"
    )

    # Add test trial
    trial_id = store.add_trial(
        "NCT12345678",
        "Drug-ABC",
        "Competitor Pharma",
        phase="Phase 2",
        indication="2L NSCLC (KRAS G12C)",
        status="completed",
        n_patients=150
    )

    # Add interim data point
    dp1 = store.add_data_point(
        "NCT12345678",
        "ORR",
        40.0,
        "2024-01-15",
        confidence_interval="32-48",
        n_patients=50,
        unit="%",
        data_maturity="interim"
    )

    # Add final data point (update)
    dp2 = store.add_data_point(
        "NCT12345678",
        "ORR",
        45.0,
        "2024-06-15",
        confidence_interval="38-52",
        n_patients=150,
        unit="%",
        data_maturity="final"
    )

    # Get history
    history = store.get_trial_history("NCT12345678", "ORR")
    print(f"\n✓ Trial history: {len(history)} data points")
    for h in history:
        print(f"  - {h['date_reported']}: ORR = {h['value']}% (n={h['n_patients']}, {h['data_maturity']})")

    # Detect update
    update_info = store.detect_update("NCT12345678", "ORR", 45.0, "2024-06-15")
    if update_info:
        print(f"\n✓ Update detected:")
        print(f"  ORR: {update_info['old_value']}% → {update_info['new_value']}% "
              f"({update_info['pct_change']:+.1f}%)")

    # Get stats
    stats = store.get_stats()
    print(f"\n✓ Entity store stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n✓ Entity store test successful!")
