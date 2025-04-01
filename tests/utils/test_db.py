# tests/utils/test_db.py
import os
import sqlite3
import tempfile
import logging
import random
import string
import uuid
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLASession

# Import the Base class from your models
from database.models import Base

logger = logging.getLogger(__name__)

class TestDatabase:
    """Helper class for managing test databases."""
    
    def __init__(self, use_memory=True):
        """
        Initialize the test database manager.
        
        Args:
            use_memory: If True, use an in-memory database. Otherwise use a temporary file.
        """
        self.use_memory = use_memory
        self.temp_dir = None
        self.db_path = None
        self.engine = None
        self.session_factory = None
        self.tables_created = False
        
        # Set up the test database
        self._setup_database()
    
    def _setup_database(self):
        """Set up a new test database."""
        if self.use_memory:
            # Use in-memory SQLite database
            db_url = "sqlite:///:memory:"
            self.db_path = ":memory:"
        else:
            # Create a temporary directory and file
            self.temp_dir = tempfile.mkdtemp()
            self.db_path = os.path.join(self.temp_dir, "test_content_machine.db")
            db_url = f"sqlite:///{self.db_path}"
        
        # Create engine and session factory
        self.engine = create_engine(db_url)
        self.session_factory = sessionmaker(bind=self.engine)
        
        # Create all tables
        Base.metadata.create_all(self.engine)
        self.tables_created = True
        
        logger.info(f"Test database initialized at {self.db_path}")
    
    def reset(self):
        """Reset the database by dropping and recreating all tables."""
        if self.engine:
            logger.debug("Resetting test database")
            # Drop all tables
            Base.metadata.drop_all(self.engine)
            # Recreate all tables
            Base.metadata.create_all(self.engine)
            self.tables_created = True
    
    @contextmanager
    def session(self):
        """
        Provide a session context manager for database operations.
        
        Yields:
            SQLAlchemy session
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def cleanup(self):
        """Clean up temporary files and resources."""
        logger.debug("Cleaning up test database resources")
        if self.engine:
            self.engine.dispose()
        
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            
        logger.info("Test database resources cleaned up")


class TestDataGenerator:
    """Helper class for generating test data."""
    
    @staticmethod
    def random_string(length=10):
        """Generate a random string."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_id():
        """Generate a random ID that won't conflict with existing IDs."""
        # Use a UUID-based approach for guaranteed uniqueness
        return f"test_{uuid.uuid4().hex[:8]}"
    
    @staticmethod
    def create_test_reddit_post(session, **overrides):
        """
        Create a test Reddit post in the database.
        
        Args:
            session: SQLAlchemy session.
            **overrides: Fields to override in the default post data.
            
        Returns:
            Created RedditPost object.
        """
        from database.models import RedditPost
        
        # Default post data with a unique ID
        post_data = {
            "reddit_id": TestDataGenerator.random_id(),
            "title": f"Test post {TestDataGenerator.random_string(5)}",
            "content": f"Test content {TestDataGenerator.random_string(20)}",
            "subreddit": "testsubreddit",
            "upvotes": random.randint(1000, 10000),
            "status": "new"
        }
        
        # Override defaults with provided values
        post_data.update(overrides)
        
        # Create the post
        post = RedditPost(**post_data)
        session.add(post)
        session.commit()
        
        return post
    
    @staticmethod
    def create_test_processed_content(session, reddit_id=None, **overrides):
        """
        Create test processed content in the database.
        
        Args:
            session: SQLAlchemy session.
            reddit_id: Reddit ID to use. If None, a new post will be created.
            **overrides: Fields to override in the default content data.
            
        Returns:
            Tuple of (RedditPost, ProcessedContent) objects.
        """
        from database.models import RedditPost, ProcessedContent
        
        # Create or get a Reddit post
        if reddit_id is None:
            post = TestDataGenerator.create_test_reddit_post(session)
            reddit_id = post.reddit_id
        else:
            post = session.query(RedditPost).filter_by(reddit_id=reddit_id).first()
            if not post:
                post = TestDataGenerator.create_test_reddit_post(session, reddit_id=reddit_id)
        
        # Default processed content data
        content_data = {
            "reddit_id": reddit_id,
            "keywords": "test,keywords",
            "hashtags": "#test,#keywords",
            "instagram_caption": f"Instagram caption {TestDataGenerator.random_string(10)}",
            "tiktok_caption": f"TikTok caption {TestDataGenerator.random_string(5)}",
            "status": "pending_validation"
        }
        
        # Override defaults with provided values
        content_data.update(overrides)
        
        # Create the processed content
        content = ProcessedContent(**content_data)
        session.add(content)
        session.commit()
        
        return (post, content)
    
    @staticmethod
    def create_test_media_content(session, reddit_id=None, **overrides):
        """
        Create test media content in the database.
        
        Args:
            session: SQLAlchemy session.
            reddit_id: Reddit ID to use. If None, a new post will be created.
            **overrides: Fields to override in the default media data.
            
        Returns:
            Tuple of (RedditPost, MediaContent) objects.
        """
        from database.models import RedditPost, MediaContent
        
        # Create or get a Reddit post
        if reddit_id is None:
            post = TestDataGenerator.create_test_reddit_post(session)
            reddit_id = post.reddit_id
        else:
            post = session.query(RedditPost).filter_by(reddit_id=reddit_id).first()
            if not post:
                post = TestDataGenerator.create_test_reddit_post(session, reddit_id=reddit_id)
        
        # Default media content data
        media_data = {
            "reddit_id": reddit_id,
            "media_type": "image",
            "file_path": f"media/images/test_{TestDataGenerator.random_string(8)}.jpg",
            "source": "test",
            "source_id": f"test_{TestDataGenerator.random_string(6)}",
            "width": 1080,
            "height": 1080,
            "keywords": "test,keywords"
        }
        
        # Override defaults with provided values
        media_data.update(overrides)
        
        # Create the media content
        media = MediaContent(**media_data)
        session.add(media)
        session.commit()
        
        return (post, media)


# Convenience functions for test setup
def setup_test_database():
    """
    Set up a new test database and return it.
    
    Returns:
        TestDatabase instance.
    """
    return TestDatabase()

def get_test_session(test_db=None):
    """
    Get a test session from a TestDatabase.
    
    Args:
        test_db: TestDatabase instance. If None, a new one will be created.
        
    Returns:
        SQLAlchemy session.
    """
    if test_db is None:
        test_db = TestDatabase()
    return test_db.session_factory()

def override_session_for_testing():
    """
    Override the default Session in the models module with a test session.
    Returns a function to restore the original Session.
    
    Returns:
        Function to restore the original Session.
    """
    import database.models
    original_Session = database.models.Session
    
    # Create a test database and use its session
    test_db = TestDatabase()
    database.models.Session = test_db.session_factory
    
    def restore_session():
        database.models.Session = original_Session
        test_db.cleanup()
    
    return restore_session