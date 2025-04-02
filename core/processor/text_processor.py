# core/processor/text_processor.py
import re
import logging
import emoji
from typing import Dict, List, Tuple, Any
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from datetime import datetime

from config.settings import config
from utils.error_handler import handle_processing_error
from database.models import RedditPost, ProcessedContent, Session

# Télécharger les ressources NLTK nécessaires (à faire une seule fois au démarrage)
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
except Exception:
    pass  # Gérer silencieusement les erreurs de téléchargement (peut-être déjà téléchargé)

logger = logging.getLogger(__name__)

class TextProcessor:
    """Classe pour traiter et formater le texte pour les plateformes sociales."""
    
    def __init__(self):
        """Initialiser le processeur de texte."""
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        logger.info("Text processor initialized")
    
    def process_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traiter un post Reddit pour le formater pour les plateformes sociales.
        
        Args:
            post_data: Données du post Reddit.
            
        Returns:
            Dictionnaire contenant le contenu formaté pour les différentes plateformes.
        """
        try:
            # Extraire le contenu principal
            title = post_data['title']
            content = post_data['content']
            
            # Nettoyer et préparer le texte
            cleaned_title = self._clean_text(title)
            cleaned_content = self._clean_text(content)
            
            # Extraire les mots-clés pour les hashtags
            keywords = self._extract_keywords(f"{cleaned_title} {cleaned_content}")
            
            # Générer des hashtags à partir des mots-clés
            hashtags = self._generate_hashtags(keywords)
            
            # Formater le contenu pour Instagram
            instagram_caption = self._format_for_instagram(cleaned_title, cleaned_content, hashtags)
            
            # Formater le contenu pour TikTok
            tiktok_caption = self._format_for_tiktok(cleaned_title, cleaned_content, hashtags)
            
            # Préparer les résultats
            processed_data = {
                'original_id': post_data['reddit_id'],
                'original_title': title,
                'original_content': content,
                'keywords': keywords,
                'hashtags': hashtags,
                'instagram_caption': instagram_caption,
                'tiktok_caption': tiktok_caption,
                'post_url': f"https://reddit.com{post_data['permalink']}"
            }
            
            # Enregistrer le contenu traité dans la base de données
            self._save_processed_content(processed_data, post_data['reddit_id'])
            
            logger.info(f"Successfully processed post {post_data['reddit_id']}")
            return processed_data
            
        except Exception as e:
            error_msg = f"Error processing text: {str(e)}"
            logger.error(error_msg)
            handle_processing_error("text_processing", error_msg, post_id=post_data.get('reddit_id', 'unknown'))
            return {
                'original_id': post_data.get('reddit_id', 'unknown'),
                'error': error_msg
            }
    
    def _clean_text(self, text: str) -> str:
        """
        Nettoyer le texte en supprimant les caractères indésirables.
        
        Args:
            text: Texte à nettoyer.
            
        Returns:
            Texte nettoyé.
        """
        if not text:
            return ""
            
        # Supprimer les liens
        text = re.sub(r'http\S+', '', text)
        
        # Supprimer les mentions utilisateur
        text = re.sub(r'@\w+', '', text)
        
        # Supprimer les caractères spéciaux, mais conserver la ponctuation de base
        text = re.sub(r'[^\w\s.,!?]', '', text)
        
        # Supprimer les espaces multiples
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extraire les mots-clés les plus importants du texte.
        
        Args:
            text: Texte à analyser.
            max_keywords: Nombre maximum de mots-clés à extraire.
            
        Returns:
            Liste de mots-clés.
        """
        if not text:
            return []
            
        # Tokenization
        tokens = word_tokenize(text.lower())
        
        # Supprimer les stop words et les tokens courts
        filtered_tokens = [
            self.lemmatizer.lemmatize(token) 
            for token in tokens 
            if token not in self.stop_words and len(token) > 3
        ]
        
        # Compter la fréquence des mots
        word_freq = {}
        for token in filtered_tokens:
            if token in word_freq:
                word_freq[token] += 1
            else:
                word_freq[token] = 1
        
        # Trier par fréquence et prendre les N premiers
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        top_keywords = [word for word, _ in sorted_keywords[:max_keywords]]
        
        return top_keywords
    
    def _generate_hashtags(self, keywords: List[str], max_hashtags: int = None) -> List[str]:
        """
        Générer des hashtags à partir des mots-clés.
        
        Args:
            keywords: Liste de mots-clés.
            max_hashtags: Nombre maximum de hashtags.
            
        Returns:
            Liste de hashtags.
        """
        if not keywords:
            return []
            
        # Ajouter toujours certains hashtags génériques liés à TIL
        generic_hashtags = ["#DidYouKnow", "#TodayILearned", "#InterestingFacts", "#Knowledge"]
        
        # Formater les mots-clés en hashtags
        keyword_hashtags = [f"#{keyword.replace(' ', '')}" for keyword in keywords]
        
        # Combiner les hashtags génériques et spécifiques
        all_hashtags = generic_hashtags + keyword_hashtags
        
        # Limiter le nombre de hashtags si nécessaire
        if max_hashtags and len(all_hashtags) > max_hashtags:
            all_hashtags = all_hashtags[:max_hashtags]
        
        return all_hashtags
    
    def _format_for_instagram(self, title: str, content: str, hashtags: List[str]) -> str:
        """
        Formater le contenu pour Instagram.
        
        Args:
            title: Titre nettoyé.
            content: Contenu nettoyé.
            hashtags: Liste de hashtags.
            
        Returns:
            Texte formaté pour Instagram.
        """
        # Ajouter quelques emojis pertinents
        emojis = emoji.emojize(":sparkles: :bulb: :brain: :nerd_face:")
        
        # Shorten the title (remove "TIL" prefix if present and limit length)
        short_title = title
        if short_title.startswith("TIL "):
            short_title = short_title[4:]
        elif short_title.startswith("TIL that "):
            short_title = short_title[9:]
        
        # Limit title length and ensure it ends with punctuation
        if len(short_title) > 100:
            short_title = short_title[:97] + "..."
        elif not short_title.endswith(('.', '!', '?')):
            short_title = short_title + "."
        
        # Combiner le titre et le contenu
        if content:
            # Extract a brief excerpt from the content (first sentence or two)
            content_excerpt = content.split('.')
            excerpt = content_excerpt[0]
            if len(excerpt) < 100 and len(content_excerpt) > 1:
                excerpt += ". " + content_excerpt[1]
                
            if len(excerpt) > 300:
                excerpt = excerpt[:297] + "..."
                
            main_text = f"{emojis} {short_title}\n\n{excerpt}"
        else:
            main_text = f"{emojis} {short_title}"
        
        # Ajouter la source
        source_text = "\n\nSource: Reddit"
        
        # Ajouter les hashtags
        instagram_hashtags = " ".join(hashtags[:config.instagram.max_hashtags])
        
        # Assembler le tout
        full_caption = f"{main_text}{source_text}\n\n{instagram_hashtags}"
        
        # S'assurer que la longueur est correcte pour Instagram
        if len(full_caption) > config.instagram.max_caption_length:
            # Réduire le texte principal pour tenir dans la limite
            excess = len(full_caption) - config.instagram.max_caption_length
            main_text = main_text[:-excess-3] + "..."
            full_caption = f"{main_text}{source_text}\n\n{instagram_hashtags}"
        
        return full_caption
    
    def _format_for_tiktok(self, title: str, content: str, hashtags: List[str]) -> str:
        """
        Formater le contenu pour TikTok.
        
        Args:
            title: Titre nettoyé.
            content: Contenu nettoyé.
            hashtags: Liste de hashtags.
            
        Returns:
            Texte formaté pour TikTok.
        """
        # Shorten the title (remove "TIL" prefix and keep it very brief)
        short_title = title
        if short_title.startswith("TIL "):
            short_title = short_title[4:]
        elif short_title.startswith("TIL that "):
            short_title = short_title[9:]
            
        # Very aggressive shortening for TikTok
        if len(short_title) > 60:
            # Look for a logical breaking point
            breaking_points = ['. ', '? ', '! ', ': ', ' - ']
            for point in breaking_points:
                pos = short_title.find(point, 30, 60)
                if pos > 0:
                    short_title = short_title[:pos+1]
                    break
            else:
                # No good breaking point found, just truncate
                short_title = short_title[:57] + "..."
        
        # Add an emoji at the beginning
        if not any(c for c in short_title if c in "✨🔍💡🧠"):
            short_title = "💡 " + short_title
            
        # For TikTok, just use the shortened title
        main_text = short_title
        
        # Ajouter les hashtags les plus importants
        tiktok_hashtags = " ".join(hashtags[:min(config.tiktok.max_hashtags, 3)])  # Even fewer hashtags
        
        # Assembler le tout
        full_caption = f"{main_text}\n{tiktok_hashtags}"
        
        # S'assurer que la longueur est correcte pour TikTok
        if len(full_caption) > config.tiktok.max_caption_length:
            # Réduire le texte principal pour tenir dans la limite
            excess = len(full_caption) - config.tiktok.max_caption_length
            main_text = main_text[:-excess-3] + "..."
            full_caption = f"{main_text}\n{tiktok_hashtags}"
        
        return full_caption
    
    def _format_for_tiktok(self, title: str, content: str, hashtags: List[str]) -> str:
        """
        Formater le contenu pour TikTok.
        
        Args:
            title: Titre nettoyé.
            content: Contenu nettoyé.
            hashtags: Liste de hashtags.
            
        Returns:
            Texte formaté pour TikTok.
        """
        # Pour TikTok, on se concentre sur le titre principalement en raison des limites de caractères
        main_text = f"{title}"
        
        # Ajouter les hashtags les plus importants
        tiktok_hashtags = " ".join(hashtags[:min(config.tiktok.max_hashtags, 5)])
        
        # Assembler le tout
        full_caption = f"{main_text}\n{tiktok_hashtags}"
        
        # S'assurer que la longueur est correcte pour TikTok
        if len(full_caption) > config.tiktok.max_caption_length:
            # Réduire le texte principal pour tenir dans la limite
            excess = len(full_caption) - config.tiktok.max_caption_length
            main_text = main_text[:-excess-3] + "..."
            full_caption = f"{main_text}\n{tiktok_hashtags}"
        
        return full_caption
    
    def _save_processed_content(self, processed_data: Dict[str, Any], reddit_id: str) -> None:
        """
        Enregistrer le contenu traité dans la base de données.
        
        Args:
            processed_data: Données traitées.
            reddit_id: ID du post Reddit original.
        """
        try:
            with Session() as session:
                # Vérifier si un contenu traité existe déjà pour ce post
                existing_content = session.query(ProcessedContent).filter_by(reddit_id=reddit_id).first()
                
                if existing_content:
                    # Mettre à jour le contenu existant
                    logger.info(f"Updating existing processed content for post {reddit_id}")
                    existing_content.keywords = ','.join(processed_data['keywords'])
                    existing_content.hashtags = ','.join(processed_data['hashtags'])
                    existing_content.instagram_caption = processed_data['instagram_caption']
                    existing_content.tiktok_caption = processed_data['tiktok_caption']
                    existing_content.updated_at = datetime.now()
                else:
                    # Mettre à jour le statut du post Reddit
                    reddit_post = session.query(RedditPost).filter_by(reddit_id=reddit_id).first()
                    if reddit_post:
                        reddit_post.status = 'processed'
                    
                    # Créer une nouvelle entrée pour le contenu traité
                    processed_content = ProcessedContent(
                        reddit_id=reddit_id,
                        keywords=','.join(processed_data['keywords']),
                        hashtags=','.join(processed_data['hashtags']),
                        instagram_caption=processed_data['instagram_caption'],
                        tiktok_caption=processed_data['tiktok_caption'],
                        status='pending_validation'  # En attente de validation humaine
                    )
                    
                    session.add(processed_content)
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to save processed content to database: {str(e)}")