# tests/test_claude_client.py
import unittest
import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.claude_client import ClaudeClient
from unittest.mock import patch, MagicMock

class TestClaudeClient(unittest.TestCase):
    def setUp(self):
        """Set up test resources"""
        # Load sample test data
        with open('tests/data/sample_reddit_posts.json', 'r') as f:
            self.sample_posts = json.load(f)
    
    def test_client_initialization(self):
        """Test Claude client initialization"""
        client = ClaudeClient()
        
        # Basic initialization checks
        self.assertTrue(hasattr(client, 'client'))
        self.assertTrue(hasattr(client, 'api_key'))
        self.assertTrue(hasattr(client, 'model'))
    
    @patch('utils.claude_client.ClaudeClient._call_claude_api')
    def test_generate_social_media_captions(self, mock_call_api):
        """Test social media caption generation"""
        # Mock API response
        mock_response = json.dumps({
            "instagram_caption": "Test Instagram Caption",
            "tiktok_caption": "Test TikTok Caption",
            "hashtags": ["#Test", "#Caption"]
        })
        mock_call_api.return_value = (mock_response, 100)
        
        # Use first sample post
        sample_post = self.sample_posts[0]
        
        client = ClaudeClient()
        captions = client.generate_social_media_captions(sample_post, sample_post['reddit_id'])
        
        # Assertions
        self.assertIn('instagram_caption', captions)
        self.assertIn('tiktok_caption', captions)
        self.assertIn('hashtags', captions)
        self.assertEqual(captions['instagram_caption'], "Test Instagram Caption")
        self.assertEqual(captions['tiktok_caption'], "Test TikTok Caption")
    
    @patch('utils.claude_client.ClaudeClient._call_claude_api')
    def test_extract_keywords(self, mock_call_api):
        """Test keyword extraction"""
        # Mock API response with keywords
        mock_response = "artificial\nintelligence\nmachine\nlearning\ntechnology"
        mock_call_api.return_value = (mock_response, 50)
        
        # Use first sample post content
        sample_post = self.sample_posts[0]
        sample_text = sample_post['content']
        
        client = ClaudeClient()
        keywords = client.extract_keywords(sample_text, sample_post['reddit_id'])
        
        # Assertions
        self.assertIsInstance(keywords, list)
        self.assertTrue(len(keywords) > 0)
        self.assertTrue(all(isinstance(kw, str) for kw in keywords))
    
    def test_fallback_caption_generation(self):
        """Test fallback caption generation when no API key is available"""
        # Temporarily remove API key
        original_api_key = os.environ.get('ANTHROPIC_API_KEY')
        os.environ['ANTHROPIC_API_KEY'] = ''
        
        try:
            client = ClaudeClient()
            sample_post = self.sample_posts[0]
            
            # Force fallback method
            captions = client._fallback_caption_generation(sample_post)
            
            # Assertions
            self.assertIn('instagram_caption', captions)
            self.assertIn('tiktok_caption', captions)
            self.assertIn('hashtags', captions)
            self.assertTrue(len(captions['instagram_caption']) > 0)
            self.assertTrue(len(captions['tiktok_caption']) > 0)
        
        finally:
            # Restore original API key
            if original_api_key:
                os.environ['ANTHROPIC_API_KEY'] = original_api_key
    
    def test_parse_caption_response(self):
        """Test parsing of Claude API response"""
        client = ClaudeClient()
        
        # Test valid JSON response
        valid_response = '''
        ```json
        {
            "instagram_caption": "Test Instagram Caption",
            "tiktok_caption": "Test TikTok Caption",
            "hashtags": ["#Test", "#Caption"]
        }
        ```
        '''
        
        parsed_result = client._parse_caption_response(valid_response)
        
        # Assertions
        self.assertEqual(parsed_result['instagram_caption'], "Test Instagram Caption")
        self.assertEqual(parsed_result['tiktok_caption'], "Test TikTok Caption")
        self.assertEqual(parsed_result['hashtags'], ["#Test", "#Caption"])
    
    def test_build_caption_prompt(self):
        """Test prompt building for caption generation"""
        client = ClaudeClient()
        sample_post = self.sample_posts[0]
        
        prompt = client._build_caption_prompt(sample_post)
        
        # Assertions
        self.assertIn(sample_post['title'], prompt)
        self.assertIn(sample_post['content'], prompt)
        self.assertIn(sample_post['subreddit'], prompt)
        self.assertTrue('JSON' in prompt)  # Ensure JSON instruction is present

if __name__ == '__main__':
    unittest.main()