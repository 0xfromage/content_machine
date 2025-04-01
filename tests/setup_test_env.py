#!/usr/bin/env python3
"""
Script to set up the test environment for Content Machine.
This script ensures that all necessary resources are available for tests.
"""
import os
import sys
import logging
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_test_directories():
    """Create necessary directories for testing."""
    directories = [
        "media/images",
        "media/videos",
        "resources",
        "logs",
        "logs/errors"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def create_test_files():
    """Create necessary test files."""
    # Create a fallback image for tests
    try:
        from PIL import Image
        fallback_img_path = 'resources/default.jpg'
        if not os.path.exists(fallback_img_path):
            img = Image.new('RGB', (1080, 1080), color=(52, 152, 219))
            img.save(fallback_img_path)
            logger.info(f"Created test image: {fallback_img_path}")
    except ImportError:
        logger.warning("PIL not available. Could not create test image.")
    
    # Create a fallback video for tests
    video_path = 'resources/default_video.mp4'
    if not os.path.exists(video_path):
        try:
            # Try to create a simple video using moviepy if available
            try:
                from moviepy.editor import ColorClip
                
                clip = ColorClip(size=(720, 1280), color=(52, 152, 219), duration=10)
                clip.write_videofile(
                    video_path,
                    fps=24,
                    codec='libx264',
                    audio=False,
                    preset='ultrafast'
                )
                logger.info(f"Created test video with moviepy: {video_path}")
            except ImportError:
                # If moviepy not available, create an empty file
                with open(video_path, 'wb') as f:
                    # Write dummy content to the file
                    f.write(b'Dummy video content')
                logger.info(f"Created dummy test video: {video_path}")
        except Exception as e:
            logger.error(f"Could not create test video: {str(e)}")

def set_test_environment_variables():
    """Set necessary environment variables for testing."""
    env_vars = {
        'ANTHROPIC_API_KEY': 'test-api-key',
        'UNSPLASH_ACCESS_KEY': 'test-unsplash-key',
        'PEXELS_API_KEY': 'test-pexels-key',
        'PIXABAY_API_KEY': 'test-pixabay-key',
        'INSTAGRAM_USERNAME': 'test_instagram_user',
        'INSTAGRAM_PASSWORD': 'test_instagram_pass',
        'TIKTOK_USERNAME': 'test_tiktok_user',
        'TIKTOK_PASSWORD': 'test_tiktok_pass'
    }
    
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
            logger.info(f"Set environment variable: {key}")

def initialize_database():
    """Initialize the test database."""
    try:
        from database.models import init_db
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

def setup_nltk():
    """Download required NLTK data packages."""
    try:
        import nltk
        
        # Create NLTK data directory if it doesn't exist
        nltk_data_dir = os.path.join(project_root, 'nltk_data')
        os.makedirs(nltk_data_dir, exist_ok=True)
        
        # Set NLTK data path
        nltk.data.path.append(nltk_data_dir)
        
        # Download required NLTK packages
        for package in ['punkt', 'stopwords', 'wordnet']:
            try:
                nltk.download(package, quiet=True, download_dir=nltk_data_dir)
                logger.info(f"Downloaded NLTK package: {package}")
            except Exception as e:
                logger.warning(f"Error downloading NLTK package {package}: {str(e)}")
    except ImportError:
        logger.warning("NLTK not available")

def main():
    """Run the setup script."""
    logger.info("Setting up test environment...")
    
    # Run setup steps
    setup_test_directories()
    create_test_files()
    set_test_environment_variables()
    setup_nltk()
    initialize_database()
    
    logger.info("Test environment setup complete")

if __name__ == "__main__":
    main()