# database/models.py
from sqlalchemy import create_engine, Column, String, Integer, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from config.settings import config


# Créer le moteur SQLAlchemy en fonction de la configuration
if config.database.db_type == 'sqlite':
    engine = create_engine(f'sqlite:///{config.database.db_name}')
elif config.database.db_type == 'postgresql':
    engine = create_engine(
        f'postgresql://{config.database.db_user}:{config.database.db_password}@'
        f'{config.database.db_host}:{config.database.db_port}/{config.database.db_name}'
    )
else:
    # Par défaut, utiliser SQLite
    engine = create_engine('sqlite:///content_machine.db')

# Créer une classe de base pour les modèles
Base = declarative_base()

# Créer une session factory
Session = sessionmaker(bind=engine)

class RedditPost(Base):
    """Modèle pour stocker les posts Reddit scrapés."""
    __tablename__ = 'reddit_posts'
    
    id = Column(Integer, primary_key=True)
    reddit_id = Column(String(20), unique=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    url = Column(String(500))
    subreddit = Column(String(100))
    upvotes = Column(Integer)
    num_comments = Column(Integer)
    created_utc = Column(DateTime)
    author = Column(String(100))
    permalink = Column(String(500))
    status = Column(String(20), default='new')  # new, processed, published, rejected
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relations
    processed_content = relationship("ProcessedContent", back_populates="reddit_post", uselist=False)
    media_content = relationship("MediaContent", back_populates="reddit_post", uselist=False)

class ProcessedContent(Base):
    """Modèle pour stocker le contenu traité."""
    __tablename__ = 'processed_contents'
    
    id = Column(Integer, primary_key=True)
    reddit_id = Column(String(20), ForeignKey('reddit_posts.reddit_id'), unique=True)
    keywords = Column(Text)  # Liste de mots-clés séparés par des virgules
    hashtags = Column(Text)  # Liste de hashtags séparés par des virgules
    instagram_caption = Column(Text)
    tiktok_caption = Column(Text)
    status = Column(String(20), default='pending_validation')  # pending_validation, validated, rejected, published
    has_media = Column(Boolean, default=False)
    published_instagram = Column(Boolean, default=False)
    published_tiktok = Column(Boolean, default=False)
    instagram_post_id = Column(String(100))
    tiktok_post_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relations
    reddit_post = relationship("RedditPost", back_populates="processed_content")

class MediaContent(Base):
    """Modèle pour stocker les informations sur les médias."""
    __tablename__ = 'media_contents'
    
    id = Column(Integer, primary_key=True)
    reddit_id = Column(String(20), ForeignKey('reddit_posts.reddit_id'), unique=True)
    media_type = Column(String(20))  # image, video
    file_path = Column(String(500))
    source_url = Column(String(500))
    source = Column(String(50))  # unsplash, pexels, pixabay, fallback
    source_id = Column(String(100))
    width = Column(Integer)
    height = Column(Integer)
    keywords = Column(Text)  # Mots-clés utilisés pour trouver l'image
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relations
    reddit_post = relationship("RedditPost", back_populates="media_content")

class PublishLog(Base):
    """Modèle pour enregistrer les tentatives de publication."""
    __tablename__ = 'publish_logs'
    
    id = Column(Integer, primary_key=True)
    reddit_id = Column(String(20), ForeignKey('reddit_posts.reddit_id'))
    platform = Column(String(20))  # instagram, tiktok
    success = Column(Boolean)
    error_message = Column(Text)
    post_id = Column(String(100))  # ID du post sur la plateforme
    post_url = Column(String(500))  # URL du post publié
    published_at = Column(DateTime, default=datetime.now)

class AIGenerationLog(Base):
    """Modèle pour enregistrer les appels à l'API Claude."""
    __tablename__ = 'ai_generation_logs'
    
    id = Column(Integer, primary_key=True)
    reddit_id = Column(String(20), ForeignKey('reddit_posts.reddit_id'))
    task = Column(String(50))  # caption_generation, keyword_extraction, etc.
    prompt = Column(Text)
    response = Column(Text)
    tokens_used = Column(Integer)
    success = Column(Boolean)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
# Créer les tables dans la base de données si elles n'existent pas
def init_db():
    """Initialiser la base de données avec les tables nécessaires."""
    Base.metadata.create_all(engine)