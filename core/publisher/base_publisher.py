# core/publisher/base_publisher.py
import logging
import os
import time
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime

from config.settings import config
from utils.error_handler import handle_publishing_error
from database.models import PublishLog, ProcessedContent, Session

logger = logging.getLogger(__name__)

class BasePublisher(ABC):
    """Classe abstraite pour les publishers de contenu sur les réseaux sociaux."""
    
    def __init__(self, platform_name: str):
        """
        Initialiser le publisher de base.
        
        Args:
            platform_name: Nom de la plateforme (instagram, tiktok, etc.).
        """
        self.platform_name = platform_name
        self.retry_count = 3
        self.retry_delay = 5  # secondes
        logger.info(f"{platform_name.capitalize()} publisher initialized")
    
    @abstractmethod
    def login(self) -> bool:
        """
        Se connecter à la plateforme.
        
        Returns:
            True si la connexion a réussi, False sinon.
        """
        pass
    
    @abstractmethod
    def publish_media(self, media_path: str, caption: str, **kwargs) -> Dict[str, Any]:
        """
        Publier un média sur la plateforme.
        
        Args:
            media_path: Chemin vers le média à publier.
            caption: Légende du post.
            **kwargs: Arguments supplémentaires spécifiques à la plateforme.
            
        Returns:
            Dictionnaire contenant le statut de la publication et d'autres informations.
        """
        pass
    
    def publish(self, media_path: str, caption: str, post_id: str, **kwargs) -> Dict[str, Any]:
        """
        Publier du contenu sur la plateforme avec gestion des erreurs et des tentatives.
        
        Args:
            media_path: Chemin vers le média à publier.
            caption: Légende du post.
            post_id: ID du post associé pour le suivi.
            **kwargs: Arguments supplémentaires spécifiques à la plateforme.
            
        Returns:
            Dictionnaire contenant le statut de la publication.
        """
        # Vérifier si le fichier existe
        if not os.path.exists(media_path):
            error_msg = f"Media file not found: {media_path}"
            logger.error(error_msg)
            self._log_publish_attempt(post_id, success=False, error_message=error_msg)
            return {"success": False, "error": error_msg}
        
        # Tenter de publier avec des essais répétés si nécessaire
        for attempt in range(1, self.retry_count + 1):
            try:
                # S'assurer que la connexion est établie
                if not self.login():
                    error_msg = f"Failed to login to {self.platform_name}"
                    logger.error(error_msg)
                    if attempt == self.retry_count:
                        self._log_publish_attempt(post_id, success=False, error_message=error_msg)
                        return {"success": False, "error": error_msg}
                    continue
                
                # Publier le média
                result = self.publish_media(media_path, caption, **kwargs)
                
                # Si la publication a réussi, mettre à jour la base de données
                if result.get('success'):
                    self._log_publish_attempt(
                        post_id=post_id,
                        success=True,
                        post_id=result.get('post_id'),
                        post_url=result.get('post_url')
                    )
                    
                    # Mettre à jour le statut du contenu traité
                    self._update_content_status(post_id, result.get('post_id'))
                    
                    logger.info(f"Successfully published to {self.platform_name}: {result.get('post_url')}")
                    return result
                else:
                    error_msg = result.get('error', f"Unknown error publishing to {self.platform_name}")
                    logger.warning(f"Attempt {attempt}/{self.retry_count}: {error_msg}")
                    
                    # Si c'est la dernière tentative, enregistrer l'échec
                    if attempt == self.retry_count:
                        self._log_publish_attempt(post_id, success=False, error_message=error_msg)
                        return result
            
            except Exception as e:
                error_msg = f"Error publishing to {self.platform_name}: {str(e)}"
                logger.error(f"Attempt {attempt}/{self.retry_count}: {error_msg}")
                handle_publishing_error(self.platform_name, error_msg, post_id=post_id)
                
                # Si c'est la dernière tentative, enregistrer l'échec
                if attempt == self.retry_count:
                    self._log_publish_attempt(post_id, success=False, error_message=error_msg)
                    return {"success": False, "error": error_msg}
            
            # Attendre avant de réessayer
            if attempt < self.retry_count:
                time.sleep(self.retry_delay * attempt)  # Augmenter le délai à chaque tentative
    
    def _log_publish_attempt(self, post_id: str, success: bool, error_message: str = None, 
                           post_id: str = None, post_url: str = None) -> None:
        """
        Enregistrer une tentative de publication dans la base de données.
        
        Args:
            post_id: ID du post Reddit.
            success: Si la publication a réussi.
            error_message: Message d'erreur éventuel.
            post_id: ID du post sur la plateforme.
            post_url: URL du post publié.
        """
        try:
            with Session() as session:
                log_entry = PublishLog(
                    reddit_id=post_id,
                    platform=self.platform_name,
                    success=success,
                    error_message=error_message,
                    post_id=post_id,
                    post_url=post_url,
                    published_at=datetime.now()
                )
                session.add(log_entry)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to log publish attempt: {str(e)}")
    
    def _update_content_status(self, reddit_id: str, platform_post_id: str) -> None:
        """
        Mettre à jour le statut du contenu traité après publication.
        
        Args:
            reddit_id: ID du post Reddit.
            platform_post_id: ID du post sur la plateforme.
        """
        try:
            with Session() as session:
                processed_content = session.query(ProcessedContent).filter_by(reddit_id=reddit_id).first()
                if processed_content:
                    processed_content.status = 'published'
                    
                    # Mettre à jour le statut spécifique à la plateforme
                    if self.platform_name == 'instagram':
                        processed_content.published_instagram = True
                        processed_content.instagram_post_id = platform_post_id
                    elif self.platform_name == 'tiktok':
                        processed_content.published_tiktok = True
                        processed_content.tiktok_post_id = platform_post_id
                    
                    processed_content.updated_at = datetime.now()
                    session.commit()
        except Exception as e:
            logger.error(f"Failed to update content status: {str(e)}")