# core/scraper/base_scraper.py
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.error_handler import handle_scraping_error
from database.models import Session

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Classe abstraite pour les scrapers de contenu."""
    
    def __init__(self, source_name: str):
        """
        Initialiser le scraper de base.
        
        Args:
            source_name: Nom de la source (reddit, twitter, etc.).
        """
        self.source_name = source_name
        logger.info(f"{source_name.capitalize()} scraper initialized")
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialiser la connexion à la source de données.
        
        Returns:
            True si l'initialisation a réussi, False sinon.
        """
        pass
    
    @abstractmethod
    def get_trending_content(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Récupérer le contenu tendance de la source.
        
        Args:
            **kwargs: Arguments spécifiques à la source.
            
        Returns:
            Liste de contenu récupéré.
        """
        pass
    
    @abstractmethod
    def save_content_to_db(self, content: Dict[str, Any]) -> Optional[str]:
        """
        Sauvegarder le contenu dans la base de données.
        
        Args:
            content: Contenu à sauvegarder.
            
        Returns:
            ID du contenu sauvegardé ou None en cas d'erreur.
        """
        pass
    
    def scrape(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Effectuer le scraping avec gestion des erreurs.
        
        Args:
            **kwargs: Arguments spécifiques au scraper.
            
        Returns:
            Liste de contenu récupéré.
        """
        try:
            # Initialiser la connexion
            if not self.initialize():
                error_msg = f"Failed to initialize {self.source_name} scraper"
                logger.error(error_msg)
                handle_scraping_error(f"{self.source_name}_init", error_msg)
                return []
            
            # Récupérer le contenu
            content_list = self.get_trending_content(**kwargs)
            
            # Filtrer et sauvegarder le contenu
            saved_content = []
            for content in content_list:
                # Appliquer des filtres spécifiques à la source
                if self.filter_content(content):
                    # Sauvegarder dans la base de données
                    content_id = self.save_content_to_db(content)
                    if content_id:
                        content['id'] = content_id
                        saved_content.append(content)
            
            logger.info(f"Scraping {self.source_name} completed. Retrieved {len(content_list)} items, saved {len(saved_content)}.")
            return saved_content
            
        except Exception as e:
            error_msg = f"Error scraping {self.source_name}: {str(e)}"
            logger.error(error_msg)
            handle_scraping_error(f"{self.source_name}_scraping", error_msg)
            return []
    
    def filter_content(self, content: Dict[str, Any]) -> bool:
        """
        Filtrer le contenu selon des critères.
        
        Args:
            content: Contenu à filtrer.
            
        Returns:
            True si le contenu doit être conservé, False sinon.
        """
        # Par défaut, conserver tout le contenu
        # Les classes enfants peuvent surcharger cette méthode
        return True
    
    def clean_content(self, text: str) -> str:
        """
        Nettoyer le texte du contenu (supprimer les caractères indésirables, etc.).
        
        Args:
            text: Texte à nettoyer.
            
        Returns:
            Texte nettoyé.
        """
        # Méthode de base pour nettoyer le texte
        # Les classes enfants peuvent surcharger cette méthode
        if not text:
            return ""
        
        # Supprimer les caractères de contrôle et les espaces multiples
        import re
        text = re.sub(r'[\r\n\t]+', ' ', text)  # Remplacer les sauts de ligne par des espaces
        text = re.sub(r'\s+', ' ', text)        # Supprimer les espaces multiples
        return text.strip()
    
    def extract_keywords(self, text: str, title: str = None) -> List[str]:
        """
        Extraire des mots-clés du contenu.
        
        Args:
            text: Texte du contenu.
            title: Titre du contenu (optionnel).
            
        Returns:
            Liste de mots-clés.
        """
        # Méthode de base pour extraire des mots-clés
        # Les classes enfants peuvent implémenter des méthodes plus sophistiquées
        import re
        from collections import Counter
        
        # Combiner le titre et le texte si disponible
        combined_text = f"{title} {text}" if title else text
        
        # Convertir en minuscules et supprimer la ponctuation
        words = re.findall(r'\b\w+\b', combined_text.lower())
        
        # Supprimer les mots courts et les mots vides
        stop_words = {'the', 'and', 'is', 'in', 'it', 'to', 'a', 'of', 'for', 'with', 'on', 'at', 'by', 'from', 'that', 'this', 'are', 'was', 'were', 'be', 'have', 'has', 'had', 'not', 'but', 'what', 'all', 'when', 'who', 'how', 'why', 'where', 'which', 'or', 'so', 'if', 'as', 'an', 'would', 'could', 'should'}
        filtered_words = [word for word in words if len(word) > 3 and word not in stop_words]
        
        # Compter les occurrences
        word_counts = Counter(filtered_words)
        
        # Retourner les mots les plus fréquents (maximum 10)
        return [word for word, _ in word_counts.most_common(10)]