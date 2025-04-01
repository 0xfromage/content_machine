# utils/error_handler.py
import logging
import traceback
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Configurer le logger pour ce module
logger = logging.getLogger(__name__)

# Créer le dossier des erreurs s'il n'existe pas
os.makedirs("logs/errors", exist_ok=True)

def handle_scraping_error(error_type: str, error_message: str, **additional_info) -> None:
    """
    Gérer une erreur de scraping.
    
    Args:
        error_type: Type d'erreur (reddit_init, reddit_scraping, etc.).
        error_message: Message d'erreur.
        additional_info: Informations supplémentaires sur l'erreur.
    """
    _log_error("scraping", error_type, error_message, additional_info)

def handle_processing_error(error_type: str, error_message: str, **additional_info) -> None:
    """
    Gérer une erreur de traitement.
    
    Args:
        error_type: Type d'erreur (text_processing, etc.).
        error_message: Message d'erreur.
        additional_info: Informations supplémentaires sur l'erreur.
    """
    _log_error("processing", error_type, error_message, additional_info)

def handle_media_error(error_type: str, error_message: str, **additional_info) -> None:
    """
    Gérer une erreur de recherche de média.
    
    Args:
        error_type: Type d'erreur (image_finding, etc.).
        error_message: Message d'erreur.
        additional_info: Informations supplémentaires sur l'erreur.
    """
    _log_error("media", error_type, error_message, additional_info)

def handle_publishing_error(error_type: str, error_message: str, **additional_info) -> None:
    """
    Gérer une erreur de publication.
    
    Args:
        error_type: Type d'erreur (instagram, tiktok, etc.).
        error_message: Message d'erreur.
        additional_info: Informations supplémentaires sur l'erreur.
    """
    _log_error("publishing", error_type, error_message, additional_info)

def handle_general_error(error_type: str, error_message: str, **additional_info) -> None:
    """
    Gérer une erreur générale.
    
    Args:
        error_type: Type d'erreur.
        error_message: Message d'erreur.
        additional_info: Informations supplémentaires sur l'erreur.
    """
    _log_error("general", error_type, error_message, additional_info)

def _log_error(category: str, error_type: str, error_message: str, additional_info: Dict[str, Any]) -> None:
    """
    Enregistrer une erreur dans le fichier de log et la console.
    
    Args:
        category: Catégorie de l'erreur (scraping, processing, etc.).
        error_type: Type d'erreur.
        error_message: Message d'erreur.
        additional_info: Informations supplémentaires sur l'erreur.
    """
    # Récupérer le traceback complet
    tb = traceback.format_exc()
    
    # Créer l'objet d'erreur
    error_object = {
        "timestamp": datetime.now().isoformat(),
        "category": category,
        "error_type": error_type,
        "error_message": error_message,
        "traceback": tb,
        "additional_info": additional_info
    }
    
    # Loguer l'erreur de manière formattée
    logger.error(
        f"[{category.upper()}] {error_type}: {error_message}",
        extra={"additional_info": additional_info}
    )
    
    # Enregistrer l'erreur dans un fichier JSON
    error_file = f"logs/errors/{category}_{datetime.now().strftime('%Y%m%d')}.json"
    
    try:
        # Charger les erreurs existantes si le fichier existe
        if os.path.exists(error_file):
            with open(error_file, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        else:
            errors = []
        
        # Ajouter la nouvelle erreur
        errors.append(error_object)
        
        # Enregistrer le fichier mis à jour
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(errors, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du log d'erreur: {str(e)}")