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

````markdown
## Bonnes pratiques de développement

### Style de code

Le projet suit les conventions PEP 8 pour le style de code Python. Nous utilisons Black comme formateur de code et Flake8 pour le linting.

```bash
# Formater le code
black content_machine/

# Vérifier le style avec Flake8
flake8 content_machine/
```
````

### Gestion des branches Git

Pour contribuer au projet, veuillez suivre le flux de travail des branches suivant:

1. Créez une branche à partir de `main` pour votre fonctionnalité ou correction: `feature/nom-de-fonctionnalité` ou `fix/nom-du-problème`
2. Développez et testez vos modifications
3. Créez une Pull Request pour faire réviser votre code
4. Une fois approuvée, la PR sera fusionnée dans `main`

### Tests

Tous les nouveaux composants doivent être accompagnés de tests unitaires. Les tests doivent couvrir les cas normaux et les cas d'erreur.

```bash
# Exécuter tous les tests
pytest

# Exécuter un test spécifique
pytest tests/test_scraper.py

# Exécuter les tests avec couverture de code
pytest --cov=content_machine tests/
```

### Documentation

Tous les modules, classes et fonctions doivent être documentés à l'aide de docstrings au format Google:

```python
def function(arg1: type, arg2: type) -> return_type:
    """
    Description de la fonction.

    Args:
        arg1: Description du premier argument.
        arg2: Description du deuxième argument.

    Returns:
        Description de la valeur de retour.

    Raises:
        ExceptionType: Description de quand l'exception est levée.
    """
```

````

## Ajout d'une section sur la sécurité

```markdown
## Sécurité

### Gestion des secrets

Tous les secrets (clés API, identifiants) doivent être stockés dans le fichier `.env` et ne jamais être inclus dans le code ou les commits Git. Un fichier `.env.example` est fourni comme modèle.

### Authentification aux API

Les jetons d'accès pour les API externes sont gérés via des variables d'environnement et ne doivent jamais être codés en dur dans l'application.

### Sécurisation des données utilisateur

Les identifiants Instagram et TikTok doivent être manipulés avec précaution. L'application sauvegarde les sessions pour éviter de stocker les mots de passe en clair.

### Scan de sécurité

Avant chaque déploiement, un scan des dépendances est recommandé pour identifier les vulnérabilités potentielles:

```bash
# Vérifier les dépendances
safety check -r requirements.txt
````

````

## Ajout d'une section sur le déploiement

```markdown
## Déploiement

### Exigences système

- Python 3.9+
- 2 GB de RAM minimum (4 GB recommandé)
- 1 GB d'espace disque (plus selon le volume de médias stockés)
- Accès Internet pour les API externes

### Installation sur un serveur

1. Cloner le dépôt:
   ```bash
   git clone https://github.com/votre-organisation/content-machine.git
   cd content-machine
````

2. Créer et activer un environnement virtuel:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. Installer les dépendances:

   ```bash
   pip install -r requirements.txt
   ```

4. Configurer le fichier .env:

   ```bash
   cp .env.example .env
   nano .env  # Modifier avec vos identifiants et clés API
   ```

5. Initialiser la base de données:

   ```bash
   python -c "from database.database import init_db; init_db()"
   ```

6. Lancer l'application en mode daemon:
   ```bash
   nohup python main.py --daemon --all --interval 3600 > app.log 2>&1 &
   ```

### Utilisation avec Docker

Un Dockerfile et un fichier docker-compose.yml sont inclus pour faciliter le déploiement:

```bash
# Construire l'image
docker-compose build

# Lancer les conteneurs
docker-compose up -d

# Vérifier les logs
docker-compose logs -f
```

```

## Contribution

Les contributions sont les bienvenues! N'hésitez pas à ouvrir une issue ou une pull request.

## Licence

Ce projet est sous licence MIT.
```
