# utils/claude_client.py
import logging
import json
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from config.settings import config
from database.models import AIGenerationLog, Session

logger = logging.getLogger(__name__)

class ClaudeClient:
    """Client pour interagir avec l'API Claude d'Anthropic."""
    
    def __init__(self):
        """Initialiser le client Claude avec la clé API."""
        try:
            # Load environment variables from .env file
            from dotenv import load_dotenv
            from pathlib import Path
            
            # Try to find and load .env file from project root
            root_dir = Path(__file__).resolve().parent.parent
            env_path = root_dir / '.env'
            if env_path.exists():
                logger.debug(f"Loading .env from {env_path}")
                load_dotenv(env_path)
            
            # Get the API key directly from environment
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

            # Add better error logging
            if not self.api_key:
                logger.critical("No ANTHROPIC_API_KEY found in environment")
                self.client = None
                return
                            
            # Import here to avoid issues if the package is not installed
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"Claude client initialized with model: {self.model}")
            except (ImportError, Exception) as e:
                logger.error(f"Failed to initialize Anthropic client: {str(e)}")
                self.client = None
                
        except Exception as e:
            logger.critical(f"Critical error initializing Claude client: {str(e)}")
            self.client = None
    
    def generate_social_media_captions(self, post_data: Dict[str, Any], reddit_id: str) -> Dict[str, Any]:
        """
        Générer des captions optimisées pour les réseaux sociaux à partir du contenu Reddit.
        
        Args:
            post_data: Données du post Reddit.
            reddit_id: ID du post Reddit pour le logging.
            
        Returns:
            Dictionnaire contenant les captions générées.
        """
        if not self.api_key or not self.client:
            logger.warning("No API key available for Claude. Using basic caption generation.")
            return self._fallback_caption_generation(post_data)
        
        try:
            # Construire le prompt pour Claude
            prompt = self._build_caption_prompt(post_data)
            
            # Appeler l'API Claude
            response, tokens = self._call_claude_api(prompt)
            
            # Parser la réponse
            captions = self._parse_caption_response(response)
            
            # Logger l'appel API dans la base de données
            self._log_api_call(
                reddit_id=reddit_id,
                task="caption_generation",
                prompt=prompt,
                response=response,
                tokens_used=tokens,
                success=True
            )
            
            return captions
            
        except Exception as e:
            error_msg = f"Error generating captions with Claude: {str(e)}"
            logger.error(error_msg)
            
            # Logger l'erreur
            self._log_api_call(
                reddit_id=reddit_id,
                task="caption_generation",
                prompt=prompt if 'prompt' in locals() else "",
                response="",
                tokens_used=0,
                success=False,
                error_message=str(e)
            )
            
            # Utiliser la génération de secours
            return self._fallback_caption_generation(post_data)
    
    def extract_keywords(self, text: str, reddit_id: str) -> List[str]:
        """
        Extraire les mots-clés importants d'un texte.
        
        Args:
            text: Texte à analyser.
            reddit_id: ID du post Reddit pour le logging.
            
        Returns:
            Liste de mots-clés.
        """
        if not self.api_key or not self.client:
            logger.warning("No API key available for Claude. Using basic keyword extraction.")
            # Utiliser une méthode basique de fallback pour l'extraction des mots-clés
            return self._fallback_keyword_extraction(text)
        
        try:
            # Construire le prompt pour Claude
            prompt = f"""
            Tu es un assistant spécialisé dans l'extraction de mots-clés. 
            Extrait les 10 mots-clés les plus importants du texte suivant. 
            Réponds uniquement avec les mots-clés, un par ligne, sans numérotation ni ponctuation.
            
            Texte: {text}
            """
            
            # Appeler l'API Claude
            response, tokens = self._call_claude_api(prompt)
            
            # Parser la réponse (un mot-clé par ligne)
            keywords = [keyword.strip() for keyword in response.strip().split('\n') if keyword.strip()]
            
            # Logger l'appel API
            self._log_api_call(
                reddit_id=reddit_id,
                task="keyword_extraction",
                prompt=prompt,
                response=response,
                tokens_used=tokens,
                success=True
            )
            
            return keywords[:10]  # Limiter à 10 mots-clés
            
        except Exception as e:
            error_msg = f"Error extracting keywords with Claude: {str(e)}"
            logger.error(error_msg)
            
            # Logger l'erreur
            self._log_api_call(
                reddit_id=reddit_id,
                task="keyword_extraction",
                prompt=prompt if 'prompt' in locals() else "",
                response="",
                tokens_used=0,
                success=False,
                error_message=str(e)
            )
            
            return self._fallback_keyword_extraction(text)
    
    def _fallback_keyword_extraction(self, text: str) -> List[str]:
        """
        Méthode de secours pour extraire des mots-clés sans Claude.
        
        Args:
            text: Texte à analyser.
            
        Returns:
            Liste de mots-clés.
        """
        try:
            import re
            from collections import Counter
            
            # Nettoyer le texte
            text = text.lower()
            # Supprimer la ponctuation et les caractères spéciaux
            text = re.sub(r'[^\w\s]', '', text)
            
            # Tokenizer le texte
            words = text.split()
            
            # Supprimer les mots courants (stop words)
            stop_words = {'the', 'and', 'is', 'in', 'it', 'to', 'a', 'of', 'for', 'with', 'on', 'at', 'by', 'from', 
                          'that', 'this', 'are', 'was', 'were', 'be', 'have', 'has', 'had', 'not', 'but', 'what', 
                          'all', 'when', 'who', 'how', 'why', 'where', 'which', 'or', 'so', 'if'}
            filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
            
            # Compter les occurrences
            word_counts = Counter(filtered_words)
            
            # Retourner les mots les plus fréquents
            return [word for word, _ in word_counts.most_common(10)]
        except Exception as e:
            logger.error(f"Error in fallback keyword extraction: {str(e)}")
            return ["technology", "information", "knowledge", "learning", "science"]  # Default keywords
    
    def _build_caption_prompt(self, post_data: Dict[str, Any]) -> str:
        """
        Construire le prompt pour la génération de captions.
        
        Args:
            post_data: Données du post Reddit.
            
        Returns:
            Prompt formaté.
        """
        title = post_data.get('title', '')
        content = post_data.get('content', '')
        subreddit = post_data.get('subreddit', '')
        
        # Limiter la taille du contenu pour économiser des tokens
        if content and len(content) > 1000:
            content = content[:1000] + "..."
        
        prompt = f'''
        Tu es un expert en marketing des réseaux sociaux spécialisé dans la création de contenu viral.
        
        INFORMATIONS SUR LE POST REDDIT :
        Titre: {title}
        Contenu: {content}
        Subreddit: r/{subreddit}
        
        TÂCHE :
        Crée deux captions optimisées pour les réseaux sociaux basées sur ce contenu Reddit :
        
        1. Une caption Instagram (maximum 2200 caractères) :
           - Commence par un hook accrocheur
           - Inclut des emojis pertinents
           - Reformate le contenu de manière engageante
           - Termine par des hashtags pertinents (maximum 30)
           
        2. Une caption TikTok (maximum 150 caractères) :
           - Version très courte et percutante
           - Inclut des emojis
           - Inclut quelques hashtags essentiels (maximum 5)
        
        FORMAT DE RÉPONSE :
        Réponds uniquement au format JSON structuré comme suit :
        ```json
        {{
          "instagram_caption": "Ta caption Instagram ici",
          "tiktok_caption": "Ta caption TikTok ici",
          "hashtags": ["liste", "de", "hashtags", "pertinents"]
        }}
        ```
        
        Ne réponds pas avec autre chose que ce JSON.
        '''
        
        return prompt
    
    def _call_claude_api(self, prompt: str) -> Tuple[str, int]:
        """
        Appeler l'API Claude avec un prompt.
        
        Args:
            prompt: Prompt à envoyer à Claude.
            
        Returns:
            Tuple contenant la réponse et le nombre de tokens utilisés.
        """
        if not self.client:
            raise RuntimeError("Claude client not initialized. Check your ANTHROPIC_API_KEY in .env")
            
        try:
            # import anthropic
            # Ajout d'un log pour aider au débogage
            logger.debug(f"Calling Claude API with model: {self.model}")
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.7,
                system="Tu es un assistant expert en marketing des réseaux sociaux qui aide à créer du contenu viral.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extraire le contenu de la réponse
            content = response.content[0].text
            
            # Calculer les tokens utilisés
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            return content, tokens_used
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            if hasattr(e, 'status_code'):
                logger.error(f"Status code: {e.status_code}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Response text: {e.response.text}")
            raise
    
    def _parse_caption_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the JSON response from Claude.
        
        Args:
            response: Response string from Claude.
            
        Returns:
            Parsed captions dictionary.
        """
        try:
            # Clean up the response
            response = response.strip()
            
            # Remove code block markers if present
            if response.startswith('```json'):
                response = response.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            try:
                captions = json.loads(response)
            except json.JSONDecodeError:
                # Fallback: try to extract JSON manually
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    captions = json.loads(json_match.group(0))
                else:
                    logger.error(f"Could not parse Claude response: {response}")
                    return self._fallback_caption_generation({})
            
            return {
                'instagram_caption': captions.get('instagram_caption', ''),
                'tiktok_caption': captions.get('tiktok_caption', ''),
                'hashtags': captions.get('hashtags', [])
            }
        except Exception as e:
            logger.error(f"Error parsing Claude caption response: {str(e)}")
            logger.debug(f"Raw response: {response}")
            return self._fallback_caption_generation({})
    
    def _fallback_caption_generation(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Méthode de secours pour générer des captions basiques sans Claude.
        
        Args:
            post_data: Données du post Reddit.
            
        Returns:
            Dictionnaire avec les captions générées.
        """
        title = post_data.get('title', '')
        subreddit = post_data.get('subreddit', '')
        
        # Hashtags génériques
        generic_hashtags = ["#DidYouKnow", "#TodayILearned", "#InterestingFacts", "#Knowledge"]
        
        # Caption Instagram basique
        instagram_caption = f"✨ {title}\n\nSource: Reddit r/{subreddit}\n\n{' '.join(generic_hashtags)}"
        
        # Caption TikTok basique (plus courte)
        tiktok_caption = f"✨ {title[:100]}... {generic_hashtags[0]} {generic_hashtags[1]}"
        
        return {
            'instagram_caption': instagram_caption,
            'tiktok_caption': tiktok_caption,
            'hashtags': generic_hashtags
        }
    
    def _log_api_call(self, reddit_id: str, task: str, prompt: str, response: str, 
                     tokens_used: int, success: bool, error_message: str = None) -> None:
        """
        Enregistrer un appel à l'API Claude dans la base de données.
        
        Args:
            reddit_id: ID du post Reddit.
            task: Type de tâche (caption_generation, keyword_extraction, etc.).
            prompt: Prompt envoyé à Claude.
            response: Réponse de Claude.
            tokens_used: Nombre de tokens utilisés.
            success: Si l'appel a réussi.
            error_message: Message d'erreur éventuel.
        """
        try:
            with Session() as session:
                log_entry = AIGenerationLog(
                    reddit_id=reddit_id,
                    task=task,
                    prompt=prompt,
                    response=response,
                    tokens_used=tokens_used,
                    success=success,
                    error_message=error_message,
                    created_at=datetime.now()
                )
                session.add(log_entry)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to log API call: {str(e)}")