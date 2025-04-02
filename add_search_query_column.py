#!/usr/bin/env python3
"""
Migration script to add the search_query column to the media_contents table.
This script should be run once after updating the code.
"""
import os
import sys
import logging
from pathlib import Path

# Add project root to the Python path to allow imports from parent directories
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def add_search_query_column():
    """Add the search_query column to media_contents table if it doesn't exist."""
    try:
        from database.models import Session, engine
        from sqlalchemy import Column, Text
        import sqlalchemy as sa
        
        # Check if the column already exists
        inspector = sa.inspect(engine)
        columns = inspector.get_columns('media_contents')
        column_names = [col['name'] for col in columns]
        
        if 'search_query' not in column_names:
            logger.info("Adding search_query column to media_contents table...")
            
            # Use raw SQL to add the column
            with engine.begin() as conn:
                if engine.dialect.name == 'sqlite':
                    conn.execute(sa.text("ALTER TABLE media_contents ADD COLUMN search_query TEXT"))
                else:  # PostgreSQL or other SQL dialects
                    conn.execute(sa.text("ALTER TABLE media_contents ADD COLUMN search_query TEXT"))
            
            logger.info("Column added successfully!")
            
            # Initialize the column with existing keywords
            with Session() as session:
                session.execute(sa.text("UPDATE media_contents SET search_query = keywords WHERE search_query IS NULL"))
                session.commit()
            
            logger.info("Column initialized with existing keywords data")
            return True
        else:
            logger.info("Column search_query already exists in media_contents table")
            return False
    except Exception as e:
        logger.error(f"Error adding column: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting database migration...")
    
    result = add_search_query_column()
    
    if result:
        print("✅ Migration completed successfully!")
    else:
        print("ℹ️ No migration needed or migration failed. Check logs for details.")