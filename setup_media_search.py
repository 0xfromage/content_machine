#!/usr/bin/env python3
"""
Setup script for the enhanced media search functionality.
This script installs the required dependencies and downloads language models.
"""
import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def install_dependencies():
    """Install the required Python packages."""
    logger.info("Installing required Python packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        logger.info("✅ Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install dependencies: {e}")
        return False

def download_nltk_data():
    """Download required NLTK data packages."""
    logger.info("Downloading NLTK data packages...")
    try:
        import nltk
        for package in ['punkt', 'stopwords', 'wordnet', 'averaged_perceptron_tagger', 'maxent_ne_chunker', 'words']:
            nltk.download(package, quiet=True)
        logger.info("✅ NLTK data packages downloaded successfully.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to download NLTK data: {e}")
        return False

def download_spacy_model():
    """Download SpaCy language model."""
    logger.info("Downloading SpaCy English language model...")
    try:
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        logger.info("✅ SpaCy model downloaded successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to download SpaCy model: {e}")
        logger.warning("The system will fall back to NLTK for NLP tasks.")
        return False

def setup_media_directories():
    """Create necessary directories for media files."""
    logger.info("Setting up media directories...")
    directories = [
        "media/images",
        "media/videos",
        "resources",
        "logs",
        "logs/errors"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Directory created or confirmed: {directory}")
    
    logger.info("✅ Media directories setup complete.")
    return True

def create_default_media():
    """Create default fallback media files."""
    logger.info("Creating default fallback media files...")
    
    # Create a default image
    try:
        from PIL import Image
        default_img_path = 'resources/default.jpg'
        img = Image.new('RGB', (1080, 1080), color=(52, 152, 219))
        img.save(default_img_path)
        logger.info(f"Created default image: {default_img_path}")
    except Exception as e:
        logger.error(f"Failed to create default image: {e}")
    
    # Create a default video
    try:
        # Try to import moviepy
        import moviepy.editor as mp
        default_video_path = 'resources/default_video.mp4'
        
        # Create a simple color clip
        color_clip = mp.ColorClip(size=(720, 1280), color=(52, 152, 219), duration=10)
        
        # Save as video
        color_clip.write_videofile(
            default_video_path,
            codec='libx264',
            fps=24,
            preset='ultrafast',
            audio=False
        )
        logger.info(f"Created default video: {default_video_path}")
    except Exception as e:
        logger.error(f"Failed to create default video: {e}")
        logger.warning("This is not critical, as fallback videos will be created as needed.")
    
    logger.info("✅ Default media creation complete.")
    return True

def main():
    """Run the setup process."""
    parser = argparse.ArgumentParser(description="Setup enhanced media search functionality")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")
    parser.add_argument("--skip-nltk", action="store_true", help="Skip NLTK data download")
    parser.add_argument("--skip-spacy", action="store_true", help="Skip SpaCy model download")
    args = parser.parse_args()
    
    logger.info("Starting setup for enhanced media search...")
    
    # Install dependencies
    if not args.skip_deps:
        install_dependencies()
    else:
        logger.info("Skipping dependency installation.")
    
    # Download NLTK data
    if not args.skip_nltk:
        download_nltk_data()
    else:
        logger.info("Skipping NLTK data download.")
    
    # Download SpaCy model (optional)
    if not args.skip_spacy:
        download_spacy_model()
    else:
        logger.info("Skipping SpaCy model download.")
    
    # Setup directories and create default media
    setup_media_directories()
    create_default_media()
    
    logger.info("✅ Setup complete! You can now use the enhanced media search functionality.")
    print("\nTo test the setup, try running: python -m unittest tests.test_media")

if __name__ == "__main__":
    main()