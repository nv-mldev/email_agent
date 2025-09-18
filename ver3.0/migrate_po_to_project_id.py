#!/usr/bin/env python3
"""
Database migration script to rename purchase_order_number to project_id
Run this script to update the existing database schema.
"""

import os
import sys
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import engine
from core.config import settings


def migrate_po_to_project_id():
    """Migrate the purchase_order_number column to project_id."""
    print("Starting migration: purchase_order_number -> project_id")

    try:
        with engine.connect() as connection:
            # Start a transaction
            trans = connection.begin()

            try:
                # Check if the old column exists
                result = connection.execute(
                    text(
                        """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'email_processing_log' 
                    AND column_name = 'purchase_order_number'
                """
                    )
                )

                old_column_exists = result.fetchone() is not None

                # Check if the new column already exists
                result = connection.execute(
                    text(
                        """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'email_processing_log' 
                    AND column_name = 'project_id'
                """
                    )
                )

                new_column_exists = result.fetchone() is not None

                if old_column_exists and not new_column_exists:
                    # Rename the column
                    print("  Renaming purchase_order_number to project_id...")
                    connection.execute(
                        text(
                            """
                        ALTER TABLE email_processing_log 
                        RENAME COLUMN purchase_order_number TO project_id
                    """
                        )
                    )
                    print("  ✅ Column renamed successfully")

                elif not old_column_exists and not new_column_exists:
                    # Add the new column
                    print("  Adding new project_id column...")
                    connection.execute(
                        text(
                            """
                        ALTER TABLE email_processing_log 
                        ADD COLUMN project_id VARCHAR(100)
                    """
                        )
                    )
                    print("  ✅ New column added successfully")

                elif new_column_exists:
                    print("  ✅ project_id column already exists")

                else:
                    print("  ⚠️  Both columns exist, manual intervention required")

                # Commit the transaction
                trans.commit()
                print("✅ Migration completed successfully!")

            except Exception as e:
                # Rollback on error
                trans.rollback()
                raise e

    except OperationalError as e:
        print(f"❌ Database connection error: {e}")
        print("Make sure the database is running and accessible.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("Email Agent - Database Migration")
    print("================================")
    print(f"Database URL: {settings.DATABASE_URL}")
    print()

    response = input("Do you want to proceed with the migration? (y/N): ")
    if response.lower() in ["y", "yes"]:
        migrate_po_to_project_id()
    else:
        print("Migration cancelled.")
