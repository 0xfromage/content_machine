# core/publisher/instagram_publisher.py
import logging
import time
import os
from typing import Dict, Any
from datetime import datetime
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, MediaError, ClientError

from config.settings import config
from utils.error_handler import handle_publishing_error
from database.models import PublishLog, ProcessedContent, Session

logger = logging.getLogger(__name__)

class InstagramPublisher:
    """Classe pour publier du contenu sur Instagram."""
    
    def __init__(self):
        """Initialiser le client Instagram avec les identifiants."""
        self.username = config.instagram.username
        self.password = config.instagram.password
        self.access_token = config.instagram.access_token
        self.client = Client()
        self.is_logged_in = False
        
        # Essayer de se connecter au démarrage si les identifiants sont disponibles
        if self.username and self.password:
            self._login()
    
    def _login(self) -> bool:
        """
        Se connecter à Instagram.
        
        Returns:
            True si la connexion a réussi, False sinon.
        """
        try:
            # Vérifier si un fichier de session existe
            session_file = f"instagram_session_{self.username}.json"
            if os.path.exists(session_file):
                # Charger la session existante
                self.client.load_settings(session_file)
                self.client.get_timeline_feed()  # Tester si la session est valide
                self.is_logged_in = True
                logger.info(f"Instagram session loaded for {self.username}")
                return True
            
            # Se connecter avec les identifiants
            self.client.login(self.username, self.password)
            
            # Sauvegarder la session pour une utilisation future
            self.client.dump_settings(session_file)
            
            self.is_logged_in = True
            logger.info(f"Successfully logged in to Instagram as {self.username}")
            return True
            
        except LoginRequired:
            # La session a expiré, essayer de se reconnecter
            try:
                if os.path.exists(session_file):
                    os.remove(session_file)  # Supprimer la session invalide
                
                self.client.login(self.username, self.password)
                self.client.dump_settings(session_file)
                self.is_logged_in = True
                logger.info(f"Re-logged in to Instagram as {self.username}")
                return True
            except Exception as e:
                logger.error(f"Failed to re-login to Instagram: {str(e)}")
                self.is_logged_in = False
                return False
                
        except Exception as e:
            logger.error(f"Failed to login to Instagram: {str(e)}")
            self.is_logged_in = False
            return False
    
    def publish(self, media_path: str, caption: str, post_id: str) -> Dict[str, Any]:
        """
        Publier une image sur Instagram.
        
        Args:
            media_path: Chemin vers l'image à publier.
            caption: Légende de l'image.
            post_id: ID du post Reddit associé.
            
        Returns:
            Dictionnaire contenant le statut de la publication.
        """
        if not self.is_logged_in and not self._login():
            error_msg = "Not logged in to Instagram and login failed"
            logger.error(error_msg)
            self._log_publish_attempt(post_id, "instagram", False, error_msg)
            return {"success": False, "error": error_msg}
        
        try:
            # Vérifier si le fichier média existe
            if not os.path.exists(media_path):
                error_msg = f"Media file not found: {media_path}"
                logger.error(error_msg)
                self._log_publish_attempt(post_id, "instagram", False, error_msg)
                return {"success": False, "error": error_msg}
            
            # Ajouter un délai pour éviter les limitations d'API
            time.sleep(2)
            
            # Publier l'image
            media = self.client.photo_upload(
                path=media_path,
                caption=caption
            )
            
            # Récupérer l'ID et l'URL du post publié
            instagram_post_id = media.id
            instagram_post_url = f"https://www.instagram.com/p/{media.code}/"
            
            # Logger la publication réussie
            logger.info(f"Successfully published to Instagram: {instagram_post_url}")
            self._log_publish_attempt(
                post_id=post_id,
                platform="instagram",
                success=True,
                post_id=instagram_post_id,
                post_url=instagram_post_url
            )
            
            return {
                "success": True,
                "post_id": instagram_post_id,
                "post_url": instagram_post_url
            }
            
        except MediaError as e:
            error_msg = f"Instagram media error: {str(e)}"
            logger.error(error_msg)
            handle_publishing_error("instagram", error_msg, post_id=post_id)
            self._log_publish_attempt(post_id, "instagram", False, error_msg)
            return {"success": False, "error": error_msg}
            
        except ClientError as e:
            error_msg = f"Instagram client error: {str(e)}"
            logger.error(error_msg)
            handle_publishing_error("instagram", error_msg, post_id=post_id)
            self._log_publish_attempt(post_id, "instagram", False, error_msg)
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"Error publishing to Instagram: {str(e)}"
            logger.error(error_msg)
            handle_publishing_error("instagram", error_msg, post_id=post_id)
            self._log_publish_attempt(post_id, "instagram", False, error_msg)
            return {"success": False, "error": error_msg}
    
    def _log_publish_attempt(self, post_id: str, platform: str, success: bool, 
                            error_message: str = None, post_id: str = None, 
                            post_url: str = None) -> None:
        """
        Enregistrer une tentative de publication dans la base de données.
        
        Args:
            post_id: ID du post Reddit.
            platform: Plateforme (instagram).
            success: Si la publication a réussi.
            error_message: Message d'erreur éventuel.
            post_id: ID du post sur la plateforme.
            post_url: URL du post publié.
        """
        try:
            with Session() as session:
                log_entry = PublishLog(
                    reddit_id=post_id,
                    platform=platform,
                    success=success,
                    error_message=error_message,
                    post_id=post_id,
                    post_url=post_url,
                    published_at=datetime.now()
                )
                session.add(log_entry)
                
                # Mettre à jour le statut du contenu traité si la publication a réussi
                if success:
                    processed_content = session.query(ProcessedContent).filter_by(reddit_id=post_id).first()
                    if processed_content:
                        processed_content.published_instagram = True
                        processed_content.instagram_post_id = post_id
                        processed_content.status = 'published'
                
                session.commit()
        except Exception as e:
            logger.error(f"Failed to log publish attempt: {str(e)}")