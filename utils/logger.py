# utils/logger.py
import logging
import os
import sys
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from config.settings import config

class CustomJsonFormatter(logging.Formatter):
    """Formateur personnalisé pour formater les logs en JSON."""
    
    def format(self, record):
        """
        Formater l'enregistrement en JSON.
        
        Args:
            record: Enregistrement de log.
            
        Returns:
            Chaîne JSON formatée.
        """
        log_object = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Ajouter les informations supplémentaires si elles existent
        if hasattr(record, 'additional_info') and record.additional_info:
            log_object["additional_info"] = record.additional_info
        
        # Ajouter les informations de l'exception si elle existe
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_object, ensure_ascii=False)

def setup_logging():
    """Configurer le logging pour l'application."""
    # Créer le dossier des logs s'il n'existe pas
    os.makedirs("logs", exist_ok=True)
    
    # Obtenir le niveau de log depuis la configuration
    log_level_str = config.log_level.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Configurer le logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Supprimer les handlers existants
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    
    # Formateur standard pour la console
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Formateur JSON pour les fichiers
    json_formatter = CustomJsonFormatter()
    
    # Handler pour la console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Handler pour les logs généraux (rotation par taille)
    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(console_formatter)
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)
    
    # Handler pour les logs journaliers (rotation par jour)
    daily_handler = TimedRotatingFileHandler(
        "logs/daily.log",
        when="midnight",
        interval=1,
        backupCount=30,  # 30 jours
        encoding='utf-8'
    )
    daily_handler.setFormatter(console_formatter)
    daily_handler.setLevel(log_level)
    root_logger.addHandler(daily_handler)
    
    # Handler pour les logs d'erreur
    error_handler = RotatingFileHandler(
        "logs/error.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setFormatter(json_formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    # Handler pour les logs JSON (pour analyse ultérieure)
    json_handler = RotatingFileHandler(
        "logs/json.log",
        maxBytes=20 * 1024 * 1024,  # 20 MB
        backupCount=5,
        encoding='utf-8'
    )
    json_handler.setFormatter(json_formatter)
    json_handler.setLevel(log_level)
    root_logger.addHandler(json_handler)
    
    # Configurer les loggers tiers pour éviter le bruit
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    # Logger un message de démarrage
    logging.info("Logging initialisé. Niveau de log: %s", log_level_str)