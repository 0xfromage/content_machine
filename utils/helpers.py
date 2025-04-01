# utils/helpers.py
import logging
import re
import os
import random
import string
import time
import unicodedata
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import emoji
import json

logger = logging.getLogger(__name__)

def slugify(text: str) -> str:
    """
    Convertir un texte en un slug URL-friendly.
    
    Args:
        text: Texte à convertir en slug.
        
    Returns:
        Slug URL-friendly.
    """
    # Normaliser les caractères unicode
    text = unicodedata.normalize('NFKD', text)
    
    # Supprimer les accents
    text = ''.join([c for c in text if not unicodedata.combining(c)])
    
    # Convertir en minuscules
    text = text.lower()
    
    # Remplacer les espaces par des tirets
    text = re.sub(r'\s+', '-', text)
    
    # Supprimer les caractères non alphanumériques
    text = re.sub(r'[^\w\-]', '', text)
    
    # Supprimer les tirets multiples
    text = re.sub(r'\-+', '-', text)
    
    # Supprimer les tirets au début et à la fin
    text = text.strip('-')
    
    return text

def generate_random_string(length: int = 10) -> str:
    """
    Générer une chaîne aléatoire.
    
    Args:
        length: Longueur de la chaîne.
        
    Returns:
        Chaîne aléatoire.
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_current_timestamp() -> int:
    """
    Obtenir le timestamp actuel en secondes.
    
    Returns:
        Timestamp actuel.
    """
    return int(time.time())

def format_timestamp(timestamp: int, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Formater un timestamp en chaîne de date.
    
    Args:
        timestamp: Timestamp à formater.
        format_str: Format de la date.
        
    Returns:
        Chaîne de date formatée.
    """
    return datetime.fromtimestamp(timestamp).strftime(format_str)

def get_date_range(days: int) -> Tuple[datetime, datetime]:
    """
    Obtenir une plage de dates.
    
    Args:
        days: Nombre de jours dans le passé.
        
    Returns:
        Tuple de (date_début, date_fin).
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date

def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
    """
    Tronquer un texte à une longueur maximale.
    
    Args:
        text: Texte à tronquer.
        max_length: Longueur maximale.
        suffix: Suffixe à ajouter si le texte est tronqué.
        
    Returns:
        Texte tronqué.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def clean_html(html: str) -> str:
    """
    Nettoyer le HTML en supprimant les balises.
    
    Args:
        html: HTML à nettoyer.
        
    Returns:
        Texte sans HTML.
    """
    # Supprimer les balises HTML
    text = re.sub(r'<[^>]+>', '', html)
    
    # Remplacer les entités HTML courantes
    html_entities = {
        '&nbsp;': ' ',
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&apos;': "'",
    }
    
    for entity, replacement in html_entities.items():
        text = text.replace(entity, replacement)
    
    # Supprimer les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def extract_urls(text: str) -> List[str]:
    """
    Extraire les URLs d'un texte.
    
    Args:
        text: Texte contenant des URLs.
        
    Returns:
        Liste d'URLs.
    """
    # Pattern pour détecter les URLs
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    
    # Trouver toutes les correspondances
    urls = re.findall(url_pattern, text)
    
    return urls

def get_file_extension(filename: str) -> str:
    """
    Obtenir l'extension d'un fichier.
    
    Args:
        filename: Nom du fichier.
        
    Returns:
        Extension du fichier.
    """
    return os.path.splitext(filename)[1].lower()

def is_image_file(filename: str) -> bool:
    """
    Vérifier si un fichier est une image.
    
    Args:
        filename: Nom du fichier.
        
    Returns:
        True si le fichier est une image, False sinon.
    """
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    return get_file_extension(filename) in image_extensions

def is_video_file(filename: str) -> bool:
    """
    Vérifier si un fichier est une vidéo.
    
    Args:
        filename: Nom du fichier.
        
    Returns:
        True si le fichier est une vidéo, False sinon.
    """
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    return get_file_extension(filename) in video_extensions

def get_file_size(file_path: str) -> int:
    """
    Obtenir la taille d'un fichier en octets.
    
    Args:
        file_path: Chemin du fichier.
        
    Returns:
        Taille du fichier en octets.
    """
    return os.path.getsize(file_path)

def format_file_size(size_in_bytes: int) -> str:
    """
    Formater la taille d'un fichier en format lisible.
    
    Args:
        size_in_bytes: Taille en octets.
        
    Returns:
        Taille formatée.
    """
    # Convertir en unités lisibles par l'homme
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_in_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"

def add_emojis(text: str, count: int = 2) -> str:
    """
    Ajouter des emojis aléatoires au début d'un texte.
    
    Args:
        text: Texte auquel ajouter des emojis.
        count: Nombre d'emojis à ajouter.
        
    Returns:
        Texte avec emojis.
    """
    # Liste d'emojis populaires
    emoji_list = ['✨', '🔥', '💡', '🎯', '🚀', '💪', '👍', '🌟', '⭐', '📌', 
                  '📚', '🧠', '👀', '🌈', '🎬', '🎮', '🎧', '📱', '💻', '📷']
    
    # Sélectionner des emojis aléatoires
    selected_emojis = random.sample(emoji_list, min(count, len(emoji_list)))
    
    # Ajouter les emojis au début du texte
    return ' '.join(selected_emojis) + ' ' + text

def count_words(text: str) -> int:
    """
    Compter le nombre de mots dans un texte.
    
    Args:
        text: Texte à analyser.
        
    Returns:
        Nombre de mots.
    """
    # Supprimer les emojis
    text = emoji.replace_emoji(text, '')
    
    # Compter les mots
    words = re.findall(r'\b\w+\b', text)
    return len(words)

def save_json(data: Any, file_path: str) -> bool:
    """
    Sauvegarder des données au format JSON.
    
    Args:
        data: Données à sauvegarder.
        file_path: Chemin du fichier.
        
    Returns:
        True si la sauvegarde a réussi, False sinon.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON: {str(e)}")
        return False

def load_json(file_path: str) -> Optional[Any]:
    """
    Charger des données JSON depuis un fichier.
    
    Args:
        file_path: Chemin du fichier.
        
    Returns:
        Données chargées ou None en cas d'erreur.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON: {str(e)}")
        return None

def retry(func, max_attempts: int = 3, delay: int = 1):
    """
    Décorateur pour réessayer une fonction en cas d'échec.
    
    Args:
        func: Fonction à décorer.
        max_attempts: Nombre maximum de tentatives.
        delay: Délai en secondes entre les tentatives.
        
    Returns:
        Fonction décorée.
    """
    def wrapper(*args, **kwargs):
        attempts = 0
        while attempts < max_attempts:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                if attempts == max_attempts:
                    raise
                logger.warning(f"Retry {attempts}/{max_attempts} for {func.__name__}: {str(e)}")
                time.sleep(delay)
    return wrapper