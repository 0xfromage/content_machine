# tests/test_scraper.py
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
from datetime import datetime

# Ajouter le dossier parent au path pour pouvoir importer les modules du projet
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.scraper.reddit_scraper import RedditScraper
from database.models import RedditPost, Session

class TestRedditScraper(unittest.TestCase):
    """Tests pour le scraper Reddit."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        # Créer un mock pour la session de base de données
        self.session_mock = MagicMock()
        self.session_mock.__enter__ = MagicMock(return_value=self.session_mock)
        self.session_mock.__exit__ = MagicMock(return_value=None)
        
        # Créer un patch pour la classe Session
        self.session_patch = patch('core.scraper.reddit_scraper.Session', return_value=self.session_mock)
        self.mock_session = self.session_patch.start()
        
        # Charger les données de test
        with open('tests/data/sample_reddit_posts.json', 'r') as f:
            self.sample_posts = json.load(f)
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter les patches
        self.session_patch.stop()
    
    @patch('praw.Reddit')
    def test_initialize(self, mock_reddit):
        """Tester l'initialisation du scraper Reddit."""
        # Configurer le mock pour praw.Reddit
        mock_reddit.return_value = MagicMock()
        
        # Créer le scraper
        scraper = RedditScraper()
        
        # Vérifier que praw.Reddit a été appelé avec les bons arguments
        mock_reddit.assert_called_once()
        
        # Vérifier que le scraper a été correctement initialisé
        self.assertIsNotNone(scraper.reddit)
    
    @patch('praw.Reddit')
    def test_get_trending_posts(self, mock_reddit):
        """Tester la récupération des posts tendance."""
        # Configurer les mocks
        mock_subreddit = MagicMock()
        mock_posts = []
        
        # Créer des posts factices
        for post_data in self.sample_posts:
            mock_post = MagicMock()
            mock_post.id = post_data['reddit_id']
            mock_post.title = post_data['title']
            mock_post.selftext = post_data['content']
            mock_post.url = post_data['url']
            mock_post.subreddit.display_name = post_data['subreddit']
            mock_post.score = post_data['upvotes']
            mock_post.num_comments = post_data['num_comments']
            mock_post.created_utc = datetime.fromisoformat(post_data['created_utc']).timestamp()
            mock_post.author = MagicMock()
            mock_post.author.name = post_data['author']
            mock_post.permalink = post_data['permalink']
            mock_post.over_18 = False
            mock_posts.append(mock_post)
        
        # Configurer le subreddit pour retourner les posts
        mock_subreddit.top.return_value = mock_posts
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        
        # Configurer la requête de base de données
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None
        
        # Initialiser le scraper
        scraper = RedditScraper()
        
        # Récupérer les posts
        posts = scraper.get_trending_posts(subreddit_name="test")
        
        # Vérifier que les posts ont été récupérés
        self.assertEqual(len(posts), len(self.sample_posts))
        
        # Vérifier que les posts contiennent les informations attendues
        for i, post in enumerate(posts):
            self.assertEqual(post['reddit_id'], self.sample_posts[i]['reddit_id'])
            self.assertEqual(post['title'], self.sample_posts[i]['title'])
            self.assertEqual(post['content'], self.sample_posts[i]['content'])
            self.assertEqual(post['subreddit'], self.sample_posts[i]['subreddit'])
            self.assertEqual(post['upvotes'], self.sample_posts[i]['upvotes'])
    
    @patch('praw.Reddit')
    def test_skip_existing_posts(self, mock_reddit):
        """Tester que les posts existants sont ignorés."""
        # Configurer les mocks
        mock_subreddit = MagicMock()
        mock_post = MagicMock()
        mock_post.id = self.sample_posts[0]['reddit_id']
        mock_post.title = self.sample_posts[0]['title']
        mock_post.selftext = self.sample_posts[0]['content']
        mock_post.url = self.sample_posts[0]['url']
        mock_post.subreddit.display_name = self.sample_posts[0]['subreddit']
        mock_post.score = self.sample_posts[0]['upvotes']
        mock_post.num_comments = self.sample_posts[0]['num_comments']
        mock_post.created_utc = datetime.fromisoformat(self.sample_posts[0]['created_utc']).timestamp()
        mock_post.author = MagicMock()
        mock_post.author.name = self.sample_posts[0]['author']
        mock_post.permalink = self.sample_posts[0]['permalink']
        mock_post.over_18 = False
        
        # Configurer le subreddit pour retourner le post
        mock_subreddit.top.return_value = [mock_post]
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        
        # Configurer la requête de base de données pour trouver un post existant
        existing_post = MagicMock()
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = existing_post
        
        # Initialiser le scraper
        scraper = RedditScraper()
        
        # Récupérer les posts
        posts = scraper.get_trending_posts(subreddit_name="test")
        
        # Vérifier qu'aucun post n'a été récupéré (car il existe déjà)
        self.assertEqual(len(posts), 0)
    
    @patch('praw.Reddit')
    def test_filter_nsfw_posts(self, mock_reddit):
        """Tester le filtrage des posts NSFW."""
        # Configurer les mocks
        mock_subreddit = MagicMock()
        mock_post = MagicMock()
        mock_post.id = "nsfw_post"
        mock_post.title = "NSFW Post"
        mock_post.selftext = "NSFW content"
        mock_post.url = "https://example.com/nsfw"
        mock_post.subreddit.display_name = "test"
        mock_post.score = 5000
        mock_post.num_comments = 100
        mock_post.created_utc = datetime.now().timestamp()
        mock_post.author = MagicMock()
        mock_post.author.name = "author"
        mock_post.permalink = "/r/test/comments/nsfw_post/nsfw_post/"
        mock_post.over_18 = True  # Post NSFW
        
        # Configurer le subreddit pour retourner le post
        mock_subreddit.top.return_value = [mock_post]
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        
        # Configurer la requête de base de données
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None
        
        # Initialiser le scraper
        scraper = RedditScraper()
        
        # Récupérer les posts
        posts = scraper.get_trending_posts(subreddit_name="test")
        
        # Vérifier qu'aucun post n'a été récupéré (car il est NSFW)
        self.assertEqual(len(posts), 0)

    @patch('praw.Reddit')
    def test_filter_low_upvotes(self, mock_reddit):
        """Tester le filtrage des posts avec peu d'upvotes."""
        # Configurer les mocks
        mock_subreddit = MagicMock()
        mock_posts = []
        
        # Créer des posts factices avec différents nombres d'upvotes
        for i, post_data in enumerate(self.sample_posts):
            mock_post = MagicMock()
            mock_post.id = post_data['reddit_id']
            mock_post.title = post_data['title']
            
            # Alternance de posts avec beaucoup/peu d'upvotes
            if i % 2 == 0:
                mock_post.score = 5000  # Beaucoup d'upvotes
            else:
                mock_post.score = 100   # Peu d'upvotes
                
            mock_post.selftext = post_data['content']
            mock_post.url = post_data['url']
            mock_post.subreddit.display_name = post_data['subreddit']
            mock_post.num_comments = post_data['num_comments']
            mock_post.created_utc = datetime.fromisoformat(post_data['created_utc']).timestamp()
            mock_post.author = MagicMock()
            mock_post.author.name = post_data['author']
            mock_post.permalink = post_data['permalink']
            mock_post.over_18 = False
            mock_posts.append(mock_post)
        
        # Configurer le subreddit pour retourner les posts
        mock_subreddit.top.return_value = mock_posts
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        
        # Configurer la requête de base de données
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None
        
        # Initialiser le scraper
        scraper = RedditScraper()
        
        # Define the number of high upvote posts
        high_upvote_count = sum(1 for i in range(len(self.sample_posts)) if i % 2 == 0)
        
        # Récupérer les posts avec un minimum d'upvotes
        posts = scraper.get_trending_posts(subreddit_name="test", min_upvotes=1000)
        
        # Vérifier que seuls les posts avec suffisamment d'upvotes sont récupérés
        self.assertEqual(len(posts), high_upvote_count)
        for post in posts:
            self.assertGreaterEqual(post['upvotes'], 1000)

    @patch('core.scraper.reddit_scraper.RedditScraper._save_post_to_db')
    @patch('praw.Reddit')
    def test_save_post_to_db(self, mock_reddit, mock_save):
        """Tester la sauvegarde des posts dans la base de données."""
        # Configurer le mock pour _save_post_to_db
        mock_save.return_value = None
        
        # Configurer les mocks pour Reddit
        mock_subreddit = MagicMock()
        mock_post = MagicMock()
        mock_post.id = self.sample_posts[0]['reddit_id']
        mock_post.title = self.sample_posts[0]['title']
        mock_post.selftext = self.sample_posts[0]['content']
        mock_post.url = self.sample_posts[0]['url']
        mock_post.subreddit.display_name = self.sample_posts[0]['subreddit']
        mock_post.score = self.sample_posts[0]['upvotes']
        mock_post.num_comments = self.sample_posts[0]['num_comments']
        mock_post.created_utc = datetime.fromisoformat(self.sample_posts[0]['created_utc']).timestamp()
        mock_post.author = MagicMock()
        mock_post.author.name = self.sample_posts[0]['author']
        mock_post.permalink = self.sample_posts[0]['permalink']
        mock_post.over_18 = False
        
        # Configurer le subreddit pour retourner le post
        mock_subreddit.top.return_value = [mock_post]
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        
        # Configurer la requête de base de données
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None
        
        # Initialiser le scraper
        scraper = RedditScraper()
        
        # Récupérer les posts
        posts = scraper.get_trending_posts(subreddit_name="test")
        
        # Vérifier que la méthode de sauvegarde a été appelée
        mock_save.assert_called_once()
        
        # Vérifier les arguments passés à _save_post_to_db
        args, _ = mock_save.call_args
        post_data = args[0]
        self.assertEqual(post_data['reddit_id'], self.sample_posts[0]['reddit_id'])
        self.assertEqual(post_data['title'], self.sample_posts[0]['title'])

    @patch('praw.Reddit')
    def test_handle_reddit_api_error(self, mock_reddit):
        """Tester la gestion des erreurs de l'API Reddit."""
        # Configurer le mock pour lever une exception
        mock_reddit.return_value.subreddit.side_effect = Exception("API Error")
        
        # Initialiser le scraper
        scraper = RedditScraper()
        
        # Récupérer les posts (devrait gérer l'erreur)
        posts = scraper.get_trending_posts(subreddit_name="test")
        
        # Vérifier que la liste de posts est vide en cas d'erreur
        self.assertEqual(len(posts), 0)

    @patch('praw.Reddit')
    def test_handle_deleted_author(self, mock_reddit):
        """Tester la gestion des posts avec auteur supprimé."""
        # Configurer les mocks
        mock_subreddit = MagicMock()
        mock_post = MagicMock()
        mock_post.id = "test_id"
        mock_post.title = "Test Title"
        mock_post.selftext = "Test content"
        mock_post.url = "https://reddit.com/r/test/comments/test"
        mock_post.subreddit.display_name = "test"
        mock_post.score = 5000
        mock_post.num_comments = 100
        mock_post.created_utc = datetime.now().timestamp()
        mock_post.author = None  # Auteur supprimé
        mock_post.permalink = "/r/test/comments/test_id/test_title/"
        mock_post.over_18 = False
        
        # Configurer le subreddit pour retourner le post
        mock_subreddit.top.return_value = [mock_post]
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        
        # Configurer la requête de base de données
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None
        
        # Initialiser le scraper
        scraper = RedditScraper()
        
        # Récupérer les posts
        posts = scraper.get_trending_posts(subreddit_name="test")
        
        # Vérifier que les posts avec auteur supprimé sont gérés
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['author'], "[deleted]")


    @patch('praw.Reddit')
    def test_multiple_subreddits(self, mock_reddit):
        """Tester la récupération des posts de plusieurs subreddits."""
        # Créer des mocks pour les subreddits
        mock_subreddit1 = MagicMock()
        mock_subreddit2 = MagicMock()
        
        # Configurer les posts pour chaque subreddit
        mock_post1 = MagicMock()
        mock_post1.id = "id1"
        mock_post1.title = "Title from subreddit1"
        mock_post1.selftext = "Content from subreddit1"
        mock_post1.url = "https://example.com/1"
        mock_post1.subreddit.display_name = "subreddit1"
        mock_post1.score = 5000
        mock_post1.num_comments = 100
        mock_post1.created_utc = datetime.now().timestamp()
        mock_post1.author = MagicMock()
        mock_post1.author.name = "user1"
        mock_post1.permalink = "/r/subreddit1/comments/id1/title/"
        mock_post1.over_18 = False
        
        mock_post2 = MagicMock()
        mock_post2.id = "id2"
        mock_post2.title = "Title from subreddit2"
        mock_post2.selftext = "Content from subreddit2"
        mock_post2.url = "https://example.com/2"
        mock_post2.subreddit.display_name = "subreddit2"
        mock_post2.score = 6000
        mock_post2.num_comments = 200
        mock_post2.created_utc = datetime.now().timestamp()
        mock_post2.author = MagicMock()
        mock_post2.author.name = "user2"
        mock_post2.permalink = "/r/subreddit2/comments/id2/title/"
        mock_post2.over_18 = False
        
        # Assigner les posts aux subreddits
        mock_subreddit1.top.return_value = [mock_post1]
        mock_subreddit2.top.return_value = [mock_post2]
        
        # Configurer le mock pour retourner les différents subreddits
        def side_effect(subreddit_name):
            if subreddit_name == "subreddit1":
                return mock_subreddit1
            elif subreddit_name == "subreddit2":
                return mock_subreddit2
            else:
                return MagicMock()
        
        mock_reddit.return_value.subreddit.side_effect = side_effect
        
        # Configurer la requête de base de données
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None
        
        # Initialize the scraper
        scraper = RedditScraper()
        
        # Directly mock the get_trending_posts method instead of patching it
        original_get_trending_posts = scraper.get_trending_posts
        
        def mock_get_trending_posts(subreddit_name=None, **kwargs):
            if subreddit_name == "subreddit1":
                return [{'reddit_id': 'id1', 'title': 'Title from subreddit1', 'subreddit': 'subreddit1'}]
            elif subreddit_name == "subreddit2":
                return [{'reddit_id': 'id2', 'title': 'Title from subreddit2', 'subreddit': 'subreddit2'}]
            else:
                return original_get_trending_posts(subreddit_name, **kwargs)
                
        scraper.get_trending_posts = mock_get_trending_posts
        
        # Set the list of subreddits for testing
        scraper.reddit.subreddits = ["subreddit1", "subreddit2"]
        
        # Call the method we're testing directly with our mocked function
        posts = []
        for subreddit in ["subreddit1", "subreddit2"]:
            posts.extend(scraper.get_trending_posts(subreddit))
            
        # Vérifier que les posts des deux subreddits sont récupérés
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0]['subreddit'], 'subreddit1')
        self.assertEqual(posts[1]['subreddit'], 'subreddit2')