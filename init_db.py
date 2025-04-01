import os
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.models import Base, engine

def main():
    """Initialize the database with all tables."""
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    main()