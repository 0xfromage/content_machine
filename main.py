# main.py
import logging
import time
import argparse
import threading
import sys
import os
from datetime import datetime, timedelta

from config.settings import config
from database.models import init_db, Session, RedditPost, ProcessedContent
from core.scraper.reddit_scraper import RedditScraper
from core.processor.text_processor import TextProcessor
from core.media.image_finder import ImageFinder
from utils.claude_client import ClaudeClient
from utils.logger import setup_logging

def parse_arguments():
    """Parser les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Content Machine - Générateur automatisé de contenu")
    parser.add_argument('--scrape', action='store_true', help="Exécuter uniquement le scraping")
    parser.add_argument('--process', action='store_true', help="Exécuter uniquement le traitement")
    parser.add_argument('--media', action='store_true', help="Exécuter uniquement la recherche de média")
    parser.add_argument('--validate', action='store_true', help="Lancer l'interface de validation")
    parser.add_argument('--all', action='store_true', help="Exécuter tous les processus")
    parser.add_argument('--daemon', action='store_true', help="Exécuter en mode daemon (continu)")
    parser.add_argument('--interval', type=int, default=3600, help="Intervalle en secondes entre les exécutions en mode daemon")
    return parser.parse_args()

def scrape_reddit():
    """Scraper Reddit pour de nouveaux posts."""
    logging.info("Démarrage du scraping Reddit...")
    scraper = RedditScraper()
    posts = scraper.get_posts_from_all_subreddits()
    logging.info(f"Scraping terminé. {len(posts)} posts récupérés.")
    return posts

def process_content(posts=None):
    """Traiter le contenu des posts scrapés."""
    logging.info("Démarrage du traitement du contenu...")
    processor = TextProcessor()
    claude_client = ClaudeClient()
    
    # Si aucun post n'est fourni, récupérer les posts non traités de la base de données
    if posts is None:
        with Session() as session:
            posts_to_process = session.query(RedditPost).filter_by(status='new').all()
            posts = [
                {
                    'reddit_id': post.reddit_id,
                    'title': post.title,
                    'content': post.content,
                    'subreddit': post.subreddit,
                    'upvotes': post.upvotes,
                    'permalink': post.permalink
                }
                for post in posts_to_process
            ]
    
    processed_count = 0
    for post in posts:
        try:
            # Utiliser Claude pour générer des captions optimisées si configuré
            reddit_id = post['reddit_id']
            captions = claude_client.generate_social_media_captions(post, reddit_id)
            
            # Si Claude a généré des captions valides, les utiliser, sinon utiliser le processeur standard
            if captions and captions.get('instagram_caption') and captions.get('tiktok_caption'):
                # Sauvegarder le contenu traité via Claude dans la base de données
                with Session() as session:
                    # Mettre à jour le statut du post Reddit
                    reddit_post = session.query(RedditPost).filter_by(reddit_id=reddit_id).first()
                    if reddit_post:
                        reddit_post.status = 'processed'
                    
                    # Créer une nouvelle entrée pour le contenu traité
                    processed_content = ProcessedContent(
                        reddit_id=reddit_id,
                        keywords=','.join(captions.get('hashtags', [])),
                        hashtags=','.join(captions.get('hashtags', [])),
                        instagram_caption=captions.get('instagram_caption', ''),
                        tiktok_caption=captions.get('tiktok_caption', ''),
                        status='pending_validation'
                    )
                    
                    session.add(processed_content)
                    session.commit()
                    
                processed_count += 1
            else:
                # Fallback au processeur standard
                processor.process_post(post)
                processed_count += 1
            
        except Exception as e:
            logging.error(f"Erreur lors du traitement du post {post['reddit_id']}: {str(e)}")
    
    logging.info(f"Traitement terminé. {processed_count} posts traités.")
    return processed_count

def find_media():
    """Rechercher des médias pour les posts traités."""
    logging.info("Démarrage de la recherche de média...")
    image_finder = ImageFinder()
    
    # Récupérer les contenus traités sans média
    with Session() as session:
        contents = session.query(ProcessedContent).filter_by(has_media=False).all()
        
        # Récupérer les mots-clés associés pour chaque contenu
        for content in contents:
            try:
                # Extraire les mots-clés du contenu
                keywords = content.keywords.split(',') if content.keywords else []
                
                # Si pas de mots-clés, utiliser les hashtags
                if not keywords and content.hashtags:
                    # Supprimer les # des hashtags
                    keywords = [tag.replace('#', '') for tag in content.hashtags.split(',')]
                
                # Si toujours pas de mots-clés, extraire du titre du post
                if not keywords:
                    reddit_post = session.query(RedditPost).filter_by(reddit_id=content.reddit_id).first()
                    if reddit_post:
                        # Utiliser le titre comme source de mots-clés
                        keywords = reddit_post.title.split()[:5]  # Utiliser les 5 premiers mots du titre
                
                # Si des mots-clés sont disponibles, rechercher une image
                if keywords:
                    image_finder.find_image(keywords, content.reddit_id)
                    logging.info(f"Média trouvé pour le post {content.reddit_id}")
                else:
                    logging.warning(f"Pas de mots-clés disponibles pour le post {content.reddit_id}")
                    
            except Exception as e:
                logging.error(f"Erreur lors de la recherche de média pour le post {content.reddit_id}: {str(e)}")
    
    logging.info("Recherche de média terminée.")

def launch_validation_interface():
    """Lancer l'interface de validation Streamlit."""
    try:
        import subprocess
        import sys
        import webbrowser
        import time
        from pathlib import Path
        
        # Get the port from config
        port = config.web_interface_port
        host = "localhost"
        url = f"http://{host}:{port}"
        
        # Path to the run_streamlit.py script
        streamlit_wrapper = Path(__file__).parent / "run_streamlit.py"
        
        # Launch using our wrapper script
        logging.info(f"Launching Streamlit through wrapper script: {streamlit_wrapper}")
        
        # Run in a subprocess
        process = subprocess.Popen([sys.executable, str(streamlit_wrapper)],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  universal_newlines=True)
        
        # Wait a moment for Streamlit to start
        time.sleep(3)
        
        # Open the browser automatically
        webbrowser.open(url)
        
        # Print the URL
        logging.info(f"Interface de validation Streamlit lancée: {url}")
        print(f"\n✅ Interface de validation lancée: {url}")
        print(f"Si votre navigateur ne s'ouvre pas automatiquement, visitez: {url}\n")
        
        # Return the process object so it can be terminated later if needed
        return process
        
    except Exception as e:
        logging.error(f"Erreur lors du lancement de l'interface Streamlit: {str(e)}")
        print(f"\n❌ Erreur lors du lancement de l'interface: {str(e)}")
        return None


def run_pipeline(scrape=True, process=True, media=True, validate=True):
    """Exécuter le pipeline complet."""
    # Initialiser la base de données
    init_db()
    
    # Étape 1: Scraper Reddit
    if scrape:
        posts = scrape_reddit()
    else:
        posts = None
    
    # Étape 2: Traiter le contenu
    if process:
        process_content(posts)
    
    # Étape 3: Rechercher des médias
    if media:
        find_media()
    
    # Étape 4: Lancer l'interface de validation si demandé
    if validate:
        launch_validation_interface()
    
    logging.info("Pipeline exécuté avec succès.")

def run_daemon(interval, scrape=True, process=True, media=True):
    """
    Exécuter le pipeline en mode daemon (continu).
    
    Args:
        interval: Intervalle en secondes entre les exécutions.
        scrape: Si le scraping doit être exécuté.
        process: Si le traitement doit être exécuté.
        media: Si la recherche de média doit être exécutée.
    """
    logging.info(f"Démarrage du mode daemon avec un intervalle de {interval} secondes.")
    
    # Initialiser la base de données au démarrage
    init_db()
    
    try:
        while True:
            # Exécuter le pipeline
            if scrape:
                posts = scrape_reddit()
            else:
                posts = None
            
            if process:
                process_content(posts)
            
            if media:
                find_media()
            
            # Attendre l'intervalle spécifié
            next_run = datetime.now() + timedelta(seconds=interval)
            logging.info(f"Pipeline exécuté avec succès. Prochaine exécution à {next_run.strftime('%H:%M:%S')}")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        logging.info("Arrêt du mode daemon à la demande de l'utilisateur.")
    except Exception as e:
        logging.error(f"Erreur dans le mode daemon: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Configurer le logging
    setup_logging()
    
    # Parser les arguments
    args = parse_arguments()
    
    # Exécuter en fonction des arguments
    if args.daemon:
        # Lancer l'interface de validation dans un thread séparé si demandé
        if args.validate or args.all:
            threading.Thread(target=launch_validation_interface).start()
        
        # Exécuter le daemon avec les composants spécifiés
        run_daemon(
            args.interval,
            scrape=args.scrape or args.all,
            process=args.process or args.all,
            media=args.media or args.all
        )
    else:
        # Exécution unique
        if args.all:
            run_pipeline()
        else:
            run_pipeline(
                scrape=args.scrape,
                process=args.process,
                media=args.media,
                validate=args.validate
            )