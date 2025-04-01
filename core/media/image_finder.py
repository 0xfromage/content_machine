# core/media/image_finder.py
import os
import logging
import requests
import random
from typing import Dict, List, Any, Optional
from PIL import Image
from io import BytesIO
import time

from config.settings import config
from utils.error_handler import handle_media_error
from database.models import ProcessedContent, MediaContent, Session

logger = logging.getLogger(__name__)

class ImageFinder:
    """Classe pour rechercher des images pertinentes basées sur les mots-clés."""
    
    def __init__(self):
        """Initialiser le chercheur d'images avec les API keys."""
        self.unsplash_api_key = config.media.unsplash_api_key
        self.pexels_api_key = config.media.pexels_api_key
        self.pixabay_api_key = config.media.pixabay_api_key
        self.image_width = config.media.image_width
        self.image_height = config.media.image_height
        self.fallback_image_path = config.media.fallback_image_path
        
        # S'assurer que le dossier des médias existe
        os.makedirs("media/images", exist_ok=True)
        logger.info("Image finder initialized")
    
    def find_image(self, keywords: List[str], post_id: str) -> Dict[str, Any]:
        """
        Rechercher une image pertinente basée sur les mots-clés.
        
        Args:
            keywords: Liste de mots-clés pour la recherche.
            post_id: ID du post pour lequel chercher une image.
            
        Returns:
            Dictionnaire contenant les informations sur l'image trouvée.
        """
        try:
            # Joindre les mots-clés en une seule chaîne de recherche
            search_query = " ".join(keywords[:3])  # Limiter à 3 mots-clés pour de meilleurs résultats
            
            # Essayer chaque API de recherche d'images dans un ordre prédéfini
            image_result = None
            
            # 1. Essayer Unsplash si une clé API est disponible
            if self.unsplash_api_key:
                image_result = self._search_unsplash(search_query)
            
            # 2. Essayer Pexels si Unsplash a échoué et qu'une clé API est disponible
            if not image_result and self.pexels_api_key:
                image_result = self._search_pexels(search_query)
            
            # 3. Essayer Pixabay si les deux précédents ont échoué et qu'une clé API est disponible
            if not image_result and self.pixabay_api_key:
                image_result = self._search_pixabay(search_query)
            
            # Si aucune image n'a été trouvée, utiliser l'image de secours
            if not image_result:
                image_result = self._use_fallback_image()
            
            # Sauvegarder l'image dans la base de données
            self._save_media_to_db(image_result, post_id)
            
            logger.info(f"Found image for post {post_id}: {image_result['source']}")
            return image_result
            
        except Exception as e:
            error_msg = f"Error finding image: {str(e)}"
            logger.error(error_msg)
            handle_media_error("image_finding", error_msg, post_id=post_id)
            
            # En cas d'erreur, utiliser l'image de secours
            fallback_result = self._use_fallback_image()
            self._save_media_to_db(fallback_result, post_id)
            return fallback_result
    
    def _search_unsplash(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Rechercher une image sur Unsplash.
        
        Args:
            query: Terme de recherche.
            
        Returns:
            Informations sur l'image ou None si aucune image n'est trouvée.
        """
        try:
            url = "https://api.unsplash.com/search/photos"
            headers = {"Authorization": f"Client-ID {self.unsplash_access_key}"}
            params = {
                "query": query,
                "per_page": 10,
                "orientation": "square"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data["results"]:
                # Choisir une image aléatoire parmi les résultats
                image = random.choice(data["results"])
                
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
            
            return None
            
        except Exception as e:
            logger.warning(f"Unsplash search failed: {str(e)}")
            return None
    
    def _search_pexels(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Rechercher une image sur Pexels.
        
        Args:
            query: Terme de recherche.
            
        Returns:
            Informations sur l'image ou None si aucune image n'est trouvée.
        """
        try:
            url = "https://api.pexels.com/v1/search"
            headers = {"Authorization": self.pexels_api_key}
            params = {
                "query": query,
                "per_page": 10,
                "size": "medium"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("photos"):
                # Choisir une image aléatoire parmi les résultats
                image = random.choice(data["photos"])
                
                # Télécharger l'image
                image_url = image["src"]["medium"]
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
            
            return None
            
        except Exception as e:
            logger.warning(f"Pexels search failed: {str(e)}")
            return None
    
    def _search_pixabay(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Rechercher une image sur Pixabay.
        
        Args:
            query: Terme de recherche.
            
        Returns:
            Informations sur l'image ou None si aucune image n'est trouvée.
        """
        try:
            url = "https://pixabay.com/api/"
            params = {
                "key": self.pixabay_api_key,
                "q": query,
                "per_page": 10,
                "image_type": "photo"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("hits"):
                # Choisir une image aléatoire parmi les résultats
                image = random.choice(data["hits"])
                
                # Télécharger l'image
                image_url = image["webformatURL"]
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
            
            return None
            
        except Exception as e:
            logger.warning(f"Pixabay search failed: {str(e)}")
            return None
    
    def _use_fallback_image(self) -> Dict[str, Any]:
        """
        Utiliser l'image de secours lorsqu'aucune image pertinente n'est trouvée.
        
        Returns:
            Informations sur l'image de secours.
        """
        return {
            "media_type": "image",
            "file_path": self.fallback_image_path,
            "url": None,
            "source": "fallback",
            "source_id": "default",
            "source_url": None,
            "width": self.image_width,
            "height": self.image_height,
            "keywords": "generic,fallback"
        }
    
    def _download_and_resize_image(self, url: str, save_path: str) -> None:
        """
        Télécharger et redimensionner une image.
        
        Args:
            url: URL de l'image à télécharger.
            save_path: Chemin où sauvegarder l'image.
        """
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Ouvrir l'image avec PIL
        image = Image.open(BytesIO(response.content))
        
        # Redimensionner l'image pour Instagram (ratio carré)
        resized_image = self._resize_image(image)
        
        # Sauvegarder l'image redimensionnée
        resized_image.save(save_path, "JPEG", quality=95)
    
    def _resize_image(self, image: Image.Image) -> Image.Image:
        """
        Redimensionner une image pour les réseaux sociaux.
        
        Args:
            image: Image PIL à redimensionner.
            
        Returns:
            Image redimensionnée.
        """
        # Créer une image carrée (recadrer puis redimensionner)
        width, height = image.size
        
        # Recadrer pour obtenir un carré
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
        
        # Redimensionner à la taille souhaitée
        image = image.resize((self.image_width, self.image_height), Image.LANCZOS)
        
        return image
    
    def _save_media_to_db(self, media_data: Dict[str, Any], post_id: str) -> None:
        """
        Enregistrer les données de l'image dans la base de données.
        
        Args:
            media_data: Informations sur l'image.
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