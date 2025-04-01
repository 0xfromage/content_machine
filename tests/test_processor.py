# tests/test_processor.py
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
from datetime import datetime

# Ajouter le dossier parent au path pour pouvoir importer les modules du projet
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.processor.text_processor import TextProcessor
from core.processor.hashtag_generator import HashtagGenerator
from database.models import RedditPost, ProcessedContent, Session
from utils.claude_client import ClaudeClient

class TestTextProcessor(unittest.TestCase):
    """Tests pour le processeur de texte."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        # Créer un mock pour la session de base de données
        self.session_mock = MagicMock()
        self.session_mock.__enter__ = MagicMock(return_value=self.session_mock)
        self.session_mock.__exit__ = MagicMock(return_value=None)
        
        # Créer un patch pour la classe Session
        self.session_patch = patch('core.processor.text_processor.Session', return_value=self.session_mock)
        self.mock_session = self.session_patch.start()
        
        # Charger les données de test
        with open('tests/data/sample_reddit_posts.json', 'r') as f:
            self.sample_posts = json.load(f)
        
        # Créer une instance du processeur
        self.processor = TextProcessor()
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter les patches
        self.session_patch.stop()
    
    def test_clean_text(self):
        """Tester le nettoyage du texte."""
        # Texte avec des URLs, mentions et caractères spéciaux
        dirty_text = "Check out this link: http://example.com and mention @username #hashtag"
        
        # Nettoyer le texte
        clean_text = self.processor._clean_text(dirty_text)
        
        # Vérifier que les URLs et mentions ont été supprimées
        self.assertNotIn("http://", clean_text)
        self.assertNotIn("@username", clean_text)
        
        # Vérifier que le hashtag a été supprimé (le caractère #)
        self.assertNotIn("#", clean_text)
        
        # Vérifier que le reste du texte est toujours présent
        self.assertIn("Check out this link", clean_text)
        self.assertIn("and mention", clean_text)
        self.assertIn("hashtag", clean_text)
    
    def test_extract_keywords(self):
        """Tester l'extraction des mots-clés."""
        # Texte avec des mots-clés potentiels
        text = "Artificial intelligence and machine learning are transforming technology and science. AI applications are everywhere."
        
        # Extraire les mots-clés
        keywords = self.processor._extract_keywords(text)
        
        # Vérifier que les mots-clés importants ont été extraits
        self.assertIn("artificial", keywords)
        self.assertIn("intelligence", keywords)
        self.assertIn("machine", keywords)
        self.assertIn("learning", keywords)
        self.assertIn("technology", keywords)
        self.assertIn("science", keywords)
        
        # Vérifier que les stop words ont été filtrés
        self.assertNotIn("and", keywords)
        self.assertNotIn("are", keywords)
    
    def test_generate_hashtags(self):
        """Tester la génération de hashtags."""
        # Liste de mots-clés
        keywords = ["artificial", "intelligence", "machine", "learning", "technology"]
        
        # Générer des hashtags avec une limite
        hashtags = self.processor._generate_hashtags(keywords, max_hashtags=5)
        
        # Vérifier que tous les hashtags commencent par #
        for hashtag in hashtags:
            self.assertTrue(hashtag.startswith("#"))
        
        # Vérifier la limite
        self.assertLessEqual(len(hashtags), 5)
        
        # Vérifier que certains hashtags génériques sont inclus
        generic_found = False
        for hashtag in hashtags:
            if hashtag in ["#DidYouKnow", "#TodayILearned", "#InterestingFacts"]:
                generic_found = True
                break
        
        self.assertTrue(generic_found, "Aucun hashtag générique trouvé")
    
    def test_format_for_instagram(self):
        """Tester le formatage pour Instagram."""
        # Données de test
        title = "Interesting AI Development"
        content = "Researchers have developed a new AI model that can understand complex language patterns."
        hashtags = ["#AI", "#Technology", "#Research", "#MachineLearning"]
        
        # Formater pour Instagram
        instagram_caption = self.processor._format_for_instagram(title, content, hashtags)
        
        # Vérifier que le titre est inclus
        self.assertIn(title, instagram_caption)
        
        # Vérifier que le contenu est inclus
        self.assertIn(content, instagram_caption)
        
        # Vérifier que tous les hashtags sont inclus
        for hashtag in hashtags:
            self.assertIn(hashtag, instagram_caption)
        
        # Vérifier qu'il y a au moins un emoji
        self.assertTrue(any(c for c in instagram_caption if c in "✨🔍💡🧠"))
        
        # Vérifier que la mention de source est incluse
        self.assertIn("Source: Reddit", instagram_caption)
    
    def test_format_for_tiktok(self):
        """Tester le formatage pour TikTok."""
        # Données de test
        title = "Interesting AI Development"
        content = "Researchers have developed a new AI model that can understand complex language patterns."
        hashtags = ["#AI", "#Technology", "#Research", "#MachineLearning"]
        
        # Formater pour TikTok
        tiktok_caption = self.processor._format_for_tiktok(title, content, hashtags)
        
        # Vérifier que le titre est inclus
        self.assertIn(title, tiktok_caption)
        
        # Vérifier la longueur (TikTok a une limite stricte)
        self.assertLessEqual(len(tiktok_caption), 150)
        
        # Vérifier qu'au moins quelques hashtags sont inclus
        hashtags_found = sum(1 for tag in hashtags if tag in tiktok_caption)
        self.assertGreater(hashtags_found, 0)
    
    @patch('core.processor.text_processor._save_processed_content')
    def test_process_post(self, mock_save):
        """Tester le traitement complet d'un post."""
        # Configurer le mock pour sauvegarder le contenu
        mock_save.return_value = None
        
        # Données de test (premier post de l'échantillon)
        post_data = self.sample_posts[0]
        
        # Traiter le post
        result = self.processor.process_post(post_data)
        
        # Vérifier que le résultat contient les champs attendus
        self.assertIn('original_id', result)
        self.assertIn('original_title', result)
        self.assertIn('keywords', result)
        self.assertIn('hashtags', result)
        self.assertIn('instagram_caption', result)
        self.assertIn('tiktok_caption', result)
        
        # Vérifier que les IDs correspondent
        self.assertEqual(result['original_id'], post_data['reddit_id'])
        
        # Vérifier que les hashtags ont été générés
        self.assertGreater(len(result['hashtags']), 0)
        
        # Vérifier que les captions ont été formatées
        self.assertGreater(len(result['instagram_caption']), 0)
        self.assertGreater(len(result['tiktok_caption']), 0)

class TestHashtagGenerator(unittest.TestCase):
    """Tests pour le générateur de hashtags."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        # Créer une instance du générateur de hashtags
        self.generator = HashtagGenerator()
    
    def test_generate_hashtags_from_keywords(self):
        """Tester la génération de hashtags à partir de mots-clés."""
        # Liste de mots-clés
        keywords = ["artificial", "intelligence", "machine", "learning"]
        
        # Texte pour contexte
        text = "Artificial intelligence and machine learning are transforming various industries."
        
        # Générer des hashtags
        hashtags = self.generator._generate_hashtags_from_keywords(keywords, text, 10)
        
        # Vérifier que les hashtags ont été générés
        self.assertGreater(len(hashtags), 0)
        
        # Vérifier que tous les hashtags commencent par #
        for hashtag in hashtags:
            self.assertTrue(hashtag.startswith("#"))
        
        # Vérifier la limite
        self.assertLessEqual(len(hashtags), 10)
    
    def test_clean_keyword(self):
        """Tester le nettoyage des mots-clés."""
        # Mot-clé avec des caractères spéciaux et espaces
        keyword = "artificial intelligence & ML"
        
        # Nettoyer le mot-clé
        clean = self.generator._clean_keyword(keyword)
        
        # Vérifier le résultat
        self.assertEqual(clean, "artificialIntelligenceMl")
        
        # Tester avec un mot-clé vide
        self.assertEqual(self.generator._clean_keyword(""), "")
        
        # Tester avec des caractères spéciaux uniquement
        self.assertEqual(self.generator._clean_keyword("!@#$%^"), "")
    
    def test_get_generic_hashtags(self):
        """Tester l'obtention de hashtags génériques."""
        # Obtenir des hashtags génériques
        hashtags = self.generator._get_generic_hashtags(5)
        
        # Vérifier le nombre
        self.assertEqual(len(hashtags), 5)
        
        # Vérifier que tous commencent par #
        for hashtag in hashtags:
            self.assertTrue(hashtag.startswith("#"))
    
    def test_get_emojis(self):
        """Tester l'obtention d'emojis."""
        # Obtenir des emojis pour une catégorie
        emojis = self.generator.get_emojis(category="TECH", count=2)
        
        # Vérifier le nombre
        self.assertEqual(len(emojis.split()), 2)
        
        # Vérifier que ce sont bien des emojis
        for emoji in emojis.split():
            self.assertTrue(any(c for c in emoji if ord(c) > 127))
        
        # Tester avec une catégorie non existante
        random_emojis = self.generator.get_emojis(category="NONEXISTENT", count=3)
        self.assertEqual(len(random_emojis.split()), 3)

if __name__ == '__main__':
    unittest.main()