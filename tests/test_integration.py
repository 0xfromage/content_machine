import unittest
import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.scraper.reddit_scraper import RedditScraper
from core.processor.text_processor import TextProcessor
from core.media.image_finder import ImageFinder
from core.media.video_finder import VideoFinder
from core.publisher.instagram_publisher import InstagramPublisher
from utils.claude_client import ClaudeClient
from database.models import Session, RedditPost, ProcessedContent, MediaContent

class IntegrationTestSuite(unittest.TestCase):
    """
    Integration tests to verify end-to-end workflow of Content Machine
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up resources shared across tests"""
        # Load sample test data
        with open('tests/data/sample_reddit_posts.json', 'r') as f:
            cls.sample_posts = json.load(f)
    
    def test_full_content_workflow(self):
        """
        Test the complete workflow:
        1. Scrape Reddit post
        2. Process content
        3. Find media
        4. Generate captions
        5. (Mock) Publish to social media
        """
        from database.models import RedditPost, Session
        with Session() as session:
            session.query(RedditPost).filter_by(reddit_id='abcd123').delete()
            session.commit()
        # Use first sample post
        sample_post = self.sample_posts[0]
        
        # Step 1: Save scraped post to database
        with Session() as session:
            reddit_post = RedditPost(
                reddit_id=sample_post['reddit_id'],
                title=sample_post['title'],
                content=sample_post['content'],
                subreddit=sample_post['subreddit'],
                upvotes=sample_post['upvotes'],
                status='new'
            )
            session.add(reddit_post)
            session.commit()
        
        # Step 2: Process content
        processor = TextProcessor()
        processed_result = processor.process_post(sample_post)
        
        # Validate processing
        self.assertIn('instagram_caption', processed_result)
        self.assertIn('tiktok_caption', processed_result)
        self.assertGreater(len(processed_result['hashtags']), 0)
        
        # Step 3: Find media
        image_finder = ImageFinder()
        keywords = processed_result['keywords']
        
        media_result = image_finder.find_image(keywords, sample_post['reddit_id'])
        
        # Validate media finding
        self.assertIn('file_path', media_result)
        self.assertTrue(os.path.exists(media_result['file_path']))
        
        # Optional: Video finding test
        video_finder = VideoFinder()
        video_result = video_finder.find_video(keywords, sample_post['reddit_id'])
        
        # Validate video finding
        self.assertIn('file_path', video_result)
        self.assertTrue(os.path.exists(video_result['file_path']))
    
    def test_claude_integration(self):
        """
        Test Claude AI integration:
        1. Generate captions
        2. Extract keywords
        """
        claude_client = ClaudeClient()
        
        # Use first sample post
        sample_post = self.sample_posts[0]
        
        # Test caption generation
        captions = claude_client.generate_social_media_captions(sample_post, sample_post['reddit_id'])
        
        self.assertIn('instagram_caption', captions)
        self.assertIn('tiktok_caption', captions)
        self.assertIn('hashtags', captions)
        
        # Test keyword extraction
        keywords = claude_client.extract_keywords(sample_post['content'], sample_post['reddit_id'])
        
        self.assertIsInstance(keywords, list)
        self.assertTrue(len(keywords) > 0)
    
    def test_database_workflow(self):
        """
        Test database interactions throughout the workflow
        """
        import uuid
        unique_id = f"test_{uuid.uuid4().hex[:8]}"
        from database.models import RedditPost, Session, ProcessedContent, MediaContent
        
        # Clean up any existing data with this ID
        with Session() as session:
            session.query(RedditPost).filter_by(reddit_id=unique_id).delete()
            session.query(ProcessedContent).filter_by(reddit_id=unique_id).delete()
            session.query(MediaContent).filter_by(reddit_id=unique_id).delete()
            session.commit()
        
        # Use first sample post as template but with unique ID
        sample_post = self.sample_posts[0]
        
        with Session() as session:
            # 1. Create Reddit Post with unique ID
            reddit_post = RedditPost(
                reddit_id=unique_id,  # Use unique ID here
                title=sample_post['title'],
                content=sample_post['content'],
                subreddit=sample_post['subreddit'],
                upvotes=sample_post['upvotes']
            )
            session.add(reddit_post)
            session.commit()
            
            # 2. Create Processed Content with same unique ID
            processed_content = ProcessedContent(
                reddit_id=unique_id,  # Use unique ID here
                instagram_caption="Test Instagram Caption",
                tiktok_caption="Test TikTok Caption",
                status='pending_validation'
            )
            session.add(processed_content)
            
            # 3. Create Media Content with same unique ID
            media_content = MediaContent(
                reddit_id=unique_id,  # Use unique ID here
                media_type='image',
                file_path='/path/to/test/image.jpg'
            )
            session.add(media_content)
            
            session.commit()
            
            # Verify relations using unique ID
            saved_post = session.query(RedditPost).filter_by(reddit_id=unique_id).first()
            self.assertIsNotNone(saved_post)
            self.assertEqual(saved_post.processed_content.instagram_caption, "Test Instagram Caption")
            self.assertEqual(saved_post.media_content.media_type, 'image')

if __name__ == '__main__':
    unittest.main()