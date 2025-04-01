"""
Mock objects for testing purposes.
This module provides mock implementations of external dependencies
to facilitate testing without real API calls or external services.
"""
import os
import json
from unittest.mock import MagicMock

class MockInstagramClient:
    """Mock implementation of the Instagram Client."""
    
    def __init__(self):
        self.logged_in = False
        self.settings = {}
    
    def login(self, username, password):
        """Mock login method."""
        self.logged_in = True
        return True
    
    def dump_settings(self, file_path):
        """Mock settings dumping."""
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write some dummy content
        with open(file_path, 'w') as f:
            json.dump({"session_id": "dummy_session"}, f)
    
    def load_settings(self, file_path):
        """Mock settings loading."""
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                self.settings = json.load(f)
            return True
        return False
    
    def get_timeline_feed(self):
        """Mock timeline feed retrieval."""
        if not self.logged_in:
            raise Exception("Login required")
        return []
    
    def photo_upload(self, path, caption):
        """Mock photo upload method."""
        # Create a mock media object
        media = MagicMock()
        media.id = "test_media_123"
        media.code = "test_abc123"
        return media

class MockRedditClient:
    """Mock implementation of the Reddit client."""
    
    def __init__(self, **kwargs):
        self.subreddits = {}
    
    def subreddit(self, subreddit_name):
        """Get a mock subreddit."""
        if subreddit_name not in self.subreddits:
            self.subreddits[subreddit_name] = MockSubreddit(subreddit_name)
        return self.subreddits[subreddit_name]

class MockSubreddit:
    """Mock implementation of a Reddit subreddit."""
    
    def __init__(self, name):
        self.name = name
        self.display_name = name
        self.posts = []
    
    def add_post(self, post_data):
        """Add a mock post to this subreddit."""
        post = MockPost(post_data, self)
        self.posts.append(post)
        return post
    
    def top(self, time_filter="day", limit=10):
        """Get top posts for this subreddit."""
        return self.posts[:limit]

class MockPost:
    """Mock implementation of a Reddit post."""
    
    def __init__(self, post_data, subreddit):
        self.id = post_data.get('reddit_id', 'test_id')
        self.title = post_data.get('title', 'Test Post')
        self.selftext = post_data.get('content', 'Test content')
        self.url = post_data.get('url', 'https://example.com')
        self.score = post_data.get('upvotes', 1000)
        self.num_comments = post_data.get('num_comments', 100)
        self.created_utc = 1617235200  # April 1, 2021 UTC
        self.permalink = post_data.get('permalink', f"/r/{subreddit.name}/comments/{self.id}/test-post/")
        self.over_18 = post_data.get('over_18', False)
        self.subreddit = subreddit
        self.author = MockAuthor(post_data.get('author', 'test_user'))

class MockAuthor:
    """Mock implementation of a Reddit author."""
    
    def __init__(self, name):
        self.name = name

class MockClaudeClient:
    """Mock implementation of the Claude AI client."""
    
    def __init__(self):
        self.messages = []
    
    def create(self, **kwargs):
        """Create a mock message."""
        response = MagicMock()
        response.content = [MagicMock()]
        response.content[0].text = json.dumps({
            "instagram_caption": "Test Instagram Caption #test",
            "tiktok_caption": "Test TikTok Caption #test",
            "hashtags": ["#test", "#keywords"]
        })
        response.usage = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        return response

def patch_external_dependencies(monkeypatch):
    """
    Patch external dependencies for testing.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
    """
    # Patch instagrapi Client
    monkeypatch.setattr('instagrapi.Client', MockInstagramClient)
    
    # Patch praw.Reddit
    monkeypatch.setattr('praw.Reddit', MockRedditClient)
    
    # Patch anthropic.Anthropic.messages
    mock_anthropic = MagicMock()
    mock_anthropic.messages.create.return_value = MockClaudeClient().create()
    monkeypatch.setattr('anthropic.Anthropic', lambda api_key: mock_anthropic)