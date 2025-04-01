# Content Machine

## Présentation

Content Machine est une application Python qui automatise la génération et la publication de contenu sur les réseaux sociaux à partir de posts Reddit populaires.

Le flux de travail principal est le suivant :
1. Scraping des posts populaires sur Reddit
2. Traitement et optimisation du contenu pour les réseaux sociaux (Instagram et TikTok)
3. Recherche automatique d'images pertinentes
4. Interface de validation humaine avant publication
5. Publication automatisée sur Instagram et TikTok

## Architecture

L'application est conçue selon une architecture modulaire avec une séparation claire des responsabilités. Voici les principaux composants:

- **Scraper**: Récupère les posts populaires sur Reddit
- **Processor**: Traite et reformate le contenu pour les réseaux sociaux
- **Media Finder**: Recherche des images pertinentes pour le contenu
- **Content Validator**: Interface web pour valider le contenu avant publication
- **Publisher**: Publie le contenu sur Instagram et TikTok
- **Database**: Stockage centralisé des données et du statut du contenu
- **Claude AI**: Intégration avec Claude d'Anthropic pour générer des captions optimisées

## Installation

### Prérequis

- Python 3.9+
- Pip
- Virtualenv (recommandé)

### Installation des dépendances

```bash
# Créer et activer un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate  # Pour Linux/Mac
venv\Scripts\activate     # Pour Windows

# Installer les dépendances
pip install -r requirements.txt

# Télécharger les ressources NLTK nécessaires
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

### Configuration

1. Copier le fichier `.env.example` en `.env`
2. Modifier le fichier `.env` avec vos identifiants et clés API:
   - API Reddit
   - API d'images (Unsplash, Pexels, Pixabay)
   - Identifiants Instagram et TikTok
   - API Claude (Anthropic)

## Utilisation

### Exécution de base

```bash
# Exécuter le pipeline complet (scraping, traitement, média, validation)
python main.py --all

# Exécuter seulement des étapes spécifiques
python main.py --scrape
python main.py --process
python main.py --media
python main.py --validate
```

### Mode Daemon (continu)

```bash
# Exécuter en mode daemon avec l'intervalle par défaut (1 heure)
python main.py --daemon --all

# Exécuter en mode daemon avec un intervalle personnalisé (en secondes)
python main.py --daemon --all --interval 1800  # 30 minutes
```

### Interface de validation

L'interface de validation Streamlit est accessible à:
```
http://localhost:8501
```

Cette interface vous permet de:
- Visualiser les posts traités et leurs images associées
- Modifier les captions générées
- Valider ou rejeter le contenu
- Publier directement sur Instagram et TikTok

## Structure du projet

```
content_machine/
│
├── .env                      # Variables d'environnement
├── .gitignore                # Fichiers à ignorer pour Git
├── requirements.txt          # Dépendances du projet
├── README.md                 # Documentation du projet
├── main.py                   # Point d'entrée principal
│
├── config/                   # Configuration centralisée
├── core/                     # Logique métier principale
│   ├── scraper/              # Scraping de Reddit
│   ├── processor/            # Traitement du texte
│   ├── media/                # Recherche de médias
│   ├── publisher/            # Publication sur réseaux sociaux
│   └── validator/            # Validation du contenu
│
├── database/                 # Gestion de la base de données
├── web_interface/            # Interface Streamlit
└── utils/                    # Utilitaires (logging, erreurs, etc.)
```

## Développement

### Linting et Formatage

```bash
# Formater le code avec Black
black content_machine/

# Vérifier le style avec Flake8
flake8 content_machine/
```

### Tests

```bash
# Exécuter les tests
pytest
```

## Troubleshooting

### Logs

Les logs sont stockés dans le dossier `logs/`:
- `app.log` - Logs généraux de l'application
- `daily.log` - Logs quotidiens
- `error.log` - Logs d'erreurs détaillés
- `json.log` - Logs au format JSON pour analyse

### Problèmes courants

- **Erreurs d'authentification Reddit**: Vérifiez votre Client ID et Client Secret
- **Erreurs d'authentification Instagram/TikTok**: Vérifiez vos identifiants et assurez-vous de ne pas dépasser les limites de l'API
- **Rate limit dépassé**: Augmentez l'intervalle d'exécution en mode daemon

## Contribution

Les contributions sont les bienvenues! N'hésitez pas à ouvrir une issue ou une pull request.

## Licence

Ce projet est sous licence MIT.