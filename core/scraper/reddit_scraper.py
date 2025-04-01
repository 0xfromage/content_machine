# core/scraper/reddit_scraper.py
import praw
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from config.settings import config
from utils.error_handler import handle_scraping_error
from database.models import RedditPost, Session

logger = logging.getLogger(__name__)

class RedditScraper:
    """Classe pour scraper des posts Reddit à partir de subreddits spécifiés."""
    
    def __init__(self):
        """Initialiser le scraper Reddit avec les identifiants d'API."""
        try:
            self.reddit = praw.Reddit(
                client_id=config.reddit.client_id,
                client_secret=config.reddit.client_secret,
                user_agent=config.reddit.user_agent
            )
            logger.info("Reddit scraper initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit scraper: {str(e)}")
            handle_scraping_error("reddit_init", str(e))
            raise
    
    def get_trending_posts(self, subreddit_name: str = None, limit: int = None, min_upvotes: int = None) -> List[Dict[str, Any]]:
        """
        Récupérer les posts tendance d'un subreddit spécifié.
        
        Args:
            subreddit_name: Nom du subreddit à scraper. Si None, utilise la configuration.
            limit: Nombre de posts à récupérer. Si None, utilise la configuration.
            min_upvotes: Nombre minimum d'upvotes requis. Si None, utilise la configuration.
            
        Returns:
            Liste de posts filtrés sous forme de dictionnaires.
        """
        if subreddit_name is None:
            # Utiliser le premier subreddit de la liste de configuration
            subreddit_name = config.reddit.subreddits[0]
        
        if limit is None:
            limit = config.reddit.post_limit
            
        if min_upvotes is None:
            min_upvotes = config.reddit.min_upvotes
        
        collected_posts = []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Obtenir les messages populaires de la journée
            posts = subreddit.top(time_filter=config.reddit.time_filter, limit=limit)
            
            for post in posts:
                # Filtrer les posts qui n'ont pas assez d'upvotes
                if post.score < min_upvotes:
                    continue
                    
                # Vérifier si le post a déjà été traité (stocké en base de données)
                with Session() as session:
                    existing_post = session.query(RedditPost).filter_by(reddit_id=post.id).first()
                    if existing_post:
                        logger.debug(f"Post {post.id} already processed, skipping")
                        continue
                
                # Extraire et formater les données pertinentes
                post_data = {
                    'reddit_id': post.id,
                    'title': post.title,
                    'content': post.selftext if hasattr(post, 'selftext') else "",
                    'url': post.url,
                    'subreddit': post.subreddit.display_name,
                    'upvotes': post.score,
                    'num_comments': post.num_comments,
                    'created_utc': datetime.fromtimestamp(post.created_utc),
                    'author': post.author.name if post.author else "[deleted]",
                    'permalink': post.permalink
                }
                
                # Filtrer les posts NSFW si nécessaire
                if hasattr(post, 'over_18') and post.over_18:
                    logger.debug(f"Skipping NSFW post {post.id}")
                    continue
                
                collected_posts.append(post_data)
                
                # Enregistrer le post dans la base de données
                self._save_post_to_db(post_data)
                
            logger.info(f"Retrieved {len(collected_posts)} posts from r/{subreddit_name}")
            return collected_posts
            
        except Exception as e:
            error_msg = f"Error scraping Reddit: {str(e)}"
            logger.error(error_msg)
            handle_scraping_error("reddit_scraping", error_msg, subreddit=subreddit_name)
            return []
    
    def get_posts_from_all_subreddits(self) -> List[Dict[str, Any]]:
        """
        Récupérer les posts de tous les subreddits configurés.
        
        Returns:
            Liste combinée de posts de tous les subreddits.
        """
        all_posts = []
        
        for subreddit in config.reddit.subreddits:
            try:
                posts = self.get_trending_posts(subreddit)
                all_posts.extend(posts)
            except Exception as e:
                logger.error(f"Failed to retrieve posts from r/{subreddit}: {str(e)}")
                handle_scraping_error("subreddit_scraping", str(e), subreddit=subreddit)
                continue
        
        return all_posts
    
    def _save_post_to_db(self, post_data: Dict[str, Any]) -> None:
        """
        Enregistrer un post dans la base de données.
        
        Args:
            post_data: Données du post à enregistrer.
        """
        try:
            with Session() as session:
                reddit_post = RedditPost(
                    reddit_id=post_data['reddit_id'],
                    title=post_data['title'],
                    content=post_data['content'],
                    url=post_data['url'],
                    subreddit=post_data['subreddit'],
                    upvotes=post_data['upvotes'],
                    num_comments=post_data['num_comments'],
                    created_utc=post_data['created_utc'],
                    author=post_data['author'],
                    permalink=post_data['permalink'],
                    status='new'  # Statut initial: nouveau post
                )
                session.add(reddit_post)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to save post to database: {str(e)}")
            # Ne pas lever l'exception pour éviter d'interrompre le processus de scraping