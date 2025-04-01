# tests/conftest.py
import os
import sys
import pytest
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import test utilities
from tests.utils.test_db import TestDatabase, TestDataGenerator, override_session_for_testing

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@pytest.fixture(scope="session")
def test_env():
    """
    Set up the global test environment.
    
    This fixture should be used at the session level to set up and tear down
    resources that are needed for the entire test session.
    """
    # Store original environment variables
    original_env = {}
    for key in os.environ:
        if key.startswith(('ANTHROPIC', 'UNSPLASH', 'PEXELS', 'PIXABAY', 'REDDIT', 'INSTAGRAM', 'TIKTOK')):
            original_env[key] = os.environ[key]
    
    # Ensure critical environment variables are set for tests
    os.environ['ANTHROPIC_API_KEY'] = os.environ.get('ANTHROPIC_API_KEY', 'sk-ant-test-key')
    os.environ['UNSPLASH_ACCESS_KEY'] = os.environ.get('UNSPLASH_ACCESS_KEY', 'test-access-key')
    os.environ['PEXELS_API_KEY'] = os.environ.get('PEXELS_API_KEY', 'test-pexels-key')
    os.environ['PIXABAY_API_KEY'] = os.environ.get('PIXABAY_API_KEY', 'test-pixabay-key')
    
    # Set up a test database file path instead of using the main one
    os.environ['DB_TYPE'] = 'sqlite'
    os.environ['DB_NAME'] = ':memory:'  # Use in-memory database for tests
    
    # Reload config to pick up test values
    import importlib
    import config.settings
    importlib.reload(config.settings)
    
    # Override the Session in models.py to use our test database
    restore_session = override_session_for_testing()
    
    # Create resources directory if needed
    for dir_path in ['resources', 'media/images', 'media/videos']:
        os.makedirs(dir_path, exist_ok=True)
    
    # Create a basic fallback image for tests
    try:
        from PIL import Image
        fallback_img_path = 'resources/default.jpg'
        if not os.path.exists(fallback_img_path):
            img = Image.new('RGB', (1080, 1080), color=(52, 152, 219))
            img.save(fallback_img_path)
    except ImportError:
        # PIL might not be available
        pass
    
    yield {
        'original_env': original_env
    }
    
    # Clean up
    restore_session()
    
    # Restore original environment variables
    for key, value in original_env.items():
        os.environ[key] = value

@pytest.fixture(scope="function")
def test_db():
    """
    Create a test database for a single test function.
    
    This provides an isolated database for each test function.
    """
    # Create a new test database
    db = TestDatabase(use_memory=True)
    
    yield db
    
    # Clean up
    db.cleanup()

@pytest.fixture(scope="function")
def test_session(test_db):
    """
    Create a session for database operations in tests.
    
    This session is connected to an isolated test database.
    """
    with test_db.session() as session:
        yield session

@pytest.fixture(scope="function")
def random_reddit_id():
    """Generate a random Reddit post ID for tests."""
    return TestDataGenerator.random_id()

@pytest.fixture(scope="function")
def test_reddit_post(test_session):
    """Create a test Reddit post."""
    return TestDataGenerator.create_test_reddit_post(test_session)

@pytest.fixture(scope="function")
def test_processed_content(test_session, test_reddit_post):
    """Create test processed content."""
    _, content = TestDataGenerator.create_test_processed_content(
        test_session, 
        reddit_id=test_reddit_post.reddit_id
    )
    return content

@pytest.fixture(scope="function")
def test_media_content(test_session, test_reddit_post):
    """Create test media content."""
    _, media = TestDataGenerator.create_test_media_content(
        test_session, 
        reddit_id=test_reddit_post.reddit_id
    )
    return media

@pytest.fixture(scope="function")
def test_image_path():
    """Create a temporary test image and return its path."""
    try:
        from PIL import Image
        import tempfile
        
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        
        # Create a colored test image
        img = Image.new('RGB', (500, 500), color=(73, 109, 137))
        img.save(path)
        
        yield path
        
        # Clean up
        if os.path.exists(path):
            os.remove(path)
    except ImportError:
        # If PIL is not available, return a static path that may not exist
        yield "tests/data/test_image.jpg"

@pytest.fixture(scope="function")
def mock_image_finder(monkeypatch):
    """
    Create a mocked version of ImageFinder that doesn't make real API calls.
    """
    from unittest.mock import MagicMock
    
    # Create a mock ImageFinder class
    mock_finder = MagicMock()
    
    # The find_image method will return a dict with image info
    mock_finder.find_image.return_value = {
        "media_type": "image",
        "file_path": "resources/default.jpg",
        "url": None,
        "source": "test",
        "source_id": "test_image",
        "source_url": None,
        "width": 1080,
        "height": 1080,
        "keywords": "test,keywords"
    }
    
    # Import this here to avoid circular imports
    import core.media.image_finder
    
    # Monkeypatch the ImageFinder class
    monkeypatch.setattr(core.media.image_finder, "ImageFinder", lambda: mock_finder)
    
    return mock_finder

@pytest.fixture(scope="function")
def mock_video_finder(monkeypatch):
    """
    Create a mocked version of VideoFinder that doesn't make real API calls.
    """
    from unittest.mock import MagicMock
    
    # Create a mock VideoFinder class
    mock_finder = MagicMock()
    
    # The find_video method will return a dict with video info
    mock_finder.find_video.return_value = {
        "media_type": "video",
        "file_path": "resources/default_video.mp4",
        "url": None,
        "source": "test",
        "source_id": "test_video",
        "source_url": None,
        "width": 1280,
        "height": 720,
        "duration": 10.0,
        "keywords": "test,keywords"
    }
    
    # Import this here to avoid circular imports
    import core.media.video_finder
    
    # Monkeypatch the VideoFinder class
    monkeypatch.setattr(core.media.video_finder, "VideoFinder", lambda: mock_finder)
    
    return mock_finder

@pytest.fixture(scope="function")
def mock_claude_client(monkeypatch):
    """
    Create a mocked version of ClaudeClient that doesn't make real API calls.
    """
    from unittest.mock import MagicMock
    
    # Create a mock ClaudeClient
    mock_client = MagicMock()
    
    # Configure the generate_social_media_captions method
    mock_client.generate_social_media_captions.return_value = {
        "instagram_caption": "Test Instagram Caption #test",
        "tiktok_caption": "Test TikTok Caption #test",
        "hashtags": ["#test", "#keywords"]
    }
    
    # Configure the extract_keywords method
    mock_client.extract_keywords.return_value = ["test", "keywords", "claude"]
    
    # Import this here to avoid circular imports
    import utils.claude_client
    
    # Monkeypatch the ClaudeClient class
    monkeypatch.setattr(utils.claude_client, "ClaudeClient", lambda: mock_client)
    
    return mock_client

@pytest.fixture(scope="function")
def robust_test_image_path():
    """Create a test image that will definitely work with image processing libraries."""
    try:
        from PIL import Image
        import tempfile
        import os
        
        # Create a temporary directory that will persist
        temp_dir = tempfile.mkdtemp()
        
        # Create a path for our test image
        image_path = os.path.join(temp_dir, "test_image.jpg")
        
        # Create a simple, reliable test image
        image = Image.new('RGB', (100, 100), color=(73, 109, 137))
        image.save(image_path)
        
        yield image_path
        
        # Clean up after the test
        try:
            os.remove(image_path)
            os.rmdir(temp_dir)
        except:
            pass
    except ImportError:
        # Fall back to a static path in resources if PIL is not available
        yield "resources/default.jpg"