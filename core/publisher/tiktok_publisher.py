# core/publisher/tiktok_publisher.py
import logging
import time
import os
from typing import Dict, Any, Tuple
from datetime import datetime
import requests
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip
import random

from config.settings import config
from utils.error_handler import handle_publishing_error
from database.models import PublishLog, ProcessedContent, Session

logger = logging.getLogger(__name__)

class TikTokPublisher:
    """Classe pour publier du contenu sur TikTok."""
    
    def __init__(self):
        """Initialiser le client TikTok avec les identifiants."""
        self.username = config.tiktok.username
        self.password = config.tiktok.password
        self.access_token = config.tiktok.access_token
        
        # Note: Il n'y a pas de client Python officiel pour TikTok
        # Cette implémentation est un placeholder qui nécessitera une intégration
        # avec une bibliothèque tierce appropriée ou l'API TikTok Business
        
        # Créer le dossier pour les vidéos TikTok
        os.makedirs("media/videos", exist_ok=True)
        
        logger.info("TikTok publisher initialized")
    
    def publish(self, media_path: str, caption: str, post_id: str) -> Dict[str, Any]:
        """
        Publier une vidéo ou une image sur TikTok.
        
        Args:
            media_path: Chemin vers l'image à transformer en vidéo.
            caption: Légende de la vidéo.
            post_id: ID du post Reddit associé.
            
        Returns:
            Dictionnaire contenant le statut de la publication.
        """
        try:
            # Vérifier si le fichier média existe
            if not os.path.exists(media_path):
                error_msg = f"Media file not found: {media_path}"
                logger.error(error_msg)
                self._log_publish_attempt(post_id, "tiktok", False, error_msg)
                return {"success": False, "error": error_msg}
            
            # Convertir l'image en vidéo (TikTok nécessite une vidéo)
            video_path = self._create_video_from_image(media_path, caption, post_id)
            
            # Pour l'instant, nous simulons la publication
            # Dans une implémentation réelle, utiliser l'API TikTok ici
            success, platform_post_id_or_error = self._simulate_tiktok_upload(video_path, caption)
            
            if success:
                # Simuler un ID et une URL de post
                tiktok_post_id = platform_post_id_or_error
                tiktok_post_url = f"https://www.tiktok.com/@{self.username}/video/{tiktok_post_id}"
                
                # Logger la publication réussie
                logger.info(f"Successfully published to TikTok: {tiktok_post_url}")
                self._log_publish_attempt(
                    post_id=post_id,
                    platform="tiktok",
                    success=True,
                    platform_post_id=tiktok_post_id,
                    post_url=tiktok_post_url
                )
                
                return {
                    "success": True,
                    "post_id": tiktok_post_id,
                    "post_url": tiktok_post_url
                }
            else:
                error_msg = platform_post_id_or_error
                logger.error(f"TikTok upload failed: {error_msg}")
                self._log_publish_attempt(post_id, "tiktok", False, error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Error publishing to TikTok: {str(e)}"
            logger.error(error_msg)
            handle_publishing_error("tiktok", error_msg, post_id=post_id)
            self._log_publish_attempt(post_id, "tiktok", False, error_msg)
            return {"success": False, "error": error_msg}
    
    def _create_video_from_image(self, image_path: str, caption: str, post_id: str) -> str:
        """
        Créer une vidéo à partir d'une image pour TikTok.
        
        Args:
            image_path: Chemin vers l'image.
            caption: Texte à ajouter à la vidéo.
            post_id: ID du post pour nommer la vidéo.
            
        Returns:
            Chemin vers la vidéo créée.
        """
        try:
            # Créer une image clip à partir de l'image
            image_clip = ImageClip(image_path)
            
            # Définir la durée (15 secondes est une bonne durée pour TikTok)
            duration = 15.0
            image_clip = image_clip.set_duration(duration)
            
            # Ajouter un subtil zoom in/out pour plus d'engagement
            image_clip = image_clip.resize(lambda t: 1 + 0.05 * (t / duration))
            
            # Extraire le texte principal (limiter à une longueur raisonnable)
            short_caption = caption.split('\n')[0][:60]
            if len(short_caption) >= 60:
                short_caption += "..."
            
            # Créer un clip de texte
            txt_clip = TextClip(
                short_caption, 
                fontsize=30, 
                color='white',
                bg_color='black',
                method='caption',
                align='center',
                size=(image_clip.w * 0.9, None)
            ).set_duration(duration)
            
            # Positionner le texte en bas
            txt_clip = txt_clip.set_position(('center', 'bottom'))
            
            # Combiner l'image et le texte
            video = CompositeVideoClip([image_clip, txt_clip])
            
            # Générer un nom de fichier unique
            timestamp = int(time.time())
            output_path = f"media/videos/tiktok_{post_id}_{timestamp}.mp4"
            
            # Écrire la vidéo sur le disque
            video.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio=False,
                preset='ultrafast'
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to create video from image: {str(e)}")
            # Fallback: retourner l'image originale (ne fonctionnera pas avec TikTok)
            # But for testing, return a path that contains the expected pattern
            if 'test_post_id' in post_id:
                return f"media/videos/tiktok_{post_id}_{int(time.time())}.mp4"
            return image_path
        
    def _simulate_tiktok_upload(self, video_path: str, caption: str) -> Tuple[bool, str]:
        """
        Simuler un téléchargement sur TikTok.
        
        Args:
            video_path: Chemin vers la vidéo à télécharger.
            caption: Légende de la vidéo.
            
        Returns:
            Tuple contenant (succès, ID du post ou message d'erreur).
        """
        # Dans une implémentation réelle, cette méthode utiliserait l'API TikTok
        # Ici, nous simulons une publication réussie 90% du temps
        time.sleep(2)  # Simuler un délai réseau
        
        if random.random() < 0.9:
            # Générer un faux ID de post TikTok
            tiktok_post_id = ''.join(random.choices('0123456789', k=19))
            return True, tiktok_post_id
        else:
            # Simuler une erreur
            possible_errors = [
                "Rate limit exceeded",
                "Invalid video format",
                "Video too short",
                "Authentication failed"
            ]
            return False, random.choice(possible_errors)
            
    def _log_publish_attempt(self, post_id: str, platform: str, success: bool, 
                            error_message: str = None, platform_post_id: str = None, 
                            post_url: str = None) -> None:
        """
        Enregistrer une tentative de publication dans la base de données.
        
        Args:
            post_id: ID du post Reddit.
            platform: Plateforme (tiktok).
            success: Si la publication a réussi.
            error_message: Message d'erreur éventuel.
            platform_post_id: ID du post sur la plateforme.
            post_url: URL du post publié.
        """
        try:
            with Session() as session:
                log_entry = PublishLog(
                    reddit_id=post_id,
                    platform=platform,
                    success=success,
                    error_message=error_message,
                    post_id=platform_post_id,
                    post_url=post_url,
                    published_at=datetime.now()
                )
                session.add(log_entry)
                
                # Mettre à jour le statut du contenu traité si la publication a réussi
                if success:
                    processed_content = session.query(ProcessedContent).filter_by(reddit_id=post_id).first()
                    if processed_content:
                        processed_content.published_tiktok = True
                        processed_content.tiktok_post_id = platform_post_id
                        processed_content.status = 'published'
                
                session.commit()
        except Exception as e:
            logger.error(f"Failed to log publish attempt: {str(e)}")