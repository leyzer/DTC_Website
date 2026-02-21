"""
Database initialization script for DTC League application.
This script initializes the SQLite database with the proper schema for production use.
It preserves reference data by exporting to CSV for migration to production servers.
"""
import sqlite3
import os
import sys
import logging
import csv
import shutil
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_NAME = "GPTLeague.db"
SCHEMA_FILE = "schema.sql"
EXPORT_DIR = "data_exports"
REFERENCE_TABLES = ['elo_rules', 'factions', 'league_settings', 'locations', 'seasons', 'systems']

def create_export_dir():
    """Create the data exports directory if it doesn't exist"""
    export_path = Path(__file__).parent / EXPORT_DIR
    export_path.mkdir(exist_ok=True)
    return export_path

def export_reference_tables(db_path):
    """Export reference tables to CSV files"""
    export_path = create_export_dir()
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            for table in REFERENCE_TABLES:
                try:
                    # Get all rows from the table
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    
                    if rows:
                        # Get column names
                        col_names = [description[0] for description in cursor.description]
                        
                        # Write to CSV
                        csv_path = export_path / f"{table}.csv"
                        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(col_names)
                            for row in rows:
                                writer.writerow(row)
                        
                        logger.info(f"✓ Exported {table}: {len(rows)} rows → {csv_path.name}")
                    else:
                        logger.info(f"  {table}: (no data)")
                        
                except Exception as e:
                    logger.warning(f"  Could not export {table}: {e}")
            
        return True
        
    except Exception as e:
        logger.error(f"✗ Error exporting reference tables: {e}")
        return False

def import_reference_tables(db_path, export_path):
    """Import reference tables from CSV files"""
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            for table in REFERENCE_TABLES:
                csv_path = export_path / f"{table}.csv"
                
                if not csv_path.exists():
                    logger.info(f"  {table}: CSV not found, skipping")
                    continue
                
                try:
                    with open(csv_path, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        col_names = next(reader)  # Get header row
                        
                        # Prepare insert statement
                        placeholders = ','.join(['?' for _ in col_names])
                        insert_sql = f"INSERT INTO {table} ({','.join(col_names)}) VALUES ({placeholders})"
                        
                        # Insert rows
                        row_count = 0
                        for row in reader:
                            if row:  # Skip empty rows
                                cursor.execute(insert_sql, row)
                                row_count += 1
                        
                        conn.commit()
                        logger.info(f"✓ Imported {table}: {row_count} rows")
                        
                except Exception as e:
                    logger.warning(f"  Error importing {table}: {e}")
            
        return True
        
    except Exception as e:
        logger.error(f"✗ Error importing reference tables: {e}")
        return False

def init_database():
    """Initialize the database from schema.sql"""
    
    # Get the current directory
    current_dir = Path(__file__).parent
    db_path = current_dir / DB_NAME
    schema_path = current_dir / SCHEMA_FILE
    
    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        return False
    
    try:
        # Create or connect to the database
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # Read and execute the schema
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Execute the schema
            cursor.executescript(schema_sql)
            conn.commit()
            
            logger.info(f"✓ Database initialized successfully at: {db_path}")
            
            # Verify tables were created
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            )
            tables = cursor.fetchall()
            
            if tables:
                logger.info(f"✓ Created {len(tables)} tables:")
                for table in tables:
                    logger.info(f"  - {table[0]}")
            
        return True
        
    except Exception as e:
        logger.error(f"✗ Error initializing database: {e}")
        return False

def cleanup_temp_sessions():
    """Remove temporary session files"""
    session_dir = Path(__file__).parent / "flask_session"
    
    if session_dir.exists():
        try:
            session_files = list(session_dir.glob("*"))
            if session_files:
                for f in session_files:
                    if f.is_file():
                        f.unlink()
                logger.info(f"✓ Cleaned up {len(session_files)} temporary session file(s)")
            else:
                logger.info("✓ No temporary session files to clean up")
        except Exception as e:
            logger.warning(f"Could not clean up session files: {e}")

def verify_database():
    """Verify the database is properly set up"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Check required tables
            required_tables = [
                'users', 'seasons', 'systems', 'games', 'game_participants',
                'ratings', 'system_memberships', 'club_memberships', 'user_roles'
            ]
            
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            )
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            missing = set(required_tables) - existing_tables
            if missing:
                logger.warning(f"✗ Missing tables: {', '.join(missing)}")
                return False
            
            logger.info("✓ All required tables exist")
            
            # Check database integrity
            cursor.execute("PRAGMA integrity_check;")
            integrity = cursor.fetchone()[0]
            if integrity == "ok":
                logger.info("✓ Database integrity check passed")
            else:
                logger.error(f"✗ Database integrity issue: {integrity}")
                return False
            
        return True
        
    except Exception as e:
        logger.error(f"✗ Error verifying database: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("DTC League Database Initialization")
    logger.info("=" * 60)
    
    current_dir = Path(__file__).parent
    db_path = current_dir / DB_NAME
    backup_path = current_dir / f"{DB_NAME}.backup"
    export_path = Path(__file__).parent / EXPORT_DIR
    
    # Step 1: Export reference tables from existing database
    if db_path.exists():
        logger.info("\n[1/4] Exporting reference tables...")
        export_reference_tables(db_path)
        
        # Step 2: Backup existing database
        logger.info("\n[2/4] Backing up existing database...")
        if backup_path.exists():
            try:
                backup_path.unlink()
            except PermissionError:
                backup_path = current_dir / f"{DB_NAME}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logger.info(f"  Existing backup is locked, using timestamped backup instead")
        
        try:
            shutil.copy(db_path, backup_path)
            logger.info(f"✓ Backup created: {backup_path.name}")
            db_path.unlink()
        except PermissionError:
            logger.warning(f"⚠ Database file is locked by another process")
            logger.warning(f"  Close any running Flask servers and try again, or:")
            logger.warning(f"  1. Manually delete/rename {DB_NAME}")
            logger.warning(f"  2. Run this script again")
            sys.exit(1)
    else:
        logger.info("\n[1/4] No existing database found, starting fresh")
        logger.info("[2/4] (backup skipped)")
    
    # Step 3: Initialize new database
    logger.info("\n[3/4] Creating fresh database...")
    if init_database():
        # Step 4: Import reference tables
        logger.info("\n[4/4] Importing reference tables...")
        if export_path.exists() and any(export_path.glob("*.csv")):
            import_reference_tables(db_path, export_path)
        
        # Cleanup temp sessions
        cleanup_temp_sessions()
        
        # Verify setup
        if verify_database():
            logger.info("=" * 60)
            logger.info("✓ Database setup completed successfully!")
            logger.info(f"✓ Reference data exported to: {EXPORT_DIR}/")
            if backup_path.exists():
                logger.info(f"✓ Original database backed up: {backup_path.name}")
            logger.info("=" * 60)
            sys.exit(0)
        else:
            logger.error("Database verification failed")
            sys.exit(1)
    else:
        logger.error("Database initialization failed")
        sys.exit(1)
