# core/media/video_finder.py
import os
import logging
import requests
import random
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

from config.settings import config
from utils.error_handler import handle_media_error
from database.models import ProcessedContent, MediaContent, Session

logger = logging.getLogger(__name__)

class VideoFinder:
    """Classe pour rechercher des vidéos pertinentes basées sur les mots-clés."""
    
    def __init__(self):
        """Initialiser le chercheur de vidéos avec les API keys."""
        self.pexels_api_key = config.media.pexels_api_key
        self.pixabay_api_key = config.media.pixabay_api_key
        self.fallback_video_path = config.media.fallback_video_path
        
        # S'assurer que le dossier des médias existe
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
        Rechercher une vidéo pertinente basée sur les mots-clés.
        
        Args:
            keywords: Liste de mots-clés pour la recherche.
            post_id: ID du post pour lequel chercher une vidéo.
            
        Returns:
            Dictionnaire contenant les informations sur la vidéo trouvée.
        """
        try:
            # Ensure we have some keywords
            if not keywords:
                logger.warning(f"No keywords provided for post {post_id}, using default keywords")
                keywords = ["knowledge", "learning", "information"]
                
            # Joindre les mots-clés en une seule chaîne de recherche
            search_query = " ".join(keywords[:3])  # Limiter à 3 mots-clés pour de meilleurs résultats
            logger.debug(f"Searching videos for query: {search_query}")
            
            # Essayer chaque API de recherche de vidéos dans un ordre prédéfini
            video_result = None
            
            # 1. Essayer Pexels si une clé API est disponible
            if self.pexels_api_key:
                logger.debug("Trying Pexels API for videos")
                video_result = self._search_pexels_videos(search_query)
            
            # 2. Essayer Pixabay si Pexels a échoué et qu'une clé API est disponible
            if not video_result and self.pixabay_api_key:
                logger.debug("Trying Pixabay API for videos")
                video_result = self._search_pixabay_videos(search_query)
            
            # Si aucune vidéo n'a été trouvée, utiliser la vidéo de secours
            if not video_result:
                logger.debug("No video found, using fallback")
                try:
                    video_result = self._use_fallback_video()
                except Exception as e:
                    logger.error(f"Error using fallback video: {str(e)}")
                    video_result = self._create_minimal_video_info()
            
            # Sauvegarder la vidéo dans la base de données
            self._save_media_to_db(video_result, post_id)
            
            logger.info(f"Found video for post {post_id}: {video_result['source']}")
            return video_result
            
        except Exception as e:
            error_msg = f"Error finding video: {str(e)}"
            logger.error(error_msg)
            handle_media_error("video_finding", error_msg, post_id=post_id)
            
            # En cas d'erreur, utiliser la vidéo de secours ou une info minimale
            try:
                fallback_result = self._use_fallback_video()
            except Exception as fallback_error:
                logger.error(f"Fallback video error: {str(fallback_error)}")
                fallback_result = self._create_minimal_video_info()
                
            self._save_media_to_db(fallback_result, post_id)
            return fallback_result
    
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
            "keywords": "generic,fallback"
        }
    
    def _search_pexels_videos(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Rechercher une vidéo sur Pexels.
        
        Args:
            query: Terme de recherche.
            
        Returns:
            Informations sur la vidéo ou None si aucune vidéo n'est trouvée.
        """
        try:
            if not self.pexels_api_key:
                logger.warning("No Pexels API key available")
                return None
                
            url = "https://api.pexels.com/videos/search"
            headers = {"Authorization": self.pexels_api_key}
            params = {
                "query": query,
                "per_page": 10,
                "size": "medium",
                "orientation": "portrait"  # Meilleur pour les formats verticaux comme TikTok
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
                # Choisir une vidéo aléatoire parmi les résultats
                video = random.choice(data["videos"])
                
                # Trouver le fichier vidéo (préférer la qualité HD si disponible)
                video_files = video.get("video_files", [])
                
                # Trier par qualité (préférer HD mais pas trop grand)
                suitable_files = [
                    f for f in video_files 
                    if f.get("width", 0) >= 720 and f.get("height", 0) >= 720
                ]
                
                if not suitable_files:
                    suitable_files = video_files
                
                if suitable_files:
                    video_file = min(suitable_files, key=lambda x: x.get("width", 0) * x.get("height", 0))
                    
                    # Télécharger la vidéo
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
        Rechercher une vidéo sur Pixabay.
        
        Args:
            query: Terme de recherche.
            
        Returns:
            Informations sur la vidéo ou None si aucune vidéo n'est trouvée.
        """
        try:
            if not self.pixabay_api_key:
                logger.warning("No Pixabay API key available")
                return None
                
            url = "https://pixabay.com/api/videos/"
            params = {
                "key": self.pixabay_api_key,
                "q": query,
                "per_page": 10,
                "video_type": "film"
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
                # Choisir une vidéo aléatoire parmi les résultats
                video = random.choice(data["hits"])
                
                # Télécharger la vidéo (utiliser large ou medium)
                video_url = None
                if video.get("videos", {}).get("large", {}).get("url"):
                    video_url = video["videos"]["large"]["url"]
                elif video.get("videos", {}).get("medium", {}).get("url"):
                    video_url = video["videos"]["medium"]["url"]
                
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
                    "width": 1280,  # Default values
                    "height": 720,
                    "duration": 10,
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
        Utiliser la vidéo de secours lorsqu'aucune vidéo pertinente n'est trouvée.
        
        Returns:
            Informations sur la vidéo de secours.
        """
        # Vérifier si le fichier de secours existe
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
                "keywords": "generic,fallback"
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
            "keywords": "generic,fallback"
        }
    
    def _download_video(self, url: str, save_path: str) -> None:
        """
        Télécharger une vidéo.
        
        Args:
            url: URL de la vidéo à télécharger.
            save_path: Chemin où sauvegarder la vidéo.
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Télécharger par blocs pour éviter les problèmes de mémoire
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.debug(f"Video downloaded successfully to {save_path}")
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise
    
    def _save_media_to_db(self, media_data: Dict[str, Any], post_id: str) -> None:
        """
        Enregistrer les données de la vidéo dans la base de données.
        
        Args:
            media_data: Informations sur la vidéo.
            post_id: ID du post associé.
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
                    existing_media.source_url = media_data["source_url"]
                    existing_media.source = media_data["source"]
                    existing_media.source_id = media_data["source_id"]
                    existing_media.width = media_data["width"]
                    existing_media.height = media_data["height"]
                    existing_media.keywords = media_data["keywords"]
                    existing_media.updated_at = datetime.now()
                else:
                    # Mettre à jour le statut du contenu traité
                    processed_content = session.query(ProcessedContent).filter_by(reddit_id=post_id).first()
                    if processed_content:
                        processed_content.has_media = True
                    
                    # Créer une nouvelle entrée pour le contenu média
                    media_content = MediaContent(
                        reddit_id=post_id,
                        media_type=media_data["media_type"],
                        file_path=media_data["file_path"],
                        source_url=media_data["source_url"],
                        source=media_data["source"],
                        source_id=media_data["source_id"],
                        width=media_data["width"],
                        height=media_data["height"],
                        keywords=media_data["keywords"]
                    )
                    
                    session.add(media_content)
                
                session.commit()
                logger.debug(f"Media content saved to database for post {post_id}")
                
        except Exception as e:
            logger.error(f"Failed to save media content to database: {str(e)}")