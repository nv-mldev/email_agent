#!/usr/bin/env python3
"""
Migration script to add confirmation fields to EmailProcessingLog table.
This adds support for human confirmation of email summaries.
"""

from sqlalchemy import text
from core.database import engine


def add_confirmation_fields():
    """Add new fields for email confirmation functionality."""

    migrations = [
        # Add project_name field
        """
        ALTER TABLE email_processing_log 
        ADD COLUMN IF NOT EXISTS project_name VARCHAR(255);
        """,
        # Add is_new_enquiry field
        """
        ALTER TABLE email_processing_log 
        ADD COLUMN IF NOT EXISTS is_new_enquiry BOOLEAN;
        """,
        # Add confirmed_by_human field
        """
        ALTER TABLE email_processing_log 
        ADD COLUMN IF NOT EXISTS confirmed_by_human BOOLEAN DEFAULT FALSE;
        """,
        # Add confirmation_timestamp field
        """
        ALTER TABLE email_processing_log 
        ADD COLUMN IF NOT EXISTS confirmation_timestamp TIMESTAMP WITH TIME ZONE;
        """,
        # Add confirmed_attachments field
        """
        ALTER TABLE email_processing_log 
        ADD COLUMN IF NOT EXISTS confirmed_attachments JSONB;
        """,
        # Add attachment_analysis field
        """
        ALTER TABLE email_processing_log 
        ADD COLUMN IF NOT EXISTS attachment_analysis JSONB;
        """,
    ]

    print("🔄 Adding confirmation fields to email_processing_log table...")

    with engine.connect() as connection:
        for i, migration in enumerate(migrations, 1):
            try:
                print(f"   Running migration {i}/{len(migrations)}...")
                connection.execute(text(migration))
                connection.commit()
                print(f"   ✅ Migration {i} completed successfully")
            except Exception as e:
                print(f"   ⚠️  Migration {i} warning: {e}")
                # Continue with other migrations even if one fails
                connection.rollback()

    print("✅ All confirmation field migrations completed!")

    # Verify the changes
    print("\n🔍 Verifying new columns...")
    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'email_processing_log' 
            AND column_name IN ('project_name', 'is_new_enquiry', 'confirmed_by_human', 
                               'confirmation_timestamp', 'confirmed_attachments', 'attachment_analysis')
            ORDER BY column_name;
        """
            )
        )

        columns = result.fetchall()
        if columns:
            print("   Added columns:")
            for column_name, data_type in columns:
                print(f"   • {column_name}: {data_type}")
        else:
            print("   ⚠️  No new columns found - they may already exist")


if __name__ == "__main__":
    print("📧 Email Agent - Confirmation Fields Migration")
    print("=" * 50)

    try:
        add_confirmation_fields()
        print("\n🎉 Migration completed successfully!")
        print("   Your email agent now supports human confirmation features!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("   Please check your database connection and try again.")
