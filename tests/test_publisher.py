import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import json
from datetime import datetime
import tempfile
import shutil

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.publisher.instagram_publisher import InstagramPublisher
from core.publisher.tiktok_publisher import TikTokPublisher
from core.publisher.base_publisher import BasePublisher
from database.models import ProcessedContent, PublishLog, Session
from tests.mocks import MockInstagramClient

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
        
        # Patch de la classe Client avec notre implémentation MockInstagramClient
        self.client_patch = patch('instagrapi.Client', MockInstagramClient)
        self.mock_client_class = self.client_patch.start()
        
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
        
        # Reset publisher state
        self.publisher = InstagramPublisher()
        
        # Force clear is_logged_in status
        self.publisher.is_logged_in = False
        
        # Connexion (call _login directly to avoid the call in __init__)
        result = self.publisher._login()
        
        # Vérifier le résultat
        self.assertTrue(result)
        self.assertTrue(self.publisher.is_logged_in)
        
        # Verify that login was called on the client
        self.publisher.client.login.assert_called_once()
    
    @patch('os.path.exists')
    def test_publish_photo(self, mock_exists):
        """Tester la publication d'une photo sur Instagram."""
        # Configurer les mocks
        mock_exists.return_value = True
        
        # Configurer le statut de connexion
        self.publisher.is_logged_in = True
        
        # Publication
        result = self.publisher.publish(self.test_image, "Test caption", "test_post_id")
        
        # Vérifier le résultat
        self.assertTrue(result["success"])
        self.assertEqual(result["post_id"], "test_media_123")
        self.assertEqual(result["post_url"], "https://www.instagram.com/p/test_abc123/")
        
        # Vérifier que la méthode de publication a été appelée
        self.publisher.client.photo_upload.assert_called_once_with(
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
    
    @patch('os.path.join')
    @patch('time.time')
    def test_create_video_from_image(self, mock_time, mock_join):
        """Tester la création d'une vidéo à partir d'une image."""
        # Mock image clip and related objects
        with patch('moviepy.editor.ImageClip') as mock_image_clip, \
             patch('moviepy.editor.TextClip') as mock_text_clip, \
             patch('moviepy.editor.CompositeVideoClip') as mock_composite:
                
            # Configure mocks
            mock_image = MagicMock()
            mock_image.w = 1080
            mock_image.h = 1920
            mock_image.resize.return_value = mock_image
            mock_image.set_duration.return_value = mock_image
            mock_image_clip.return_value = mock_image
            
            mock_text = MagicMock()
            mock_text.set_position.return_value = mock_text
            mock_text.set_duration.return_value = mock_text
            mock_text_clip.return_value = mock_text
            
            mock_video = MagicMock()
            mock_composite.return_value = mock_video
            
            # Set up file mock
            with patch('builtins.open', mock_open()):
                # Fix the timestamp for predictable output
                mock_time.return_value = 12345
                
                # Set up join to return a predictable path
                mock_join.return_value = f"media/videos/tiktok_test_post_id_12345.mp4"
                
                # Call the method
                path = self.publisher._create_video_from_image(self.test_image, "Test caption", "test_post_id")
        
        # Verify that the expected path is returned
        self.assertEqual(path, "media/videos/tiktok_test_post_id_12345.mp4")
    
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