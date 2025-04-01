# core/processor/hashtag_generator.py
import logging
import re
import random
from typing import List, Set, Dict, Any, Optional
import emoji
from nltk.stem import WordNetLemmatizer

from config.settings import config
from config.constants import GENERIC_HASHTAGS, CATEGORY_EMOJIS
from utils.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

class HashtagGenerator:
    """Classe pour générer des hashtags pertinents pour les réseaux sociaux."""
    
    def __init__(self):
        """Initialiser le générateur de hashtags."""
        self.lemmatizer = WordNetLemmatizer()
        self.claude_client = ClaudeClient()
        logger.info("Hashtag generator initialized")
    
    def generate_hashtags(self, keywords: List[str], text: str, reddit_id: str, platform: str = 'instagram') -> List[str]:
        """
        Générer des hashtags pertinents pour un contenu donné.
        
        Args:
            keywords: Liste de mots-clés extraits du contenu.
            text: Texte complet du contenu.
            reddit_id: ID du post Reddit (pour le logging).
            platform: Plateforme cible (instagram ou tiktok).
            
        Returns:
            Liste de hashtags générés.
        """
        # Déterminer le nombre maximum de hashtags en fonction de la plateforme
        if platform.lower() == 'instagram':
            max_hashtags = config.instagram.max_hashtags
        elif platform.lower() == 'tiktok':
            max_hashtags = config.tiktok.max_hashtags
        else:
            max_hashtags = 10  # Valeur par défaut
        
        try:
            # Utiliser Claude si disponible
            if hasattr(self.claude_client, 'api_key') and self.claude_client.api_key:
                ai_hashtags = self._generate_hashtags_with_claude(text, reddit_id, max_hashtags)
                if ai_hashtags and len(ai_hashtags) > 0:
                    return ai_hashtags
            
            # Méthode de fallback si Claude n'est pas disponible ou a échoué
            return self._generate_hashtags_from_keywords(keywords, text, max_hashtags)
            
        except Exception as e:
            logger.error(f"Error generating hashtags: {str(e)}")
            # Méthode de secours en cas d'erreur
            return self._get_generic_hashtags(max_hashtags)
    
    def _generate_hashtags_with_claude(self, text: str, reddit_id: str, max_hashtags: int) -> List[str]:
        """
        Utiliser Claude pour générer des hashtags pertinents.
        
        Args:
            text: Texte pour lequel générer des hashtags.
            reddit_id: ID du post Reddit.
            max_hashtags: Nombre maximum de hashtags à générer.
            
        Returns:
            Liste de hashtags générés par Claude.
        """
        # Claude pourrait ne pas être initialisé correctement
        if not hasattr(self.claude_client, 'extract_keywords'):
            return []
            
        try:
            # Extraire des mots-clés avec Claude
            keywords = self.claude_client.extract_keywords(text, reddit_id)
            
            # Transformer les mots-clés en hashtags
            hashtags = []
            for keyword in keywords:
                # Nettoyer et formater le mot-clé
                clean_keyword = self._clean_keyword(keyword)
                if clean_keyword:
                    hashtags.append(f"#{clean_keyword}")
            
            # Ajouter quelques hashtags génériques
            generic_hashtags = self._get_generic_hashtags(5)
            all_hashtags = hashtags + generic_hashtags
            
            # Supprimer les doublons et limiter le nombre
            unique_hashtags = list(dict.fromkeys(all_hashtags))
            return unique_hashtags[:max_hashtags]
            
        except Exception as e:
            logger.error(f"Claude hashtag generation failed: {str(e)}")
            return []
    
    def _generate_hashtags_from_keywords(self, keywords: List[str], text: str, max_hashtags: int) -> List[str]:
        """
        Générer des hashtags à partir des mots-clés extraits.
        
        Args:
            keywords: Liste de mots-clés.
            text: Texte complet pour contexte.
            max_hashtags: Nombre maximum de hashtags.
            
        Returns:
            Liste de hashtags.
        """
        # Collecter tous les hashtags potentiels
        hashtags = []
        
        # 1. Ajouter des hashtags à partir des mots-clés
        for keyword in keywords:
            clean_keyword = self._clean_keyword(keyword)
            if clean_keyword:
                hashtags.append(f"#{clean_keyword}")
        
        # 2. Rechercher des hashtags composés de plusieurs mots
        compound_keywords = self._find_compound_keywords(keywords, text)
        for compound in compound_keywords:
            clean_compound = self._clean_keyword(compound)
            if clean_compound:
                hashtags.append(f"#{clean_compound}")
        
        # 3. Ajouter des hashtags génériques
        generic_count = min(max_hashtags // 3, 5)  # Au moins quelques hashtags génériques
        generic_hashtags = self._get_generic_hashtags(generic_count)
        
        # Combiner tous les hashtags
        all_hashtags = hashtags + generic_hashtags
        
        # Supprimer les doublons
        unique_hashtags = list(dict.fromkeys(all_hashtags))
        
        # Limiter le nombre de hashtags
        return unique_hashtags[:max_hashtags]
    
    def _clean_keyword(self, keyword: str) -> str:
        """
        Nettoyer et formater un mot-clé pour le transformer en hashtag.
        
        Args:
            keyword: Mot-clé à nettoyer.
            
        Returns:
            Mot-clé nettoyé et formaté.
        """
        # Supprimer les caractères spéciaux et la ponctuation
        clean = re.sub(r'[^\w\s]', '', keyword)
        
        # Supprimer les espaces et mettre en camelCase
        words = clean.split()
        if not words:
            return ""
            
        # Capitaliser la première lettre de chaque mot sauf le premier
        camel_case = words[0].lower()
        for word in words[1:]:
            if word:
                camel_case += word[0].upper() + word[1:].lower()
        
        return camel_case
    
    def _find_compound_keywords(self, keywords: List[str], text: str) -> List[str]:
        """
        Trouver des expressions composées qui pourraient faire de bons hashtags.
        
        Args:
            keywords: Liste de mots-clés individuels.
            text: Texte complet pour chercher des expressions.
            
        Returns:
            Liste d'expressions composées.
        """
        compounds = []
        
        # Rechercher des motifs communs dans le texte
        # Par exemple, "artificial intelligence", "machine learning", etc.
        common_patterns = [
            r'(\w+\s+\w+)\s+technology',
            r'(\w+\s+\w+)\s+science',
            r'(\w+\s+\w+)\s+theory',
            r'(\w+\s+\w+)\s+method',
            r'(\w+\s+\w+)\s+technique'
        ]
        
        for pattern in common_patterns:
            matches = re.findall(pattern, text.lower())
            compounds.extend(matches)
        
        # Rechercher des collocations de mots-clés dans le texte
        for i, kw1 in enumerate(keywords):
            for kw2 in keywords[i+1:]:
                # Rechercher les deux mots-clés adjacents dans le texte
                pattern = fr'\b{re.escape(kw1)}\s+{re.escape(kw2)}\b'
                matches = re.findall(pattern, text.lower())
                if matches:
                    compounds.append(f"{kw1} {kw2}")
                
                # Ordre inversé
                pattern = fr'\b{re.escape(kw2)}\s+{re.escape(kw1)}\b'
                matches = re.findall(pattern, text.lower())
                if matches:
                    compounds.append(f"{kw2} {kw1}")
        
        # Limiter le nombre d'expressions composées
        return list(set(compounds))[:5]
    
    def _get_generic_hashtags(self, count: int) -> List[str]:
        """
        Obtenir des hashtags génériques pour compléter les hashtags spécifiques.
        
        Args:
            count: Nombre de hashtags génériques à obtenir.
            
        Returns:
            Liste de hashtags génériques.
        """
        # Déterminer les catégories à utiliser (TIL, Science, etc.)
        categories = list(GENERIC_HASHTAGS.keys())
        selected_categories = random.sample(categories, min(3, len(categories)))
        
        # Collecter les hashtags des catégories sélectionnées
        all_generic = []
        for category in selected_categories:
            all_generic.extend(GENERIC_HASHTAGS[category])
        
        # Toujours inclure les hashtags TIL
        all_generic.extend(GENERIC_HASHTAGS['LEARNING'])
        
        # Mélanger et sélectionner le nombre demandé
        random.shuffle(all_generic)
        return list(dict.fromkeys(all_generic))[:count]
    
    def get_emojis(self, category: str = None, count: int = 3) -> str:
        """
        Obtenir des emojis pertinents pour une catégorie donnée.
        
        Args:
            category: Catégorie pour laquelle obtenir des emojis.
            count: Nombre d'emojis à obtenir.
            
        Returns:
            Chaîne d'emojis.
        """
        if category and category.upper() in CATEGORY_EMOJIS:
            emojis = CATEGORY_EMOJIS[category.upper()]
        else:
            # Mélanger des emojis de différentes catégories
            categories = list(CATEGORY_EMOJIS.keys())
            selected_categories = random.sample(categories, min(3, len(categories)))
            
            emojis = []
            for category in selected_categories:
                emojis.extend(CATEGORY_EMOJIS[category])
        
        # Sélectionner et joindre les emojis
        selected_emojis = random.sample(emojis, min(count, len(emojis)))
        return ' '.join(selected_emojis)