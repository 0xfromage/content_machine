# core/media/image_finder.py
import os
import logging
import requests
import random
import re
import sys
from typing import Dict, List, Any, Optional
from PIL import Image
from io import BytesIO
import time
from datetime import datetime

# Make sure parent directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.settings import config
from utils.error_handler import handle_media_error
from utils.claude_media_search import ClaudeMediaSearch
from database.models import Session, RedditPost, ProcessedContent, MediaContent

logger = logging.getLogger(__name__)

class ImageFinder:
    """Class for finding relevant images based on content keywords."""
    
    def __init__(self):
        """Initialize the image finder with API keys."""
        # Make sure we're using the same attribute names consistently
        self.unsplash_access_key = config.media.unsplash_access_key
        self.pexels_api_key = config.media.pexels_api_key
        self.pixabay_api_key = config.media.pixabay_api_key
        self.image_width = config.media.image_width
        self.image_height = config.media.image_height
        self.fallback_image_path = config.media.fallback_image_path
        
        # Initialize the Claude-powered media search enhancer
        self.claude_search = ClaudeMediaSearch()
        
        # Ensure image directories exist
        os.makedirs("media/images", exist_ok=True)
        
        # Log API availability status
        logger.info(f"Image finder initialized with APIs: " + 
                   f"Unsplash: {'Available' if self.unsplash_access_key else 'Missing'}, " +
                   f"Pexels: {'Available' if self.pexels_api_key else 'Missing'}, " +
                   f"Pixabay: {'Available' if self.pixabay_api_key else 'Missing'}")
        
        # Ensure fallback image directory exists
        if self.fallback_image_path:
            os.makedirs(os.path.dirname(self.fallback_image_path), exist_ok=True)
    
    def find_image(self, keywords: List[str], post_id: str) -> Dict[str, Any]:
        """
        Find a relevant image based on keywords and post content.
        
        Args:
            keywords: List of keywords for searching.
            post_id: ID of the post to associate with the image.
            
        Returns:
            Dictionary containing information about the found image.
        """
        try:
            # Get the original post title and content for better context
            post_title = ""
            post_content = ""
            try:
                with Session() as session:
                    post = session.query(RedditPost).filter_by(reddit_id=post_id).first()
                    if post:
                        post_title = post.title
                        post_content = post.content
            except Exception as e:
                logger.warning(f"Could not retrieve post details: {str(e)}")
                # Fall back to keywords if post details can't be retrieved
                if keywords:
                    post_title = " ".join(keywords)
            
            # Use Claude to generate optimized search queries
            if post_title or post_content:
                primary_query, alt_queries = self.claude_search.generate_search_queries(
                    post_title, post_content, post_id, media_type="image"
                )
                logger.info(f"Claude generated query for post {post_id}: '{primary_query}'")
                search_query = primary_query
            else:
                # Fallback to basic keyword joining if post details not available
                search_query = " ".join(keywords[:5])
                alt_queries = []
            
            logger.debug(f"Searching images for query: {search_query}")
            
            # Try to find an image with the primary query
            image_result = self._try_all_image_sources(search_query)
            
            # If no results with primary query, try alternative queries
            if not image_result and alt_queries:
                for alt_query in alt_queries:
                    logger.info(f"Trying alternative query: '{alt_query}'")
                    image_result = self._try_all_image_sources(alt_query)
                    if image_result:
                        search_query = alt_query  # Update the successful query
                        break
            
            # If still no results, fall back to the original keywords
            if not image_result and keywords:
                original_query = " ".join(keywords[:5]) 
                logger.info(f"Trying original keywords: '{original_query}'")
                image_result = self._try_all_image_sources(original_query)
                if image_result:
                    search_query = original_query
            
            # If no image found with any queries, use fallback
            if not image_result:
                logger.debug("No image found with any query, using fallback")
                image_result = self._use_fallback_image()
            
            # Add the successful search query to the result
            image_result['search_query'] = search_query
            
            # Save the image info to the database
            self._save_media_to_db(image_result, post_id)
            
            logger.info(f"Found image for post {post_id}: {image_result['source']} (Query: {search_query})")
            return image_result
            
        except Exception as e:
            error_msg = f"Error finding image: {str(e)}"
            logger.error(error_msg)
            handle_media_error("image_finding", error_msg, post_id=post_id)
            
            # Use fallback image in case of error
            fallback_result = self._use_fallback_image()
            self._save_media_to_db(fallback_result, post_id)
            return fallback_result
    
    def _try_all_image_sources(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Try all available image sources with the given query.
        
        Args:
            query: Search query string.
            
        Returns:
            Image information or None if no image found.
        """
        # Try each API in sequence, stopping once an image is found
        image_result = None
        
        # 1. Try Unsplash first if available
        if self.unsplash_access_key:
            logger.debug("Trying Unsplash API")
            image_result = self._search_unsplash(query)
        
        # 2. Try Pexels if Unsplash failed and API is available
        if not image_result and self.pexels_api_key:
            logger.debug("Trying Pexels API")
            image_result = self._search_pexels(query)
        
        # 3. Try Pixabay if both previous APIs failed
        if not image_result and self.pixabay_api_key:
            logger.debug("Trying Pixabay API")
            image_result = self._search_pixabay(query)
        
        return image_result
    
    def _search_unsplash(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for an image on Unsplash.
        
        Args:
            query: Search query string.
            
        Returns:
            Image information or None if no image found.
        """
        try:
            if not self.unsplash_access_key:
                logger.warning("No Unsplash access key provided")
                return None
                
            url = "https://api.unsplash.com/search/photos"
            headers = {"Authorization": f"Client-ID {self.unsplash_access_key}"}
            params = {
                "query": query,
                "per_page": 30,  # Increased from 10 to get more varied results
                "orientation": "squarish" 
            }
            
            logger.debug(f"Sending request to Unsplash API: {url}")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            # Log the status code for debugging
            logger.debug(f"Unsplash API response status: {response.status_code}")
            
            # Raise an exception for 4xx/5xx status codes
            response.raise_for_status()
            
            data = response.json()
            if data["results"]:
                # Sort results by relevance score if available
                if "relevance" in data:
                    results = sorted(data["results"], key=lambda x: x.get("relevance", 0), reverse=True)
                    # Pick from the top 5 most relevant results
                    image = random.choice(results[:5]) if len(results) >= 5 else results[0]
                else:
                    # Use the top 30% of results to ensure better relevance
                    top_results = data["results"][:max(3, len(data["results"]) // 3)]
                    image = random.choice(top_results)
                
                # Télécharger l'image
                image_url = image["urls"]["regular"]
                image_path = f"media/images/unsplash_{image['id']}.jpg"
                
                self._download_and_resize_image(image_url, image_path)
                
                return {
                    "media_type": "image",
                    "file_path": image_path,
                    "url": image_url,
                    "source": "unsplash",
                    "source_id": image["id"],
                    "source_url": image["links"]["html"],
                    "width": self.image_width,
                    "height": self.image_height,
                    "keywords": query
                }
            
            logger.debug("No results from Unsplash API")
            return None
            
        except Exception as e:
            logger.warning(f"Unsplash search failed: {str(e)}")
            
            # More detailed error logging for API issues
            if isinstance(e, requests.exceptions.HTTPError):
                logger.error(f"Unsplash API error: {e.response.text if hasattr(e, 'response') else str(e)}")
            
            return None
    
    def _search_pexels(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for an image on Pexels.
        
        Args:
            query: Search query string.
            
        Returns:
            Image information or None if no image found.
        """
        try:
            if not self.pexels_api_key:
                logger.warning("No Pexels API key provided")
                return None
                
            url = "https://api.pexels.com/v1/search"
            headers = {"Authorization": self.pexels_api_key}
            params = {
                "query": query,
                "per_page": 30,  # Increased from 10 to get more varied results
                "size": "medium"
            }
            
            logger.debug(f"Sending request to Pexels API: {url}")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            # Log the status code for debugging
            logger.debug(f"Pexels API response status: {response.status_code}")
            
            # Raise an exception for 4xx/5xx status codes
            response.raise_for_status()
            
            data = response.json()
            if data.get("photos"):
                # Pick from the top results to ensure better relevance
                top_results = data["photos"][:max(5, len(data["photos"]) // 3)]
                image = random.choice(top_results)
                
                # Download the image
                image_url = image["src"]["large"]
                image_path = f"media/images/pexels_{image['id']}.jpg"
                
                self._download_and_resize_image(image_url, image_path)
                
                return {
                    "media_type": "image",
                    "file_path": image_path,
                    "url": image_url,
                    "source": "pexels",
                    "source_id": str(image["id"]),
                    "source_url": image["url"],
                    "width": self.image_width,
                    "height": self.image_height,
                    "keywords": query
                }
            
            logger.debug("No results from Pexels API")
            return None
            
        except Exception as e:
            logger.warning(f"Pexels search failed: {str(e)}")
            
            # More detailed error logging for API issues
            if isinstance(e, requests.exceptions.HTTPError):
                logger.error(f"Pexels API error: {e.response.text if hasattr(e, 'response') else str(e)}")
                
            return None
    
    def _search_pixabay(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for an image on Pixabay.
        
        Args:
            query: Search query string.
            
        Returns:
            Image information or None if no image found.
        """
        try:
            if not self.pixabay_api_key:
                logger.warning("No Pixabay API key provided")
                return None
                
            url = "https://pixabay.com/api/"
            params = {
                "key": self.pixabay_api_key,
                "q": query,
                "per_page": 30,  # Increased from 10 to get more varied results
                "image_type": "photo",
                "safesearch": "true"
            }
            
            logger.debug(f"Sending request to Pixabay API: {url}")
            response = requests.get(url, params=params, timeout=10)
            
            # Log the status code for debugging
            logger.debug(f"Pixabay API response status: {response.status_code}")
            
            # Raise an exception for 4xx/5xx status codes
            response.raise_for_status()
            
            data = response.json()
            if data.get("hits"):
                # Sort results by relevance - Pixabay provides metrics we can use
                results = sorted(data["hits"], key=lambda x: x.get("relevance", 0) + x.get("views", 0)/10000, reverse=True)
                
                # Pick from the top results to ensure better relevance
                top_results = results[:max(5, len(results) // 3)]
                image = random.choice(top_results)
                
                # Download the image
                image_url = image["largeImageURL"]
                image_path = f"media/images/pixabay_{image['id']}.jpg"
                
                self._download_and_resize_image(image_url, image_path)
                
                return {
                    "media_type": "image",
                    "file_path": image_path,
                    "url": image_url,
                    "source": "pixabay",
                    "source_id": str(image["id"]),
                    "source_url": image["pageURL"],
                    "width": self.image_width,
                    "height": self.image_height,
                    "keywords": query
                }
            
            logger.debug("No results from Pixabay API")
            return None
            
        except Exception as e:
            logger.warning(f"Pixabay search failed: {str(e)}")
            
            # More detailed error logging for API issues
            if isinstance(e, requests.exceptions.HTTPError):
                logger.error(f"Pixabay API error: {e.response.text if hasattr(e, 'response') else str(e)}")
                
            return None
    
    def _use_fallback_image(self) -> Dict[str, Any]:
        """
        Use the fallback image when no relevant image is found.
        
        Returns:
            Information about the fallback image.
        """
        # Ensure fallback image exists or create a default one
        if not self.fallback_image_path or not os.path.exists(self.fallback_image_path):
            logger.warning("Fallback image not found, creating a default one")
            return self._create_default_image()
            
        return {
            "media_type": "image",
            "file_path": self.fallback_image_path,
            "url": None,
            "source": "fallback",
            "source_id": "default",
            "source_url": None,
            "width": self.image_width,
            "height": self.image_height,
            "keywords": "generic,fallback",
            "search_query": "fallback"
        }
    
    def _create_default_image(self) -> Dict[str, Any]:
        """
        Create a default image when no fallback is available.
        
        Returns:
            Information about the generated image.
        """
        try:
            # Create resources directory if it doesn't exist
            fallback_dir = "resources"
            os.makedirs(fallback_dir, exist_ok=True)
            
            # Generate a simple colored image with text
            default_path = os.path.join(fallback_dir, "default.jpg")
            
            # Create a colored background
            img = Image.new('RGB', (self.image_width, self.image_height), color=(52, 152, 219))
            
            # Save the image
            img.save(default_path, "JPEG", quality=95)
            
            logger.info(f"Created default fallback image at {default_path}")
            
            return {
                "media_type": "image",
                "file_path": default_path,
                "url": None,
                "source": "fallback",
                "source_id": "default",
                "source_url": None,
                "width": self.image_width,
                "height": self.image_height,
                "keywords": "generic,fallback",
                "search_query": "fallback"
            }
        except Exception as e:
            logger.error(f"Error creating default image: {str(e)}")
            
            # Return a minimal fallback that doesn't depend on file creation
            return {
                "media_type": "image",
                "file_path": "resources/default.jpg",  # This might not exist
                "url": None,
                "source": "fallback",
                "source_id": "default",
                "source_url": None,
                "width": 1080,
                "height": 1080,
                "keywords": "generic,fallback",
                "search_query": "fallback"
            }
    
    def _download_and_resize_image(self, url: str, save_path: str) -> None:
        """
        Download and resize an image.
        
        Args:
            url: URL of the image to download.
            save_path: Path where to save the image.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Open the image with PIL
            image = Image.open(BytesIO(response.content))
            
            # Resize the image for Instagram (square ratio)
            resized_image = self._resize_image(image)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Save the resized image
            resized_image.save(save_path, "JPEG", quality=95)
            
            logger.debug(f"Image downloaded and saved to {save_path}")
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            raise
    
    def _resize_image(self, image: Image.Image) -> Image.Image:
        """
        Resize an image for social media.
        
        Args:
            image: PIL Image object to resize.
            
        Returns:
            Resized PIL Image object.
        """
        # Create a square image (crop then resize)
        width, height = image.size
        
        # Crop to obtain a square
        if width > height:
            left = (width - height) // 2
            top = 0
            right = left + height
            bottom = height
        else:
            top = (height - width) // 2
            left = 0
            bottom = top + width
            right = width
            
        image = image.crop((left, top, right, bottom))
        
        # Resize to the desired size
        image = image.resize((self.image_width, self.image_height), Image.Resampling.LANCZOS)
        
        return image
    
    def _save_media_to_db(self, media_data: Dict[str, Any], post_id: str) -> None:
        """
        Save image data to the database.
        
        Args:
            media_data: Information about the image.
            post_id: ID of the associated post.
        """
        try:
            with Session() as session:
                # Check if media content already exists for this post
                existing_media = session.query(MediaContent).filter_by(reddit_id=post_id).first()
                
                if existing_media:
                    logger.warning(f"Media content already exists for post {post_id}, updating")
                    
                    # Update existing record
                    existing_media.media_type = media_data["media_type"]
                    existing_media.file_path = media_data["file_path"]
                    existing_media.source_url = media_data.get("url")
                    existing_media.source = media_data["source"]
                    existing_media.source_id = media_data["source_id"]
                    existing_media.width = media_data["width"]
                    existing_media.height = media_data["height"]
                    existing_media.keywords = media_data.get("keywords", "")
                    # Save search query if available
                    if "search_query" in media_data:
                        existing_media.search_query = media_data["search_query"]
                    existing_media.updated_at = datetime.now()
                else:
                    # Update the processed content status
                    processed_content = session.query(ProcessedContent).filter_by(reddit_id=post_id).first()
                    if processed_content:
                        processed_content.has_media = True
                    
                    # Create a new entry for the media content
                    media_content = MediaContent(
                        reddit_id=post_id,
                        media_type=media_data["media_type"],
                        file_path=media_data["file_path"],
                        source_url=media_data.get("url"),
                        source=media_data["source"],
                        source_id=media_data["source_id"],
                        width=media_data["width"],
                        height=media_data["height"],
                        keywords=media_data.get("keywords", ""),
                        search_query=media_data.get("search_query", "")
                    )
                    
                    session.add(media_content)
                
                session.commit()
                logger.debug(f"Media content saved to database for post {post_id}")
                
        except Exception as e:
            logger.error(f"Failed to save media content to database: {str(e)}")