import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.models import Base, engine

def main():
    """Initialize the database with all tables."""
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    main()

