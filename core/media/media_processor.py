# core/media/media_processor.py
import logging
import os
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from typing import Dict, Any, Optional
import random

from config.settings import config
from utils.error_handler import handle_media_error

logger = logging.getLogger(__name__)

class MediaProcessor:
    """Classe pour traiter et améliorer les médias pour les réseaux sociaux."""
    
    def __init__(self):
        """Initialiser le processeur de médias."""
        # Créer les dossiers pour les médias traités
        os.makedirs("media/processed/images", exist_ok=True)
        os.makedirs("media/processed/videos", exist_ok=True)
        logger.info("Media processor initialized")
    
    def process_image(self, image_path: str, post_id: str) -> Optional[str]:
        """
        Traiter une image pour la rendre optimale pour les réseaux sociaux.
        
        Args:
            image_path: Chemin vers l'image à traiter.
            post_id: ID du post associé.
            
        Returns:
            Chemin vers l'image traitée ou None en cas d'erreur.
        """
        try:
            # Vérifier si le fichier existe
            if not os.path.exists(image_path):
                logger.error(f"Image not found: {image_path}")
                return None
            
            # Ouvrir l'image avec PIL
            image = Image.open(image_path)
            
            # Appliquer un ensemble de traitements
            processed_image = self._enhance_image(image)
            
            # Générer un chemin pour l'image traitée
            processed_path = f"media/processed/images/processed_{post_id}.jpg"
            
            # Sauvegarder l'image traitée
            processed_image.save(processed_path, "JPEG", quality=95)
            
            logger.info(f"Image successfully processed: {processed_path}")
            return processed_path
            
        except Exception as e:
            error_msg = f"Error processing image: {str(e)}"
            logger.error(error_msg)
            handle_media_error("image_processing", error_msg, post_id=post_id)
            return None
    
    def _enhance_image(self, image: Image.Image) -> Image.Image:
        """
        Améliorer une image pour les réseaux sociaux.
        
        Args:
            image: Image PIL à améliorer.
            
        Returns:
            Image améliorée.
        """
        # S'assurer que l'image est en mode RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Normaliser l'orientation (gérer les EXIF)
        image = ImageOps.exif_transpose(image)
        
        # Légère amélioration de la netteté
        image = image.filter(ImageFilter.SHARPEN)
        
        # Légère amélioration du contraste
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        # Légère amélioration de la luminosité
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)
        
        # Légère amélioration de la saturation
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.2)
        
        return image
    
    def add_watermark(self, image_path: str, watermark_text: str) -> Optional[str]:
        """
        Ajouter un filigrane à une image.
        
        Args:
            image_path: Chemin vers l'image.
            watermark_text: Texte du filigrane.
            
        Returns:
            Chemin vers l'image avec filigrane ou None en cas d'erreur.
        """
        try:
            from PIL import ImageDraw, ImageFont
            
            # Ouvrir l'image
            image = Image.open(image_path)
            
            # Créer un objet Draw
            draw = ImageDraw.Draw(image)
            
            # Essayer de charger une police ou utiliser la police par défaut
            try:
                font = ImageFont.truetype("arial.ttf", 30)
            except IOError:
                font = ImageFont.load_default()
            
            # Obtenir la taille de l'image
            width, height = image.size
            
            # Position du filigrane (en bas à droite)
            position = (width - 250, height - 50)
            
            # Ajouter ombre pour meilleure visibilité
            draw.text((position[0]+2, position[1]+2), watermark_text, font=font, fill=(0, 0, 0, 128))
            
            # Ajouter le texte du filigrane
            draw.text(position, watermark_text, font=font, fill=(255, 255, 255, 192))
            
            # Sauvegarder l'image
            watermarked_path = image_path.replace(".jpg", "_watermarked.jpg")
            image.save(watermarked_path, "JPEG", quality=95)
            
            return watermarked_path
            
        except Exception as e:
            logger.error(f"Error adding watermark: {str(e)}")
            return None
    
    def create_collage(self, image_paths: list, title: str, post_id: str) -> Optional[str]:
        """
        Créer un collage à partir de plusieurs images.
        
        Args:
            image_paths: Liste des chemins d'images.
            title: Titre à afficher sur le collage.
            post_id: ID du post associé.
            
        Returns:
            Chemin vers le collage ou None en cas d'erreur.
        """
        try:
            from PIL import ImageDraw, ImageFont
            
            # Nombre d'images
            num_images = len(image_paths)
            if num_images == 0:
                return None
            
            # Charger les images
            images = []
            for path in image_paths:
                if os.path.exists(path):
                    img = Image.open(path)
                    images.append(img)
            
            if not images:
                return None
            
            # Taille du collage (format carré pour Instagram)
            collage_width = 1080
            collage_height = 1080
            
            # Créer une nouvelle image pour le collage
            collage = Image.new('RGB', (collage_width, collage_height), (255, 255, 255))
            
            # Déterminer la disposition en fonction du nombre d'images
            if len(images) == 1:
                # Une seule image centrée
                img = images[0]
                img = img.resize((collage_width, collage_height - 100))
                collage.paste(img, (0, 100))
            elif len(images) == 2:
                # Deux images côte à côte
                for i, img in enumerate(images):
                    img = img.resize((collage_width // 2, collage_height - 100))
                    collage.paste(img, (i * (collage_width // 2), 100))
            elif len(images) == 3:
                # Trois images: une en haut, deux en bas
                img = images[0]
                img = img.resize((collage_width, (collage_height - 100) // 2))
                collage.paste(img, (0, 100))
                
                for i in range(1, 3):
                    img = images[i]
                    img = img.resize((collage_width // 2, (collage_height - 100) // 2))
                    collage.paste(img, ((i-1) * (collage_width // 2), 100 + (collage_height - 100) // 2))
            else:
                # 4 images ou plus: grille 2x2
                for i in range(min(4, len(images))):
                    img = images[i]
                    img = img.resize((collage_width // 2, (collage_height - 100) // 2))
                    collage.paste(img, ((i % 2) * (collage_width // 2), 100 + (i // 2) * (collage_height - 100) // 2))
            
            # Ajouter le titre
            draw = ImageDraw.Draw(collage)
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except IOError:
                font = ImageFont.load_default()
                
            # Dessiner le titre
            draw.rectangle([(0, 0), (collage_width, 100)], fill=(52, 152, 219))
            draw.text((10, 30), title, font=font, fill=(255, 255, 255))
            
            # Sauvegarder le collage
            collage_path = f"media/processed/images/collage_{post_id}.jpg"
            collage.save(collage_path, "JPEG", quality=95)
            
            return collage_path
            
        except Exception as e:
            error_msg = f"Error creating collage: {str(e)}"
            logger.error(error_msg)
            handle_media_error("collage_creation", error_msg, post_id=post_id)
            return None