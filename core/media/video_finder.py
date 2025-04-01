# core/media/video_finder.py
import os
import logging
import requests
import random
from typing import Dict, List, Any, Optional
import time
from moviepy.editor import VideoFileClip

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
        self.fallback_video_path = config.media.get('fallback_video_path', 'resources/default_video.mp4')
        
        # S'assurer que le dossier des médias existe
        os.makedirs("media/videos", exist_ok=True)
        logger.info("Video finder initialized")
    
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
            # Joindre les mots-clés en une seule chaîne de recherche
            search_query = " ".join(keywords[:3])  # Limiter à 3 mots-clés pour de meilleurs résultats
            
            # Essayer chaque API de recherche de vidéos dans un ordre prédéfini
            video_result = None
            
            # 1. Essayer Pexels si une clé API est disponible
            if self.pexels_api_key:
                video_result = self._search_pexels_videos(search_query)
            
            # 2. Essayer Pixabay si Pexels a échoué et qu'une clé API est disponible
            if not video_result and self.pixabay_api_key:
                video_result = self._search_pixabay_videos(search_query)
            
            # Si aucune vidéo n'a été trouvée, utiliser la vidéo de secours
            if not video_result:
                video_result = self._use_fallback_video()
            
            # Sauvegarder la vidéo dans la base de données
            self._save_media_to_db(video_result, post_id)
            
            logger.info(f"Found video for post {post_id}: {video_result['source']}")
            return video_result
            
        except Exception as e:
            error_msg = f"Error finding video: {str(e)}"
            logger.error(error_msg)
            handle_media_error("video_finding", error_msg, post_id=post_id)
            
            # En cas d'erreur, utiliser la vidéo de secours
            fallback_result = self._use_fallback_video()
            self._save_media_to_db(fallback_result, post_id)
            return fallback_result
    
    def _search_pexels_videos(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Rechercher une vidéo sur Pexels.
        
        Args:
            query: Terme de recherche.
            
        Returns:
            Informations sur la vidéo ou None si aucune vidéo n'est trouvée.
        """
        try:
            url = "https://api.pexels.com/videos/search"
            headers = {"Authorization": self.pexels_api_key}
            params = {
                "query": query,
                "per_page": 10,
                "size": "medium",
                "orientation": "portrait"  # Meilleur pour les formats verticaux comme TikTok
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("videos"):
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
                    
                    self._download_video(video_url, video_path)
                    
                    # Obtenir la durée et les dimensions
                    with VideoFileClip(video_path) as clip:
                        duration = clip.duration
                        width, height = clip.size
                    
                    return {
                        "media_type": "video",
                        "file_path": video_path,
                        "url": video_url,
                        "source": "pexels",
                        "source_id": str(video["id"]),
                        "source_url": video["url"],
                        "width": width,
                        "height": height,
                        "duration": duration,
                        "keywords": query
                    }
            
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
            url = "https://pixabay.com/api/videos/"
            params = {
                "key": self.pixabay_api_key,
                "q": query,
                "per_page": 10,
                "video_type": "film"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("hits"):
                # Choisir une vidéo aléatoire parmi les résultats
                video = random.choice(data["hits"])
                
                # Télécharger la vidéo (utiliser large ou medium)
                if video.get("videos", {}).get("large", {}).get("url"):
                    video_url = video["videos"]["large"]["url"]
                elif video.get("videos", {}).get("medium", {}).get("url"):
                    video_url = video["videos"]["medium"]["url"]
                else:
                    return None
                
                video_path = f"media/videos/pixabay_{video['id']}.mp4"
                
                self._download_video(video_url, video_path)
                
                # Obtenir la durée et les dimensions
                with VideoFileClip(video_path) as clip:
                    duration = clip.duration
                    width, height = clip.size
                
                return {
                    "media_type": "video",
                    "file_path": video_path,
                    "url": video_url,
                    "source": "pixabay",
                    "source_id": str(video["id"]),
                    "source_url": video["pageURL"],
                    "width": width,
                    "height": height,
                    "duration": duration,
                    "keywords": query
                }
            
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
        if not os.path.exists(self.fallback_video_path):
            # Si le fichier n'existe pas, créer une vidéo simple avec moviepy
            from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
            
            # Créer un fond coloré
            color_clip = ColorClip(size=(720, 1280), color=(52, 152, 219), duration=10)
            
            # Ajouter un texte
            text_clip = TextClip("Content Machine", fontsize=70, color='white', font='Arial-Bold')
            text_clip = text_clip.set_position('center').set_duration(10)
            
            # Combiner les clips
            final_clip = CompositeVideoClip([color_clip, text_clip])
            
            # Sauvegarder dans un fichier
            os.makedirs(os.path.dirname(self.fallback_video_path), exist_ok=True)
            final_clip.write_videofile(self.fallback_video_path, codec='libx264', fps=24)
        
        # Obtenir la durée et les dimensions du fichier de secours
        with VideoFileClip(self.fallback_video_path) as clip:
            duration = clip.duration
            width, height = clip.size
        
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
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Télécharger par blocs pour éviter les problèmes de mémoire
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    def _save_media_to_db(self, media_data: Dict[str, Any], post_id: str) -> None:
        """
        Enregistrer les données de la vidéo dans la base de données.
        
        Args:
            media_data: Informations sur la vidéo.
            post_id: ID du post associé.
        """
        try:
            with Session() as session:
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
                
        except Exception as e:
            logger.error(f"Failed to save media content to database: {str(e)}")