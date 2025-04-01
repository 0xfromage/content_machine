# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# Charger les variables d'environnement depuis le fichier .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

@dataclass
class RedditConfig:
    """Configuration pour le scraping de Reddit."""
    client_id: str = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    user_agent: str = os.getenv("REDDIT_USER_AGENT", "ContentMachine/1.0")
    subreddits: List[str] = None
    min_upvotes: int = 1000
    post_limit: int = 50
    time_filter: str = "day"  # hour, day, week, month, year, all
    
    def __post_init__(self):
        # Convertir la chaîne de caractères séparée par des virgules en liste
        if self.subreddits is None:
            subreddits_str = os.getenv("REDDIT_SUBREDDITS", "todayilearned")
            self.subreddits = [s.strip() for s in subreddits_str.split(",")]
        
        # Convertir les valeurs numériques
        try:
            self.min_upvotes = int(os.getenv("REDDIT_MIN_UPVOTES", "1000"))
            self.post_limit = int(os.getenv("REDDIT_POST_LIMIT", "50"))
        except ValueError:
            # Valeurs par défaut en cas d'erreur
            self.min_upvotes = 1000
            self.post_limit = 50

@dataclass
class MediaConfig:
    """Configuration pour la recherche de médias."""
    unsplash_access_key: str = os.getenv("UNSPLASH_ACCESS_KEY", "")
    unsplash_secret_key: str = os.getenv("UNSPLASH_SECRET_KEY", "")
    unsplash_app_id: str = os.getenv("UNSPLASH_APP_ID", "")
    pexels_api_key: str = os.getenv("PEXELS_API_KEY", "")
    pixabay_api_key: str = os.getenv("PIXABAY_API_KEY", "")
    image_width: int = 1080
    image_height: int = 1080
    fallback_image_path: str = os.getenv("FALLBACK_IMAGE_PATH", "resources/default.jpg")

@dataclass
class InstagramConfig:
    """Configuration pour Instagram."""
    username: str = os.getenv("INSTAGRAM_USERNAME", "")
    password: str = os.getenv("INSTAGRAM_PASSWORD", "")
    # OU utiliser le token d'accès si vous utilisez l'API officielle
    access_token: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    max_caption_length: int = 2200
    max_hashtags: int = 30

@dataclass
class TikTokConfig:
    """Configuration pour TikTok."""
    username: str = os.getenv("TIKTOK_USERNAME", "")
    password: str = os.getenv("TIKTOK_PASSWORD", "")
    # OU utiliser le token d'accès si vous utilisez l'API officielle
    access_token: str = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    max_caption_length: int = 150
    max_hashtags: int = 10

@dataclass
class DatabaseConfig:
    """Configuration pour la base de données."""
    db_type: str = os.getenv("DB_TYPE", "sqlite")  # sqlite, postgresql, etc.
    db_name: str = os.getenv("DB_NAME", "content_machine.db")
    db_user: Optional[str] = os.getenv("DB_USER", None)
    db_password: Optional[str] = os.getenv("DB_PASSWORD", None)
    db_host: Optional[str] = os.getenv("DB_HOST", None)
    db_port: Optional[int] = None
    
    def __post_init__(self):
        port = os.getenv("DB_PORT")
        if port:
            try:
                self.db_port = int(port)
            except ValueError:
                self.db_port = None

@dataclass
class AppConfig:
    """Configuration globale de l'application."""
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    web_interface_port: int = int(os.getenv("WEB_INTERFACE_PORT", "8501"))
    auto_publish: bool = os.getenv("AUTO_PUBLISH", "False").lower() == "true"
    
    # Use default_factory instead of direct instantiation
    reddit: RedditConfig = field(default_factory=RedditConfig)
    media: MediaConfig = field(default_factory=MediaConfig)
    instagram: InstagramConfig = field(default_factory=InstagramConfig)
    tiktok: TikTokConfig = field(default_factory=TikTokConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

# Instance unique de configuration à utiliser dans toute l'application
config = AppConfig()