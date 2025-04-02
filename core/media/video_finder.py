# core/media/video_finder.py
import os
import logging
import requests
import random
import re
from typing import Dict, List, Any, Optional
import time
import tempfile
from PIL import Image
from io import BytesIO
from datetime import datetime

# Conditional MoviePy import with fallback
try:
    from moviepy.editor import VideoFileClip, ImageClip, TextClip, ColorClip, CompositeVideoClip
    MOVIEPY_AVAILABLE = True
except (ImportError, Exception) as e:
    MOVIEPY_AVAILABLE = False
    logging.warning(f"MoviePy not available: {str(e)}")
    # Create dummy classes for testing
    class DummyClip:
        def __init__(self, *args, **kwargs):
            self.duration = 10.0
            self.size = (1280, 720)
            
        def resize(self, *args, **kwargs):
            return self
            
        def set_duration(self, *args, **kwargs):
            return self
            
        def set_position(self, *args, **kwargs):
            return self
            
        def write_videofile(self, *args, **kwargs):
            # Just pretend to write the file
            import os
            os.makedirs(os.path.dirname(args[0]), exist_ok=True)
            with open(args[0], 'w') as f:
                f.write('dummy video content')
            return None
            
    VideoFileClip = ImageClip = TextClip = ColorClip = CompositeVideoClip = DummyClip

from config.settings import config
from utils.error_handler import handle_media_error
from utils.claude_media_search import ClaudeMediaSearch
from database.models import ProcessedContent, MediaContent, Session, RedditPost

logger = logging.getLogger(__name__)

class VideoFinder:
    """Class for finding relevant videos based on content keywords."""
    
    def __init__(self):
        """Initialize the video finder with API keys."""
        self.pexels_api_key = config.media.pexels_api_key
        self.pixabay_api_key = config.media.pixabay_api_key
        self.fallback_video_path = config.media.fallback_video_path
        
        # Initialize the Claude-powered media search enhancer
        self.claude_search = ClaudeMediaSearch()
        
        # Ensure that the media directory exists
        os.makedirs("media/videos", exist_ok=True)
        
        # Log API status
        logger.info(f"Video finder initialized with APIs: " +
                   f"Pexels: {'Available' if self.pexels_api_key else 'Missing'}, " +
                   f"Pixabay: {'Available' if self.pixabay_api_key else 'Missing'}")
        
        # Check if MoviePy is available
        if not MOVIEPY_AVAILABLE:
            logger.warning("MoviePy is not available. Video creation will be limited.")
    
    def find_video(self, keywords: List[str], post_id: str) -> Dict[str, Any]:
        """
        Find a relevant video based on keywords and post content.
        
        Args:
            keywords: List of keywords for searching.
            post_id: ID of the post to associate with the video.
            
        Returns:
            Dictionary containing information about the found video.
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
                    post_title, post_content, post_id, media_type="video"
                )
                logger.info(f"Claude generated video query for post {post_id}: '{primary_query}'")
                search_query = primary_query
            else:
                # Fallback to basic keyword joining if post details not available
                search_query = " ".join(keywords[:5])
                alt_queries = []
            
            logger.debug(f"Searching videos for query: {search_query}")
            
            # Try to find a video with the primary query
            video_result = self._try_all_video_sources(search_query)
            
            # If no results with primary query, try alternative queries
            if not video_result and alt_queries:
                for alt_query in alt_queries:
                    logger.info(f"Trying alternative video query: '{alt_query}'")
                    video_result = self._try_all_video_sources(alt_query)
                    if video_result:
                        search_query = alt_query  # Update the successful query
                        break
            
            # If still no results, fall back to the original keywords
            if not video_result and keywords:
                original_query = " ".join(keywords[:5]) 
                logger.info(f"Trying original keywords for video: '{original_query}'")
                video_result = self._try_all_video_sources(original_query)
                if video_result:
                    search_query = original_query
            
            # If no video found with any queries, use fallback
            if not video_result:
                logger.debug("No video found with any query, using fallback")
                video_result = self._use_fallback_video()
            
            # Add the successful search query to the result
            video_result['search_query'] = search_query
            
            # Save the video info to the database
            self._save_media_to_db(video_result, post_id)
            
            logger.info(f"Found video for post {post_id}: {video_result['source']} (Query: {search_query})")
            return video_result
            
        except Exception as e:
            error_msg = f"Error finding video: {str(e)}"
            logger.error(error_msg)
            handle_media_error("video_finding", error_msg, post_id=post_id)
            
            # Use fallback video in case of error
            fallback_result = self._use_fallback_video()
            self._save_media_to_db(fallback_result, post_id)
            return fallback_result
    
    def _try_all_video_sources(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Try all available video sources with the given query.
        
        Args:
            query: Search query string.
            
        Returns:
            Video information or None if no video found.
        """
        # Try each API in sequence, stopping once a video is found
        video_result = None
        
        # 1. Try Pexels first if available
        if self.pexels_api_key:
            logger.debug("Trying Pexels API for videos")
            video_result = self._search_pexels_videos(query)
        
        # 2. Try Pixabay if Pexels failed and API is available
        if not video_result and self.pixabay_api_key:
            logger.debug("Trying Pixabay API for videos")
            video_result = self._search_pixabay_videos(query)
        
        return video_result
    
    def _search_pexels_videos(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a video on Pexels.
        
        Args:
            query: Search query string.
            
        Returns:
            Video information or None if no video found.
        """
        try:
            if not self.pexels_api_key:
                logger.warning("No Pexels API key available")
                return None
                
            url = "https://api.pexels.com/videos/search"
            headers = {"Authorization": self.pexels_api_key}
            params = {
                "query": query,
                "per_page": 30,  # Increased from 10 to get more varied results
                "size": "medium",
                "orientation": "portrait"  # Better for vertical formats like TikTok
            }
            
            logger.debug(f"Sending request to Pexels videos API: {url}")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            # Log the status code
            logger.debug(f"Pexels videos API response status: {response.status_code}")
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"Pexels video search failed: {response.status_code} - {response.text}")
                return None
                
            data = response.json()
            if data.get("videos") and len(data["videos"]) > 0:
                # Use the top 30% of results to ensure better relevance
                top_results = data["videos"][:max(5, len(data["videos"]) // 3)]
                video = random.choice(top_results)
                
                # Find the video file (prefer HD quality if available)
                video_files = video.get("video_files", [])
                
                # Sort by quality (prefer HD but not too large)
                suitable_files = [
                    f for f in video_files 
                    if f.get("width", 0) >= 720 and f.get("height", 0) >= 720 and
                    f.get("file_type", "").startswith("video/")
                ]
                
                if not suitable_files:
                    suitable_files = video_files
                
                if suitable_files:
                    # Sort files by resolution (prefer higher resolution)
                    sorted_files = sorted(
                        suitable_files, 
                        key=lambda x: x.get("width", 0) * x.get("height", 0),
                        reverse=True
                    )
                    
                    # Use the highest quality but not the largest file
                    video_file = sorted_files[min(1, len(sorted_files) - 1)] if len(sorted_files) > 1 else sorted_files[0]
                    
                    # Download the video
                    video_url = video_file["link"]
                    video_path = f"media/videos/pexels_{video['id']}.mp4"
                    
                    # Create an info dict even if download fails
                    video_info = {
                        "media_type": "video",
                        "file_path": video_path,
                        "url": video_url,
                        "source": "pexels",
                        "source_id": str(video["id"]),
                        "source_url": video["url"],
                        "width": video_file.get("width", 1280),
                        "height": video_file.get("height", 720),
                        "duration": video.get("duration", 10),
                        "keywords": query
                    }
                    
                    try:
                        self._download_video(video_url, video_path)
                        
                        # Update dimensions if we can get them from the actual file
                        if MOVIEPY_AVAILABLE and os.path.exists(video_path):
                            with VideoFileClip(video_path) as clip:
                                video_info["duration"] = clip.duration
                                video_info["width"], video_info["height"] = clip.size
                    except Exception as e:
                        logger.error(f"Error downloading Pexels video: {str(e)}")
                        # Continue with the info we have even if download failed
                    
                    return video_info
            
            logger.debug("No suitable videos found in Pexels")
            return None
            
        except Exception as e:
            logger.warning(f"Pexels video search failed: {str(e)}")
            return None
    
    def _search_pixabay_videos(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a video on Pixabay.
        
        Args:
            query: Search query string.
            
        Returns:
            Video information or None if no video found.
        """
        try:
            if not self.pixabay_api_key:
                logger.warning("No Pixabay API key available")
                return None
                
            url = "https://pixabay.com/api/videos/"
            params = {
                "key": self.pixabay_api_key,
                "q": query,
                "per_page": 30,  # Increased from 10 to get more varied results
                "video_type": "all"  # Include all video types
            }
            
            logger.debug(f"Sending request to Pixabay videos API: {url}")
            response = requests.get(url, params=params, timeout=15)
            
            # Log the status code
            logger.debug(f"Pixabay videos API response status: {response.status_code}")
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"Pixabay video search failed: {response.status_code} - {response.text}")
                return None
                
            data = response.json()
            if data.get("hits") and len(data["hits"]) > 0:
                # Use the top 30% of results to ensure better relevance
                top_results = data["hits"][:max(5, len(data["hits"]) // 3)]
                video = random.choice(top_results)
                
                # Get the best quality video (prefer large or medium)
                video_url = None
                video_width = 0
                video_height = 0
                
                # Prioritize videos with higher resolution
                video_options = []
                
                if video.get("videos", {}).get("large", {}).get("url"):
                    video_options.append({
                        "url": video["videos"]["large"]["url"],
                        "width": video["videos"]["large"].get("width", 1920),
                        "height": video["videos"]["large"].get("height", 1080)
                    })
                
                if video.get("videos", {}).get("medium", {}).get("url"):
                    video_options.append({
                        "url": video["videos"]["medium"]["url"],
                        "width": video["videos"]["medium"].get("width", 1280),
                        "height": video["videos"]["medium"].get("height", 720)
                    })
                
                if video.get("videos", {}).get("small", {}).get("url"):
                    video_options.append({
                        "url": video["videos"]["small"]["url"],
                        "width": video["videos"]["small"].get("width", 960),
                        "height": video["videos"]["small"].get("height", 540)
                    })
                
                if video_options:
                    # Sort by resolution (highest first)
                    video_options.sort(key=lambda x: x["width"] * x["height"], reverse=True)
                    
                    # Select the second highest quality if available (balance of quality and size)
                    selected_option = video_options[min(1, len(video_options) - 1)] if len(video_options) > 1 else video_options[0]
                    
                    video_url = selected_option["url"]
                    video_width = selected_option["width"]
                    video_height = selected_option["height"]
                
                if not video_url:
                    logger.warning("No suitable video URL found in Pixabay response")
                    return None
                
                video_path = f"media/videos/pixabay_{video['id']}.mp4"
                
                # Create video info even if download fails
                video_info = {
                    "media_type": "video",
                    "file_path": video_path,
                    "url": video_url,
                    "source": "pixabay",
                    "source_id": str(video["id"]),
                    "source_url": video["pageURL"],
                    "width": video_width,
                    "height": video_height,
                    "duration": 10,  # Default duration, will be updated if possible
                    "keywords": query
                }
                
                try:
                    self._download_video(video_url, video_path)
                    
                    # Update dimensions if we can get them from the actual file
                    if MOVIEPY_AVAILABLE and os.path.exists(video_path):
                        with VideoFileClip(video_path) as clip:
                            video_info["duration"] = clip.duration
                            video_info["width"], video_info["height"] = clip.size
                except Exception as e:
                    logger.error(f"Error downloading Pixabay video: {str(e)}")
                    # Continue with the info we have even if download failed
                
                return video_info
            
            logger.debug("No suitable videos found in Pixabay")
            return None
            
        except Exception as e:
            logger.warning(f"Pixabay video search failed: {str(e)}")
            return None
    
    def _use_fallback_video(self) -> Dict[str, Any]:
        """
        Use the fallback video when no relevant video is found.
        
        Returns:
            Information about the fallback video.
        """
        # Check if the fallback file exists
        if self.fallback_video_path and os.path.exists(self.fallback_video_path):
            logger.debug(f"Using existing fallback video: {self.fallback_video_path}")
            
            # Get dimensions and duration if possible
            width, height, duration = 720, 1280, 10.0
            if MOVIEPY_AVAILABLE:
                try:
                    with VideoFileClip(self.fallback_video_path) as clip:
                        duration = clip.duration
                        width, height = clip.size
                except Exception as e:
                    logger.warning(f"Could not get fallback video info: {str(e)}")
            
            return {
                "media_type": "video",
                "file_path": self.fallback_video_path,
                "url": None,
                "source": "fallback",
                "source_id": "default",
                "source_url": None,
                "width": width,
                "height": height,
                "duration": duration,
                "keywords": "generic,fallback",
                "search_query": "fallback"
            }
        
        # Create a fallback video directory if needed
        fallback_dir = os.path.dirname(self.fallback_video_path) if self.fallback_video_path else "resources"
        os.makedirs(fallback_dir, exist_ok=True)
        
        # Set default fallback path if not specified
        if not self.fallback_video_path:
            self.fallback_video_path = os.path.join(fallback_dir, "default_video.mp4")
            
        # Create a basic video if MoviePy is available
        if MOVIEPY_AVAILABLE:
            try:
                # Create fallback components using safe approaches
                try:
                    # Approach 1: Using ColorClip (less dependent on ImageMagick)
                    color_clip = ColorClip(size=(720, 1280), color=(52, 152, 219), duration=10)
                    
                    # Try with different text settings to find one that works
                    text_clip = None
                    for method in ["label", "caption", None]:
                        try:
                            text_clip = TextClip(
                                "Content Machine", 
                                fontsize=70, 
                                color='white',
                                bg_color='black',
                                method=method,
                                size=(600, 200) if method else None
                            )
                            text_clip = text_clip.set_position('center').set_duration(10)
                            break
                        except Exception as text_error:
                            logger.warning(f"Text clip method {method} failed: {str(text_error)}")
                    
                    # If no text clip could be created, use only color clip
                    if text_clip:
                        final_clip = CompositeVideoClip([color_clip, text_clip])
                    else:
                        final_clip = color_clip
                        
                    # Write to file with safe settings
                    final_clip.write_videofile(
                        self.fallback_video_path,
                        codec='libx264',
                        fps=24,
                        preset='ultrafast',
                        audio=False
                    )
                    
                    width, height = final_clip.size
                    duration = final_clip.duration
                    
                    logger.info(f"Successfully created fallback video at {self.fallback_video_path}")
                    
                except Exception as e:
                    logger.error(f"Error creating fallback video with approach 1: {str(e)}")
                    
                    # Approach 2: Create from a static image if text approach failed
                    try:
                        # Create a simple image
                        img = Image.new('RGB', (720, 1280), color=(52, 152, 219))
                        temp_img_path = os.path.join(tempfile.gettempdir(), "temp_fallback.jpg")
                        img.save(temp_img_path)
                        
                        # Create video from the image
                        image_clip = ImageClip(temp_img_path).set_duration(10)
                        image_clip.write_videofile(
                            self.fallback_video_path,
                            codec='libx264',
                            fps=24,
                            preset='ultrafast',
                            audio=False
                        )
                        
                        width, height = image_clip.size
                        duration = image_clip.duration
                        
                        # Clean up temp file
                        try:
                            os.remove(temp_img_path)
                        except:
                            pass
                            
                        logger.info(f"Successfully created fallback video from image at {self.fallback_video_path}")
                        
                    except Exception as img_error:
                        logger.error(f"Error creating fallback video with approach 2: {str(img_error)}")
                        # Fall back to returning info only without actual file
                        return self._create_minimal_video_info()
                        
            except Exception as final_error:
                logger.error(f"All fallback video creation approaches failed: {str(final_error)}")
                return self._create_minimal_video_info()
        else:
            logger.warning("MoviePy not available. Cannot create fallback video.")
            return self._create_minimal_video_info()
        
        return {
            "media_type": "video",
            "file_path": self.fallback_video_path,
            "url": None,
            "source": "fallback",
            "source_id": "default",
            "source_url": None,
            "width": width,
            "height": height,
            "duration": duration,
            "keywords": "generic,fallback",
            "search_query": "fallback"
        }
    
    def _create_minimal_video_info(self) -> Dict[str, Any]:
        """
        Create a minimal video info structure when everything else fails.
        This doesn't depend on file creation or external dependencies.
        
        Returns:
            Basic video information dict
        """
        return {
            "media_type": "video",
            "file_path": os.path.join("resources", "default_video.mp4"),
            "url": None,
            "source": "fallback",
            "source_id": "default_minimal",
            "source_url": None,
            "width": 720,
            "height": 1280,
            "duration": 10.0,
            "keywords": "generic,fallback",
            "search_query": "fallback"
        }
    
    def _download_video(self, url: str, save_path: str) -> None:
        """
        Download a video from URL.
        
        Args:
            url: URL of the video to download.
            save_path: Path where to save the video.
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Download in chunks to avoid memory issues
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.debug(f"Video downloaded successfully to {save_path}")
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise
    
    def _save_media_to_db(self, media_data: Dict[str, Any], post_id: str) -> None:
        """
        Save video data to the database.
        
        Args:
            media_data: Information about the video.
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