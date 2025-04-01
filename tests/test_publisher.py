# tests/test_publisher.py
import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import json
from datetime import datetime
import tempfile
import shutil

# Ajouter le dossier parent au path pour pouvoir importer les modules du projet
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.publisher.instagram_publisher import InstagramPublisher
from core.publisher.tiktok_publisher import TikTokPublisher
from core.publisher.base_publisher import BasePublisher
from database.models import ProcessedContent, PublishLog, Session

class MockPublisher(BasePublisher):
    """Publisher fictif pour tester la classe abstraite."""
    
    def __init__(self):
        """Initialiser le publisher de test."""
        super().__init__("mock")
    
    def login(self):
        """Méthode de login factice."""
        return True
    
    def publish_media(self, media_path, caption, **kwargs):
        """Méthode de publication factice."""
        if media_path == "error.jpg":
            return {"success": False, "error": "Test error"}
        return {"success": True, "post_id": "test_post_id", "post_url": "https://example.com/post"}

class TestBasePublisher(unittest.TestCase):
    """Tests pour la classe de base des publishers."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        # Créer un mock pour la session de base de données
        self.session_mock = MagicMock()
        self.session_mock.__enter__ = MagicMock(return_value=self.session_mock)
        self.session_mock.__exit__ = MagicMock(return_value=None)
        
        # Créer un patch pour la classe Session
        self.session_patch = patch('core.publisher.base_publisher.Session', return_value=self.session_mock)
        self.mock_session = self.session_patch.start()
        
        # Créer un publisher factice
        self.publisher = MockPublisher()
        
        # Créer un dossier temporaire pour les fichiers de test
        self.test_dir = tempfile.mkdtemp()
        self.test_image = os.path.join(self.test_dir, "test_image.jpg")
        with open(self.test_image, "wb") as f:
            f.write(b"test image content")
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter les patches
        self.session_patch.stop()
        
        # Supprimer le dossier temporaire
        shutil.rmtree(self.test_dir)
    
    @patch('os.path.exists')
    def test_publish_success(self, mock_exists):
        """Tester la publication réussie."""
        # Configurer les mocks
        mock_exists.return_value = True
        
        # Publication
        result = self.publisher.publish(self.test_image, "Test caption", "test_post_id")
        
        # Vérifier le résultat
        self.assertTrue(result["success"])
        self.assertEqual(result["post_id"], "test_post_id")
        
        # Vérifier que le log a été créé
        self.session_mock.add.assert_called()
        self.session_mock.commit.assert_called()
    
    @patch('os.path.exists')
    def test_publish_missing_file(self, mock_exists):
        """Tester la publication avec un fichier manquant."""
        # Configurer les mocks
        mock_exists.return_value = False
        
        # Publication
        result = self.publisher.publish(self.test_image, "Test caption", "test_post_id")
        
        # Vérifier le résultat
        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])
    
    @patch('os.path.exists')
    def test_publish_error(self, mock_exists):
        """Tester la publication avec une erreur."""
        # Configurer les mocks
        mock_exists.return_value = True
        
        # Publication avec fichier qui déclenche une erreur
        result = self.publisher.publish("error.jpg", "Test caption", "test_post_id")
        
        # Vérifier le résultat
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Test error")

class TestInstagramPublisher(unittest.TestCase):
    """Tests pour le publisher Instagram."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        # Créer un mock pour la session de base de données
        self.session_mock = MagicMock()
        self.session_mock.__enter__ = MagicMock(return_value=self.session_mock)
        self.session_mock.__exit__ = MagicMock(return_value=None)
        
        # Créer un patch pour la classe Session
        self.session_patch = patch('core.publisher.instagram_publisher.Session', return_value=self.session_mock)
        self.mock_session = self.session_patch.start()
        
        # Créer un patch pour le client Instagrapi
        self.client_patch = patch('core.publisher.instagram_publisher.Client')
        self.mock_client = self.client_patch.start()
        
        # Créer une instance du client mock
        self.mock_client_instance = MagicMock()
        self.mock_client.return_value = self.mock_client_instance
        
        # Créer un publisher Instagram
        self.publisher = InstagramPublisher()
        
        # Créer un dossier temporaire pour les fichiers de test
        self.test_dir = tempfile.mkdtemp()
        self.test_image = os.path.join(self.test_dir, "test_image.jpg")
        with open(self.test_image, "wb") as f:
            f.write(b"test image content")
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter les patches
        self.session_patch.stop()
        self.client_patch.stop()
        
        # Supprimer le dossier temporaire
        shutil.rmtree(self.test_dir)
    
    @patch('os.path.exists')
    def test_login_success(self, mock_exists):
        """Tester la connexion réussie à Instagram."""
        # Configurer les mocks
        mock_exists.return_value = False  # Pas de fichier de session existant
        
        # Simuler une connexion réussie
        self.mock_client_instance.login.return_value = True
        
        # Connexion
        result = self.publisher._login()
        
        # Vérifier le résultat
        self.assertTrue(result)
        self.assertTrue(self.publisher.is_logged_in)
        
        # Vérifier que la méthode login a été appelée
        self.mock_client_instance.login.assert_called_with(
            self.publisher.username, self.publisher.password
        )
        
        # Vérifier que la session a été sauvegardée
        self.mock_client_instance.dump_settings.assert_called_once()
    
    @patch('os.path.exists')
    def test_publish_photo(self, mock_exists):
        """Tester la publication d'une photo sur Instagram."""
        # Configurer les mocks
        mock_exists.return_value = True
        
        # Configurer le statut de connexion
        self.publisher.is_logged_in = True
        
        # Simuler une publication réussie
        mock_media = MagicMock()
        mock_media.id = "media_123"
        mock_media.code = "abc123"
        self.mock_client_instance.photo_upload.return_value = mock_media
        
        # Publication
        result = self.publisher.publish(self.test_image, "Test caption", "test_post_id")
        
        # Vérifier le résultat
        self.assertTrue(result["success"])
        self.assertEqual(result["post_id"], "media_123")
        self.assertEqual(result["post_url"], "https://www.instagram.com/p/abc123/")
        
        # Vérifier que la méthode de publication a été appelée
        self.mock_client_instance.photo_upload.assert_called_once_with(
            path=self.test_image, caption="Test caption"
        )

class TestTikTokPublisher(unittest.TestCase):
    """Tests pour le publisher TikTok."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        # Créer un mock pour la session de base de données
        self.session_mock = MagicMock()
        self.session_mock.__enter__ = MagicMock(return_value=self.session_mock)
        self.session_mock.__exit__ = MagicMock(return_value=None)
        
        # Créer un patch pour la classe Session
        self.session_patch = patch('core.publisher.tiktok_publisher.Session', return_value=self.session_mock)
        self.mock_session = self.session_patch.start()
        
        # Créer un publisher TikTok
        self.publisher = TikTokPublisher()
        
        # Créer un dossier temporaire pour les fichiers de test
        self.test_dir = tempfile.mkdtemp()
        self.test_image = os.path.join(self.test_dir, "test_image.jpg")
        with open(self.test_image, "wb") as f:
            f.write(b"test image content")
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter les patches
        self.session_patch.stop()
        
        # Supprimer le dossier temporaire
        shutil.rmtree(self.test_dir)
    
    @patch('core.publisher.tiktok_publisher.TikTokPublisher._create_video_from_image')
    @patch('core.publisher.tiktok_publisher.TikTokPublisher._simulate_tiktok_upload')
    @patch('os.path.exists')
    def test_publish_video(self, mock_exists, mock_upload, mock_create_video):
        """Tester la publication d'une vidéo sur TikTok."""
        # Configurer les mocks
        mock_exists.return_value = True
        mock_create_video.return_value = "test_video.mp4"
        mock_upload.return_value = (True, "tiktok_123")
        
        # Publication
        result = self.publisher.publish(self.test_image, "Test caption", "test_post_id")
        
        # Vérifier le résultat
        self.assertTrue(result["success"])
        self.assertEqual(result["post_id"], "tiktok_123")
        
        # Vérifier que les méthodes ont été appelées
        mock_create_video.assert_called_once_with(self.test_image, "Test caption", "test_post_id")
        mock_upload.assert_called_once_with("test_video.mp4", "Test caption")
    
    @patch('moviepy.editor.ImageClip')
    @patch('moviepy.editor.TextClip')
    @patch('moviepy.editor.CompositeVideoClip')
    def test_create_video_from_image(self, mock_composite, mock_text, mock_image):
        """Tester la création d'une vidéo à partir d'une image."""
        # Configurer les mocks
        mock_image_clip = MagicMock()
        mock_image_clip.w = 1080
        mock_image_clip.h = 1920
        mock_image.return_value = mock_image_clip
        
        mock_text_clip = MagicMock()
        mock_text.return_value = mock_text_clip
        
        mock_video = MagicMock()
        mock_composite.return_value = mock_video
        
        # Créer une vidéo
        with patch('builtins.open', mock_open()):
            path = self.publisher._create_video_from_image(self.test_image, "Test caption", "test_post_id")
        
        # Vérifier le chemin de la vidéo
        self.assertIn("tiktok_test_post_id", path)
        self.assertTrue(path.endswith(".mp4"))
        
        # Vérifier que les méthodes ont été appelées
        mock_image.assert_called_once()
        mock_text.assert_called_once()
        mock_composite.assert_called_once()
        mock_video.write_videofile.assert_called_once()
    
    def test_simulate_tiktok_upload(self):
        """Tester la simulation d'upload sur TikTok."""
        # Configurer un mock pour random
        with patch('random.random') as mock_random:
            # Simuler un succès
            mock_random.return_value = 0.5  # Moins que 0.9, donc succès
            success, post_id = self.publisher._simulate_tiktok_upload("test_video.mp4", "Test caption")
            self.assertTrue(success)
            self.assertTrue(post_id.isdigit())
            
            # Simuler un échec
            mock_random.return_value = 0.95  # Plus que 0.9, donc échec
            success, error = self.publisher._simulate_tiktok_upload("test_video.mp4", "Test caption")
            self.assertFalse(success)
            self.assertIsInstance(error, str)

if __name__ == '__main__':
    unittest.main()