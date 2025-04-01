import pytest
import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import test utilities
from tests.mocks import patch_external_dependencies

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up the test environment automatically for all tests.
    This fixture runs once at the beginning of the test session.
    """
    # Run the setup script
    from tests.setup_test_env import main as setup_env
    setup_env()
    
    # Set environment variables for tests
    os.environ.setdefault('ANTHROPIC_API_KEY', 'test-api-key')
    os.environ.setdefault('UNSPLASH_ACCESS_KEY', 'test-unsplash-key')
    os.environ.setdefault('PEXELS_API_KEY', 'test-pexels-key')
    os.environ.setdefault('PIXABAY_API_KEY', 'test-pixabay-key')
    os.environ.setdefault('INSTAGRAM_USERNAME', 'test_instagram_user')
    os.environ.setdefault('INSTAGRAM_PASSWORD', 'test_instagram_pass')
    os.environ.setdefault('TIKTOK_USERNAME', 'test_tiktok_user')
    os.environ.setdefault('TIKTOK_PASSWORD', 'test_tiktok_pass')
    
    # Set up a test database file path instead of using the main one
    os.environ.setdefault('DB_TYPE', 'sqlite')
    os.environ.setdefault('DB_NAME', ':memory:')  # Use in-memory database for tests
    
    # Initialize the database
    from database.models import init_db
    init_db()

@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    """
    Patch external dependencies for all tests.
    This fixture runs for each test function.
    """
    patch_external_dependencies(monkeypatch)

@pytest.fixture
def sample_reddit_post():
    """Provide a sample Reddit post for tests."""
    return {
        'reddit_id': 'test_post',
        'title': 'Test Post Title',
        'content': 'This is test content for the Reddit post.',
        'subreddit': 'testsubreddit',
        'upvotes': 5000,
        'num_comments': 200,
        'author': 'test_user',
        'permalink': '/r/testsubreddit/comments/test_post/test_post_title/',
        'url': 'https://reddit.com/r/testsubreddit/comments/test_post/test_post_title/'
    }

@pytest.fixture
def test_image_path(tmp_path):
    """Create a test image and return its path."""
    try:
        from PIL import Image
        
        # Create a test image in the temporary directory
        image_path = tmp_path / "test_image.jpg"
        
        # Create a colored test image
        img = Image.new('RGB', (500, 500), color=(73, 109, 137))
        img.save(image_path)
        
        return str(image_path)
    except ImportError:
        # Return a fallback path if PIL is not available
        return "resources/default.jpg"

@pytest.fixture
def setup_database():
    """Set up the database for tests that need it."""
    from database.models import RedditPost, ProcessedContent, MediaContent, Session
    
    # Create a test post
    post_id = f"test_{os.urandom(4).hex()}"
    
    with Session() as session:
        # Create a Reddit post
        reddit_post = RedditPost(
            reddit_id=post_id,
            title="Test Post",
            content="Test content",
            subreddit="testsubreddit",
            upvotes=1000,
            status="new"
        )
        session.add(reddit_post)
        
        # Create processed content
        processed_content = ProcessedContent(
            reddit_id=post_id,
            keywords="test,keywords",
            hashtags="#test,#keywords",
            instagram_caption="Test Instagram Caption",
            tiktok_caption="Test TikTok Caption",
            status="pending_validation"
        )
        session.add(processed_content)
        
        # Create media content
        media_content = MediaContent(
            reddit_id=post_id,
            media_type="image",
            file_path="resources/default.jpg",
            source="test",
            source_id="test_image",
            width=1080,
            height=1080,
            keywords="test,keywords"
        )
        session.add(media_content)
        
        session.commit()
    
    # Return the post ID for reference
    return post_id