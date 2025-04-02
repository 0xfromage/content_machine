# utils/claude_media_search.py
import logging
import json
from typing import List, Dict, Any, Tuple, Optional
import re
import random

from utils.claude_client import ClaudeClient
from config.settings import config

logger = logging.getLogger(__name__)

class ClaudeMediaSearch:
    """
    Enhances media search by using Claude AI to analyze content and generate
    optimal search queries for images and videos.
    """
    
    def __init__(self):
        """Initialize the Claude media search enhancer."""
        self.claude_client = ClaudeClient()
        # Check if Claude is available
        self.claude_available = (
            hasattr(self.claude_client, 'api_key') and 
            self.claude_client.api_key is not None and
            hasattr(self.claude_client, 'client') and
            self.claude_client.client is not None
        )
        
        if not self.claude_available:
            logger.warning("Claude API not available for media search enhancement")
        else:
            logger.info("Claude media search enhancer initialized")
    
    def generate_search_queries(self, 
                              post_title: str, 
                              post_content: str, 
                              post_id: str,
                              media_type: str = "image") -> Tuple[str, List[str]]:
        """
        Generate search queries for visual media using Claude.
        
        Args:
            post_title: Title of the post
            post_content: Content/text of the post
            post_id: Post ID for tracking
            media_type: Type of media to search for ('image' or 'video')
            
        Returns:
            Tuple of (primary_query, [alternative_queries])
        """
        if not self.claude_available:
            logger.warning("Claude not available, using fallback method")
            return self._fallback_query_generation(post_title, post_content, media_type)
        
        try:
            # Build the prompt
            prompt = self._build_media_search_prompt(post_title, post_content, media_type)
            
            # Call Claude API
            response, tokens = self._call_claude_api(prompt, post_id)
            
            # Parse the response
            primary_query, alt_queries = self._parse_search_response(response)
            
            if primary_query:
                logger.info(f"Generated primary search query: '{primary_query}'")
                return primary_query, alt_queries
            else:
                logger.warning("Failed to generate search query with Claude, using fallback")
                return self._fallback_query_generation(post_title, post_content, media_type)
                
        except Exception as e:
            logger.error(f"Error generating search queries with Claude: {str(e)}")
            return self._fallback_query_generation(post_title, post_content, media_type)
    
    def _build_media_search_prompt(self, title: str, content: str, media_type: str) -> str:
        """
        Build the prompt for Claude to generate media search queries.
        
        Args:
            title: Post title
            content: Post content
            media_type: Type of media ('image' or 'video')
            
        Returns:
            Prompt string
        """
        visual_term = "an image" if media_type == "image" else "a video"
        
        prompt = f"""
        You are an expert at finding visually relevant {media_type}s for content.
        
        I need help finding {visual_term} to illustrate the following content:
        
        TITLE: {title}
        
        CONTENT: {content}
        
        Your task is to analyze this content and give me:
        1. The BEST search query that would find a highly relevant {media_type} for this content
        2. 3 ALTERNATIVE search queries in case the first one doesn't yield good results
        
        Guidelines:
        - Focus on the most visually representable aspects of the content
        - Be specific and descriptive - prefer "golden retriever puppy playing" over just "dog"
        - For abstract concepts, suggest concrete visual representations
        - Consider both literal and metaphorical visual matches
        - Keep queries under 5-7 words for best results
        - Don't include special characters like hashtags or quotes
        
        FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
        ```json
        {{
          "primary_query": "your best search query here",
          "alternative_queries": [
            "alternative query 1",
            "alternative query 2",
            "alternative query 3"
          ]
        }}
        ```
        
        Do not include any other text before or after the JSON.
        """
        
        # Add some media-specific hints
        if media_type == "image":
            prompt += "\nFor images, favor static scenes and clear subjects that would make compelling photo subjects."
        else:  # video
            prompt += "\nFor videos, favor queries that imply motion, activity, or process that would work well in a video format."
        
        return prompt
    
    def _call_claude_api(self, prompt: str, post_id: str) -> Tuple[str, int]:
        """
        Call the Claude API with the prompt.
        
        Args:
            prompt: The prompt to send to Claude
            post_id: Post ID for tracking
            
        Returns:
            Tuple of (response_text, tokens_used)
        """
        # Import here to avoid circular imports
        from utils.claude_client import ClaudeClient
        
        try:
            # Create a new instance to avoid interference with other uses
            claude = ClaudeClient()
            
            # Call Claude API directly using the internal method
            response, tokens = claude._call_claude_api(prompt)
            
            # Log the API call for tracking
            claude._log_api_call(
                reddit_id=post_id,
                task="media_search_query",
                prompt=prompt,
                response=response,
                tokens_used=tokens,
                success=True
            )
            
            return response, tokens
            
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            raise
    
    def _parse_search_response(self, response: str) -> Tuple[str, List[str]]:
        """
        Parse Claude's response to extract search queries.
        
        Args:
            response: Response from Claude
            
        Returns:
            Tuple of (primary_query, [alternative_queries])
        """
        try:
            # Extract JSON content from the response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            
            if not json_match:
                # Try without the code block markers
                json_match = re.search(r'({.*})', response, re.DOTALL)
                
            if json_match:
                json_content = json_match.group(1)
                
                # Parse the JSON
                query_data = json.loads(json_content)
                
                primary_query = query_data.get("primary_query", "")
                alt_queries = query_data.get("alternative_queries", [])
                
                # Ensure we have valid data
                if primary_query and isinstance(primary_query, str):
                    return primary_query, alt_queries
            
            # If we couldn't parse the response properly
            logger.warning(f"Could not parse Claude response: {response}")
            return "", []
            
        except Exception as e:
            logger.error(f"Error parsing search response: {str(e)}")
            return "", []
    
    def _fallback_query_generation(self, title: str, content: str, media_type: str) -> Tuple[str, List[str]]:
        """
        Generate search queries without Claude when API is unavailable.
        
        Args:
            title: Post title
            content: Post content
            media_type: Type of media ('image' or 'video')
            
        Returns:
            Tuple of (primary_query, [alternative_queries])
        """
        # Simple cleaning
        title = re.sub(r'TIL\s+that\s+', '', title)
        title = re.sub(r'TIL\s+', '', title)
        
        # Extract key nouns with a simple regex approach
        words = re.findall(r'\b[A-Za-z]{4,}\b', f"{title} {content}")
        
        # Stop words to filter out
        stop_words = {
            'this', 'that', 'these', 'those', 'have', 'would', 'could', 'should',
            'with', 'what', 'from', 'there', 'their', 'they', 'them', 'than',
            'then', 'when', 'where', 'which', 'while', 'about', 'does', 'some'
        }
        
        # Filter and get most common words
        filtered_words = [word.lower() for word in words if word.lower() not in stop_words]
        
        # Count words for frequency
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Get top words for primary query (up to 4 words)
        top_words = [word for word, _ in sorted_words[:4]]
        
        # Emphasize title words by checking if they're in the top words
        title_words = [w.lower() for w in re.findall(r'\b[A-Za-z]{4,}\b', title)]
        for word in title_words:
            if word not in top_words and word not in stop_words:
                top_words.insert(0, word)
                if len(top_words) > 4:
                    top_words.pop()
        
        # Create primary query
        primary_query = " ".join(top_words)
        
        # Create alternative queries with different word combinations
        alternative_queries = []
        
        # Alt 1: Title-focused query
        if len(title_words) >= 2:
            alt1 = " ".join(title_words[:3])
            alternative_queries.append(alt1)
        
        # Alt 2: Random selection from top 10
        if len(sorted_words) > 5:
            alt_words = random.sample([w for w, _ in sorted_words[:10]], min(4, len(sorted_words)))
            alt2 = " ".join(alt_words)
            alternative_queries.append(alt2)
        
        # Alt 3: Add media type context 
        context_terms = {
            "image": ["scenic", "picture", "photograph", "view"],
            "video": ["motion", "action", "moving", "activity"]
        }
        context = random.choice(context_terms.get(media_type, [""])) 
        if len(top_words) >= 2:
            alt3 = f"{context} {top_words[0]} {top_words[1]}"
            alternative_queries.append(alt3)
        
        # Filter out duplicates and empty queries
        alternative_queries = [q for q in alternative_queries if q and q != primary_query]
        
        return primary_query, alternative_queries