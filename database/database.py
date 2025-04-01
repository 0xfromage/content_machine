# database/database.py
import logging
import os
from sqlalchemy import create_engine, event, Integer, func
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

from config.settings import config
from database.models import Base
from utils.error_handler import handle_general_error

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestionnaire de connexion à la base de données."""
    
    def __init__(self):
        """Initialiser le gestionnaire de base de données."""
        self.engine = None
        self.Session = None
        self.initialized = False
    
    def initialize(self):
        """Initialiser la connexion à la base de données."""
        try:
            # Créer le moteur SQLAlchemy
            if config.database.db_type == 'sqlite':
                db_path = config.database.db_name
                # Créer le dossier parent si nécessaire
                os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
                
                self.engine = create_engine(f'sqlite:///{db_path}')
                
                # Activer le support des clés étrangères pour SQLite
                @event.listens_for(self.engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()
                    
            elif config.database.db_type == 'postgresql':
                db_url = (
                    f'postgresql://{config.database.db_user}:{config.database.db_password}@'
                    f'{config.database.db_host}:{config.database.db_port}/{config.database.db_name}'
                )
                self.engine = create_engine(db_url)
            else:
                logger.error(f"Unsupported database type: {config.database.db_type}")
                return False
            
            # Créer une session factory
            self.Session = scoped_session(sessionmaker(bind=self.engine))
            
            # Créer les tables si elles n'existent pas
            Base.metadata.create_all(self.engine)
            
            self.initialized = True
            logger.info(f"Database connection initialized: {config.database.db_type}")
            return True
            
        except SQLAlchemyError as e:
            error_msg = f"Error initializing database: {str(e)}"
            logger.error(error_msg)
            handle_general_error("database", error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected error initializing database: {str(e)}"
            logger.error(error_msg)
            handle_general_error("database", error_msg)
            return False
    
    @contextmanager
    def session_scope(self):
        """
        Fournir un contexte transactionnel pour les opérations de base de données.
        
        Usage:
            with db_manager.session_scope() as session:
                session.add(some_object)
        """
        if not self.initialized:
            self.initialize()
            
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            error_msg = f"Database session error: {str(e)}"
            logger.error(error_msg)
            handle_general_error("database_session", error_msg)
            raise
        finally:
            session.close()
    
    def check_connection(self):
        """
        Vérifier si la connexion à la base de données est fonctionnelle.
        
        Returns:
            True si la connexion est fonctionnelle, False sinon.
        """
        if not self.initialized:
            return self.initialize()
            
        try:
            # Exécuter une requête simple pour vérifier la connexion
            with self.session_scope() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {str(e)}")
            return False
    
    def backup_database(self, backup_path=None):
        """
        Créer une sauvegarde de la base de données.
        
        Args:
            backup_path: Chemin où sauvegarder la base de données.
                         Si None, un nom par défaut sera généré.
                         
        Returns:
            Chemin de la sauvegarde ou None en cas d'erreur.
        """
        if not self.initialized:
            if not self.initialize():
                return None
                
        try:
            if config.database.db_type == 'sqlite':
                import shutil
                from datetime import datetime
                
                # Générer un nom de fichier pour la sauvegarde
                if backup_path is None:
                    backup_dir = "backups"
                    os.makedirs(backup_dir, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
                
                # Copier le fichier SQLite
                shutil.copy2(config.database.db_name, backup_path)
                logger.info(f"Database backup created: {backup_path}")
                return backup_path
                
            elif config.database.db_type == 'postgresql':
                # Pour PostgreSQL, utiliser pg_dump
                import subprocess
                from datetime import datetime
                
                # Générer un nom de fichier pour la sauvegarde
                if backup_path is None:
                    backup_dir = "backups"
                    os.makedirs(backup_dir, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = os.path.join(backup_dir, f"backup_{timestamp}.sql")
                
                # Exécuter pg_dump
                cmd = [
                    "pg_dump",
                    f"--host={config.database.db_host}",
                    f"--port={config.database.db_port}",
                    f"--username={config.database.db_user}",
                    f"--dbname={config.database.db_name}",
                    f"--file={backup_path}"
                ]
                
                env = os.environ.copy()
                env["PGPASSWORD"] = config.database.db_password
                
                subprocess.run(cmd, env=env, check=True)
                logger.info(f"Database backup created: {backup_path}")
                return backup_path
                
            else:
                logger.error(f"Backup not supported for database type: {config.database.db_type}")
                return None
                
        except Exception as e:
            error_msg = f"Database backup failed: {str(e)}"
            logger.error(error_msg)
            handle_general_error("database_backup", error_msg)
            return None
    
    def vacuum_database(self):
        """
        Optimiser la base de données SQLite avec VACUUM.
        
        Returns:
            True si l'optimisation a réussi, False sinon.
        """
        if not self.initialized:
            if not self.initialize():
                return False
                
        try:
            if config.database.db_type == 'sqlite':
                with self.session_scope() as session:
                    session.execute("VACUUM")
                logger.info("Database vacuumed successfully")
                return True
            else:
                logger.warning(f"VACUUM not supported for database type: {config.database.db_type}")
                return False
                
        except Exception as e:
            error_msg = f"Database vacuum failed: {str(e)}"
            logger.error(error_msg)
            handle_general_error("database_vacuum", error_msg)
            return False
    
    def get_database_stats(self):
        """
        Obtenir des statistiques sur la base de données.
        
        Returns:
            Dictionnaire de statistiques ou None en cas d'erreur.
        """
        if not self.initialized:
            if not self.initialize():
                return None
                
        try:
            stats = {}
            
            with self.session_scope() as session:
                # Statistiques générales
                from database.models import RedditPost, ProcessedContent, MediaContent, PublishLog
                
                stats['total_posts'] = session.query(RedditPost).count()
                stats['processed_content'] = session.query(ProcessedContent).count()
                stats['media_content'] = session.query(MediaContent).count()
                stats['publish_logs'] = session.query(PublishLog).count()
                
                # Statistiques par statut
                post_status = session.query(
                    RedditPost.status, 
                    func.count(RedditPost.id)
                ).group_by(RedditPost.status).all()
                
                stats['post_status'] = {status: count for status, count in post_status}
                
                content_status = session.query(
                    ProcessedContent.status, 
                    func.count(ProcessedContent.id)
                ).group_by(ProcessedContent.status).all()
                
                stats['content_status'] = {status: count for status, count in content_status}
                
                # Statistiques de publication
                publish_success = session.query(
                    PublishLog.platform,
                    func.sum(func.cast(PublishLog.success, Integer))
                ).group_by(PublishLog.platform).all()
                
                stats['publish_success'] = {platform: int(count) for platform, count in publish_success}
                
                # Taille de la base de données
                if config.database.db_type == 'sqlite':
                    import os
                    stats['database_size'] = os.path.getsize(config.database.db_name)
            
            return stats
            
        except Exception as e:
            error_msg = f"Failed to get database stats: {str(e)}"
            logger.error(error_msg)
            handle_general_error("database_stats", error_msg)
            return None


# Instance singleton du gestionnaire de base de données
db_manager = DatabaseManager()

# Fonction pour initialiser la base de données
def init_db():
    """Initialiser la base de données."""
    return db_manager.initialize()