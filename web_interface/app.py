import streamlit as st
import pandas as pd
import os
import logging
import sys
from datetime import datetime
from PIL import Image


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import config
from database.models import Session, RedditPost, ProcessedContent, MediaContent
from core.publisher.instagram_publisher import InstagramPublisher
from core.publisher.tiktok_publisher import TikTokPublisher

logger = logging.getLogger(__name__)

class ContentValidatorApp:
    """Application Streamlit pour valider le contenu avant publication."""
    
    def __init__(self):
        """Initialiser l'application Streamlit."""
        self.instagram_publisher = InstagramPublisher()
        self.tiktok_publisher = TikTokPublisher()
        
        # Configuration de la page Streamlit
        st.set_page_config(
            page_title="Content Machine - Validation",
            page_icon="🤖",
            layout="wide"
        )
    
    def run(self):
        """Exécuter l'application Streamlit."""
        st.title("Content Machine - Validation du Contenu")
        
        # Barre latérale pour les options
        with st.sidebar:
            st.header("Options")
            view_option = st.selectbox(
                "Vue :",
                ["Contenu à valider", "Contenu scrapé", "Tous les contenus", "Contenus validés", "Contenus rejetés", "Contenus publiés"]
            )
            
            st.header("Configuration")
            if st.button("Paramètres"):
                self.show_settings()
        
        # Afficher la vue sélectionnée
        if view_option == "Contenu à valider":
            self._show_content_to_validate()
        elif view_option == "Contenu scrapé":
            self._show_scraped_content()
        elif view_option == "Tous les contenus":
            self._show_all_content()
        elif view_option == "Contenus validés":
            self._show_validated_content()
        elif view_option == "Contenus rejetés":
            self._show_rejected_content()
        elif view_option == "Contenus publiés":
            self._show_published_content()
    
    def _show_scraped_content(self):
        """Afficher le contenu scrapé en attente de traitement."""
        st.header("Contenu scrapé en attente de traitement")
        
        with Session() as session:
            scraped_posts = session.query(RedditPost).filter_by(status='new').all()
            
            if not scraped_posts:
                st.info("Aucun nouveau contenu scrapé à traiter.")
                return
                
            # Option de sélection en masse
            all_ids = [post.reddit_id for post in scraped_posts]
            selected_posts = st.multiselect(
                "Sélectionner plusieurs posts pour action en masse",
                options=all_ids,
                format_func=lambda x: session.query(RedditPost).filter_by(reddit_id=x).first().title
            )
            
            # Actions en masse
            if selected_posts:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Traiter la sélection"):
                        for post_id in selected_posts:
                            # Mettre à jour le statut pour traitement
                            post = session.query(RedditPost).filter_by(reddit_id=post_id).first()
                            post.status = 'pending_processing'
                        session.commit()
                        st.success(f"{len(selected_posts)} posts marqués pour traitement")
                        st.rerun()
                
                with col2:
                    if st.button("Supprimer la sélection"):
                        for post_id in selected_posts:
                            post = session.query(RedditPost).filter_by(reddit_id=post_id).first()
                            session.delete(post)
                        session.commit()
                        st.success(f"{len(selected_posts)} posts supprimés")
                        st.rerun()
            
            # Afficher chaque post individuellement
            for post in scraped_posts:
                with st.expander(f"{post.title} (r/{post.subreddit})"):
                    st.write(f"**Upvotes:** {post.upvotes} | **Commentaires:** {post.num_comments}")
                    st.write(f"**Date de création:** {post.created_utc}")
                    st.write(f"**Auteur:** {post.author}")
                    st.write(f"**Lien Reddit:** [Voir sur Reddit](https://reddit.com{post.permalink})")
                    
                    if post.content:
                        with st.expander("Contenu complet"):
                            st.write(post.content)
                    
                    # Actions individuelles
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        edit_title = st.text_input("Titre", post.title, key=f"title_{post.reddit_id}")
                        edit_content = st.text_area("Contenu", post.content, key=f"content_{post.reddit_id}")
                        if st.button("Sauvegarder les modifications", key=f"save_{post.reddit_id}"):
                            post.title = edit_title
                            post.content = edit_content
                            session.commit()
                            st.success("Modifications sauvegardées")
                            st.rerun()
                    
                    with col2:
                        if st.button("Traiter", key=f"process_{post.reddit_id}"):
                            post.status = 'pending_processing'
                            session.commit()
                            st.success("Post marqué pour traitement")
                            st.rerun()
                    
                    with col3:
                        if st.button("Supprimer", key=f"delete_{post.reddit_id}"):
                            session.delete(post)
                            session.commit()
                            st.success("Post supprimé")
                            st.rerun()
    
    def _show_content_to_validate(self):
        """Afficher le contenu traité en attente de validation."""
        content_filter = ProcessedContent.status == 'pending_validation'
        contents = self._get_contents(content_filter)
        
        if not contents:
            st.info("Aucun contenu à valider.")
            return
        
        st.header("Contenu à valider")
        self._display_contents(contents)
    
    def _show_all_content(self):
        """Afficher tous les contenus."""
        contents = self._get_contents(True)
        
        if not contents:
            st.info("Aucun contenu trouvé.")
            return
        
        st.header("Tous les contenus")
        self._display_contents(contents)
    
    def _show_validated_content(self):
        """Afficher les contenus validés."""
        content_filter = ProcessedContent.status == 'validated'
        contents = self._get_contents(content_filter)
        
        if not contents:
            st.info("Aucun contenu validé.")
            return
        
        st.header("Contenus validés")
        self._display_contents(contents)
    
    def _show_rejected_content(self):
        """Afficher les contenus rejetés."""
        content_filter = ProcessedContent.status == 'rejected'
        contents = self._get_contents(content_filter)
        
        if not contents:
            st.info("Aucun contenu rejeté.")
            return
        
        st.header("Contenus rejetés")
        self._display_contents(contents)
    
    def _show_published_content(self):
        """Afficher les contenus publiés."""
        content_filter = ProcessedContent.status == 'published'
        contents = self._get_contents(content_filter)
        
        if not contents:
            st.info("Aucun contenu publié.")
            return
        
        st.header("Contenus publiés")
        self._display_contents(contents)
    
    def _get_filter(self, filter_option):
        """
        Obtenir le filtre SQL en fonction de l'option sélectionnée.
        
        Args:
            filter_option: Option de filtre sélectionnée.
            
        Returns:
            Fonction de filtre pour la requête SQLAlchemy.
        """
        if filter_option == "En attente de validation":
            return ProcessedContent.status == 'pending_validation'
        elif filter_option == "Validés":
            return ProcessedContent.status == 'validated'
        elif filter_option == "Rejetés":
            return ProcessedContent.status == 'rejected'
        elif filter_option == "Publiés":
            return ProcessedContent.status == 'published'
        else:  # Tous
            return True
    
    def _get_contents(self, content_filter):
        """
        Obtenir les contenus à afficher depuis la base de données.
        
        Args:
            content_filter: Filtre à appliquer.
            
        Returns:
            Liste de contenus.
        """
        try:
            with Session() as session:
                # Joindre les tables pour obtenir toutes les informations nécessaires
                query = (
                    session.query(
                        RedditPost, 
                        ProcessedContent, 
                        MediaContent
                    )
                    .join(
                        ProcessedContent, 
                        RedditPost.reddit_id == ProcessedContent.reddit_id
                    )
                    .outerjoin(
                        MediaContent,
                        RedditPost.reddit_id == MediaContent.reddit_id
                    )
                    .filter(content_filter)
                    .order_by(ProcessedContent.created_at.desc())
                )
                
                results = query.all()
                
                # Formater les résultats
                contents = []
                for reddit_post, processed_content, media_content in results:
                    content = {
                        'reddit_id': reddit_post.reddit_id,
                        'title': reddit_post.title,
                        'content': reddit_post.content,
                        'subreddit': reddit_post.subreddit,
                        'upvotes': reddit_post.upvotes,
                        'permalink': reddit_post.permalink,
                        'instagram_caption': processed_content.instagram_caption,
                        'tiktok_caption': processed_content.tiktok_caption,
                        'status': processed_content.status,
                        'created_at': processed_content.created_at,
                        'published_instagram': processed_content.published_instagram,
                        'published_tiktok': processed_content.published_tiktok,
                        'media_path': media_content.file_path if media_content else None,
                        'media_source': media_content.source if media_content else None
                    }
                    contents.append(content)
                
                return contents
                
        except Exception as e:
            logger.error(f"Error retrieving contents: {str(e)}")
            st.error(f"Erreur lors de la récupération des contenus: {str(e)}")
            return []
    
    def _display_contents(self, contents):
        """
        Afficher les contenus dans l'interface Streamlit.
        
        Args:
            contents: Liste de contenus à afficher.
        """
        # Option de sélection en masse
        content_ids = [content['reddit_id'] for content in contents]
        selected_contents = st.multiselect(
            "Sélectionner plusieurs contenus pour action en masse",
            options=content_ids,
            format_func=lambda x: next((c['title'][:50] + "..." if len(c['title']) > 50 else c['title'] for c in contents if c['reddit_id'] == x), x)
        )
        
        # Actions en masse
        if selected_contents:
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Valider la sélection"):
                    for content_id in selected_contents:
                        content = next((c for c in contents if c['reddit_id'] == content_id), None)
                        if content:
                            self._update_content_status(
                                content_id, 
                                'validated', 
                                content['instagram_caption'], 
                                content['tiktok_caption']
                            )
                    st.success(f"{len(selected_contents)} contenus validés!")
                    st.rerun()
            
            with col2:
                if st.button("Rejeter la sélection"):
                    for content_id in selected_contents:
                        content = next((c for c in contents if c['reddit_id'] == content_id), None)
                        if content:
                            self._update_content_status(
                                content_id, 
                                'rejected', 
                                content['instagram_caption'], 
                                content['tiktok_caption']
                            )
                    st.success(f"{len(selected_contents)} contenus rejetés!")
                    st.rerun()
            
            with col3:
                platforms = st.multiselect(
                    "Choisir les plateformes pour la publication en masse",
                    options=["Instagram", "TikTok"],
                    default=["Instagram", "TikTok"]
                )
                
                if st.button("Publier la sélection"):
                    success_count = 0
                    for content_id in selected_contents:
                        content = next((c for c in contents if c['reddit_id'] == content_id), None)
                        if content:
                            success = True
                            if "Instagram" in platforms:
                                ig_success = self._publish_to_instagram(
                                    content_id, 
                                    content['instagram_caption'], 
                                    content['media_path']
                                )
                                success = success and ig_success
                            
                            if "TikTok" in platforms:
                                tt_success = self._publish_to_tiktok(
                                    content_id, 
                                    content['tiktok_caption'], 
                                    content['media_path']
                                )
                                success = success and tt_success
                            
                            if success:
                                success_count += 1
                    
                    st.success(f"{success_count}/{len(selected_contents)} contenus publiés avec succès!")
                    st.rerun()
        
        # Affichage individuel des contenus
        for i, content in enumerate(contents):
            with st.container():
                st.header(f"#{i+1} - {content['title']}")
                
                # Afficher les détails du post Reddit
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.subheader("Détails du post Reddit")
                    st.write(f"**Subreddit:** r/{content['subreddit']}")
                    st.write(f"**Upvotes:** {content['upvotes']}")
                    
                    # Afficher l'image
                    if content['media_path'] and os.path.exists(content['media_path']):
                        try:
                            image = Image.open(content['media_path'])
                            st.image(image, caption=f"Source: {content['media_source']}")
                        except Exception as e:
                            st.error(f"Erreur lors de l'affichage de l'image: {str(e)}")
                    else:
                        st.warning("Aucune image disponible")
                    
                    # Statut de publication
                    st.subheader("Statut de publication")
                    if content['published_instagram']:
                        st.success("✅ Publié sur Instagram")
                    else:
                        st.info("❌ Non publié sur Instagram")
                    
                    if content['published_tiktok']:
                        st.success("✅ Publié sur TikTok")
                    else:
                        st.info("❌ Non publié sur TikTok")
                
                with col2:
                    # Onglets pour les différentes plateformes
                    tabs = st.tabs(["Instagram", "TikTok", "Original"])
                    
                    with tabs[0]:
                        st.subheader("Instagram Caption")
                        instagram_caption = st.text_area(
                            "Modifier la caption Instagram",
                            content['instagram_caption'],
                            height=200,
                            key=f"instagram_{content['reddit_id']}"
                        )
                    
                    with tabs[1]:
                        st.subheader("TikTok Caption")
                        tiktok_caption = st.text_area(
                            "Modifier la caption TikTok",
                            content['tiktok_caption'],
                            height=100,
                            key=f"tiktok_{content['reddit_id']}"
                        )
                    
                    with tabs[2]:
                        st.subheader("Contenu Original")
                        st.write(f"**Titre:** {content['title']}")
                        st.write(f"**Contenu:**\n{content['content']}")
                        st.write(f"**Lien Reddit:** [Voir sur Reddit](https://reddit.com{content['permalink']})")
                    
                    # Choix des plateformes de publication
                    st.subheader("Options de publication")
                    platforms = st.multiselect(
                        "Plateformes de publication",
                        options=["Instagram", "TikTok"],
                        default=["Instagram", "TikTok"],
                        key=f"platforms_{content['reddit_id']}"
                    )
                
                # Actions
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("Valider", key=f"validate_{content['reddit_id']}"):
                        self._update_content_status(
                            content['reddit_id'], 
                            'validated', 
                            instagram_caption, 
                            tiktok_caption
                        )
                        st.success("Contenu validé!")
                        st.rerun()
                
                with col2:
                    if st.button("Rejeter", key=f"reject_{content['reddit_id']}"):
                        self._update_content_status(
                            content['reddit_id'], 
                            'rejected', 
                            instagram_caption, 
                            tiktok_caption
                        )
                        st.error("Contenu rejeté!")
                        st.rerun()
                
                with col3:
                    if st.button("Publier", key=f"publish_{content['reddit_id']}"):
                        success_messages = []
                        
                        if "Instagram" in platforms:
                            ig_success = self._publish_to_instagram(
                                content['reddit_id'], 
                                instagram_caption, 
                                content['media_path']
                            )
                            if ig_success:
                                success_messages.append("Instagram")
                        
                        if "TikTok" in platforms:
                            tt_success = self._publish_to_tiktok(
                                content['reddit_id'], 
                                tiktok_caption, 
                                content['media_path']
                            )
                            if tt_success:
                                success_messages.append("TikTok")
                        
                        if success_messages:
                            st.success(f"Publié sur {' et '.join(success_messages)}!")
                            st.rerun()
                        else:
                            st.error("Échec de la publication. Veuillez vérifier les logs.")
                
                st.divider()
    
    def _update_content_status(self, reddit_id, status, instagram_caption, tiktok_caption):
        """
        Mettre à jour le statut et le contenu dans la base de données.
        
        Args:
            reddit_id: ID du post Reddit.
            status: Nouveau statut.
            instagram_caption: Caption Instagram mise à jour.
            tiktok_caption: Caption TikTok mise à jour.
            
        Returns:
            True si la mise à jour a réussi, False sinon.
        """
        try:
            with Session() as session:
                processed_content = session.query(ProcessedContent).filter_by(reddit_id=reddit_id).first()
                if processed_content:
                    processed_content.status = status
                    if instagram_caption is not None:
                        processed_content.instagram_caption = instagram_caption
                    if tiktok_caption is not None:
                        processed_content.tiktok_caption = tiktok_caption
                    processed_content.updated_at = datetime.now()
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error updating content status: {str(e)}")
            st.error(f"Erreur lors de la mise à jour du statut: {str(e)}")
            return False
    
    def _publish_to_instagram(self, reddit_id, caption, media_path):
        """
        Publier le contenu sur Instagram.
        
        Args:
            reddit_id: ID du post Reddit.
            caption: Caption à publier.
            media_path: Chemin vers le média à publier.
            
        Returns:
            True si la publication a réussi, False sinon.
        """
        try:
            result = self.instagram_publisher.publish(
                media_path=media_path,
                caption=caption,
                post_id=reddit_id
            )
            
            if result.get('success'):
                # Mettre à jour le statut dans la base de données
                with Session() as session:
                    processed_content = session.query(ProcessedContent).filter_by(reddit_id=reddit_id).first()
                    if processed_content:
                        processed_content.status = 'published'
                        processed_content.published_instagram = True
                        processed_content.instagram_post_id = result.get('post_id')
                        processed_content.updated_at = datetime.now()
                        session.commit()
                return True
            else:
                st.error(f"Erreur lors de la publication sur Instagram: {result.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Error publishing to Instagram: {str(e)}")
            st.error(f"Erreur lors de la publication sur Instagram: {str(e)}")
            return False
    
    def _publish_to_tiktok(self, reddit_id, caption, media_path):
        """
        Publier le contenu sur TikTok.
        
        Args:
            reddit_id: ID du post Reddit.
            caption: Caption à publier.
            media_path: Chemin vers le média à publier.
            
        Returns:
            True si la publication a réussi, False sinon.
        """
        try:
            result = self.tiktok_publisher.publish(
                media_path=media_path,
                caption=caption,
                post_id=reddit_id
            )
            
            if result.get('success'):
                # Mettre à jour le statut dans la base de données
                with Session() as session:
                    processed_content = session.query(ProcessedContent).filter_by(reddit_id=reddit_id).first()
                    if processed_content:
                        processed_content.status = 'published'
                        processed_content.published_tiktok = True
                        processed_content.tiktok_post_id = result.get('post_id')
                        processed_content.updated_at = datetime.now()
                        session.commit()
                return True
            else:
                st.error(f"Erreur lors de la publication sur TikTok: {result.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Error publishing to TikTok: {str(e)}")
            st.error(f"Erreur lors de la publication sur TikTok: {str(e)}")
            return False
    
    def show_settings(self):
        """Afficher et modifier les paramètres de l'application."""
        st.title("Paramètres de l'application")
        
        # Reddit Settings
        st.header("Paramètres Reddit")
        subreddits = st.text_input("Subreddits (séparés par des virgules)", 
                                 ", ".join(config.reddit.subreddits))
        min_upvotes = st.number_input("Minimum d'upvotes", 
                                    min_value=1, 
                                    value=config.reddit.min_upvotes)
        post_limit = st.number_input("Limite de posts", 
                                   min_value=1, 
                                   value=config.reddit.post_limit)
        
        # Instagram Settings
        st.header("Paramètres Instagram")
        instagram_username = st.text_input("Nom d'utilisateur Instagram", 
                                        config.instagram.username)
        
        # TikTok Settings
        st.header("Paramètres TikTok")
        tiktok_username = st.text_input("Nom d'utilisateur TikTok", 
                                      config.tiktok.username)
        
        # Claude Settings
        st.header("Paramètres Claude")
        anthropic_model = st.selectbox(
            "Modèle Claude",
            ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"],
            index=0
        )
        
        # Save settings
        if st.button("Enregistrer les paramètres"):
            # Ici, vous pourriez mettre à jour le fichier .env ou une base de données
            # Pour cet exemple, nous allons simplement mettre à jour l'objet config
            config.reddit.subreddits = [s.strip() for s in subreddits.split(',')]
            config.reddit.min_upvotes = min_upvotes
            config.reddit.post_limit = post_limit
            config.instagram.username = instagram_username
            config.tiktok.username = tiktok_username
            
            # Écrire les changements dans le fichier .env
            try:
                self._update_env_file({
                    "REDDIT_SUBREDDITS": ",".join(config.reddit.subreddits),
                    "REDDIT_MIN_UPVOTES": str(min_upvotes),
                    "REDDIT_POST_LIMIT": str(post_limit),
                    "INSTAGRAM_USERNAME": instagram_username,
                    "TIKTOK_USERNAME": tiktok_username,
                    "ANTHROPIC_MODEL": anthropic_model
                })
                st.success("Paramètres enregistrés avec succès!")
            except Exception as e:
                st.error(f"Erreur lors de la sauvegarde des paramètres: {str(e)}")
    
    def _update_env_file(self, new_values):
        """
        Mettre à jour le fichier .env avec de nouvelles valeurs.
        
        Args:
            new_values: Dictionnaire de valeurs à mettre à jour.
        """
        env_path = ".env"
        
        # Vérifier si le fichier .env existe
        if not os.path.exists(env_path):
            logger.warning(f"Le fichier {env_path} n'existe pas. Création d'un nouveau fichier.")
            # Créer le fichier à partir du modèle .env.example s'il existe
            if os.path.exists(".env.example"):
                import shutil
                shutil.copy(".env.example", env_path)
                logger.info(f"Fichier {env_path} créé à partir de .env.example")
            else:
                # Créer un fichier vide
                with open(env_path, "w") as file:
                    file.write("# Fichier d'environnement Content Machine\n")
        
        try:
            # Lire le fichier .env existant
            with open(env_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
            
            # Créer un dictionnaire pour stocker les valeurs existantes
            existing_values = {}
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        key, value = line.split("=", 1)
                        existing_values[key.strip()] = value.strip()
                    except ValueError:
                        # Ignorer les lignes mal formatées
                        logger.warning(f"Ligne mal formatée ignorée: {line}")
            
            # Mettre à jour les valeurs
            existing_values.update(new_values)
            
            # Recréer le fichier .env avec les commentaires préservés et les valeurs mises à jour
            updated_lines = []
            processed_keys = set()
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    updated_lines.append(line)
                    continue
                
                try:
                    key, _ = line.split("=", 1)
                    key = key.strip()
                    
                    if key in existing_values:
                        updated_lines.append(f"{key}={existing_values[key]}")
                        processed_keys.add(key)
                    else:
                        # Conserver la ligne originale si la clé n'est pas à mettre à jour
                        updated_lines.append(line)
                except ValueError:
                    # Conserver les lignes mal formatées
                    updated_lines.append(line)
            
            # Ajouter les nouvelles valeurs qui n'existaient pas
            for key, value in existing_values.items():
                if key not in processed_keys:
                    updated_lines.append(f"{key}={value}")
            
            # Écrire le fichier mis à jour
            with open(env_path, "w", encoding="utf-8") as file:
                file.write("\n".join(updated_lines) + "\n")
            
            logger.info(f"Fichier {env_path} mis à jour avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du fichier {env_path}: {str(e)}")
            raise


# Point d'entrée pour Streamlit
if __name__ == "__main__":
    app = ContentValidatorApp()
    app.run()