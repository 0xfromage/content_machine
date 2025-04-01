# tests/test_media.py
import unittest
import os
import sys
import tempfile
import shutil
from PIL import Image
import random

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.media.image_finder import ImageFinder
from core.media.video_finder import VideoFinder
from core.media.media_processor import MediaProcessor

class TestMediaModules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test resources"""
        cls.temp_dir = tempfile.mkdtemp()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test resources"""
        shutil.rmtree(cls.temp_dir)
    
    def setUp(self):
        """Create a test image for media processing"""
        test_image_path = os.path.join(self.temp_dir, "test_image.jpg")
        
        # Create a simple test image
        test_image = Image.new('RGB', (1000, 1000), color=(random.randint(0, 255), 
                                                           random.randint(0, 255), 
                                                           random.randint(0, 255)))
        test_image.save(test_image_path)
        self.test_image_path = test_image_path
    
    def test_image_finder(self):
        """Test image finding capabilities"""
        image_finder = ImageFinder()
        
        # Test keywords
        keywords = ["technology", "science", "innovation"]
        
        # Find an image
        result = image_finder.find_image(keywords, "test_post")
        
        # Assertions
        self.assertIn('file_path', result)
        self.assertTrue(os.path.exists(result['file_path']))
        self.assertIn('media_type', result)
        self.assertEqual(result['media_type'], 'image')
    
    def test_video_finder(self):
        """Test video finding capabilities"""
        video_finder = VideoFinder()
        
        # Test keywords
        keywords = ["technology", "future", "innovation"]
        
        # Find a video
        result = video_finder.find_video(keywords, "test_post")
        
        # Assertions
        self.assertIn('file_path', result)
        self.assertTrue(os.path.exists(result['file_path']))
        self.assertIn('media_type', result)
        self.assertEqual(result['media_type'], 'video')
    
    def test_media_processor(self):
        """Test media processing capabilities"""
        media_processor = MediaProcessor()
        
        # Test image processing
        processed_image_path = media_processor.process_image(self.test_image_path, "test_post")
        
        # Assertions about processed image
        self.assertIsNotNone(processed_image_path)
        self.assertTrue(os.path.exists(processed_image_path))
        
        # Test watermarking
        watermarked_path = media_processor.add_watermark(processed_image_path, "Test Watermark")
        self.assertIsNotNone(watermarked_path)
        self.assertTrue(os.path.exists(watermarked_path))
    
    def test_media_collage(self):
        """Test media collage creation"""
        media_processor = MediaProcessor()
        
        # Create multiple test images
        test_images = [self.test_image_path]
        for i in range(3):
            new_image_path = os.path.join(self.temp_dir, f"test_image_{i}.jpg")
            test_image = Image.new('RGB', (1000, 1000), 
                                   color=(random.randint(0, 255), 
                                          random.randint(0, 255), 
                                          random.randint(0, 255)))
            test_image.save(new_image_path)
            test_images.append(new_image_path)
        
        # Create collage
        collage_path = media_processor.create_collage(test_images, "Test Collage", "test_post")
        
        # Assertions
        self.assertIsNotNone(collage_path)
        self.assertTrue(os.path.exists(collage_path))

if __name__ == '__main__':
    unittest.main()