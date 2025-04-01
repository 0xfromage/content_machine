# config/constants.py
"""
Constantes utilisées dans l'ensemble de l'application.
Ces valeurs sont fixes et ne changent pas en fonction de la configuration.
"""

# Constantes pour le statut des posts Reddit
REDDIT_STATUS = {
    'NEW': 'new',                 # Post récemment scrapé
    'PENDING': 'pending_processing',  # En attente de traitement
    'PROCESSED': 'processed',     # Traité avec succès
    'FAILED': 'failed',           # Échec du traitement
    'PUBLISHED': 'published',     # Publié avec succès
    'ARCHIVED': 'archived'        # Archivé (trop ancien)
}

# Constantes pour le statut du contenu traité
CONTENT_STATUS = {
    'PENDING': 'pending_validation',  # En attente de validation humaine
    'VALIDATED': 'validated',      # Validé par un humain
    'REJECTED': 'rejected',        # Rejeté par un humain
    'PUBLISHED': 'published',      # Publié sur les réseaux sociaux
    'FAILED': 'failed'             # Échec de publication
}

# Types de média
MEDIA_TYPES = {
    'IMAGE': 'image',
    'VIDEO': 'video',
    'GIF': 'gif',
    'CAROUSEL': 'carousel'
}

# Types de sources de média
MEDIA_SOURCES = {
    'UNSPLASH': 'unsplash',
    'PEXELS': 'pexels',
    'PIXABAY': 'pixabay',
    'FALLBACK': 'fallback'
}

# Plateformes de publication
PLATFORMS = {
    'INSTAGRAM': 'instagram',
    'TIKTOK': 'tiktok'
}

# Types d'erreurs
ERROR_TYPES = {
    # Erreurs de scraping
    'REDDIT_INIT': 'reddit_init',
    'REDDIT_SCRAPING': 'reddit_scraping',
    'SUBREDDIT_SCRAPING': 'subreddit_scraping',
    
    # Erreurs de traitement
    'TEXT_PROCESSING': 'text_processing',
    'CAPTION_GENERATION': 'caption_generation',
    'HASHTAG_GENERATION': 'hashtag_generation',
    
    # Erreurs de média
    'IMAGE_FINDING': 'image_finding',
    'VIDEO_FINDING': 'video_finding',
    'MEDIA_DOWNLOAD': 'media_download',
    'IMAGE_PROCESSING': 'image_processing',
    'VIDEO_PROCESSING': 'video_processing',
    
    # Erreurs de publication
    'INSTAGRAM_AUTH': 'instagram_auth',
    'INSTAGRAM_PUBLISH': 'instagram_publish',
    'TIKTOK_AUTH': 'tiktok_auth',
    'TIKTOK_PUBLISH': 'tiktok_publish',
    
    # Erreurs API
    'API_RATE_LIMIT': 'api_rate_limit',
    'API_AUTH': 'api_auth',
    'API_RESPONSE': 'api_response',
    
    # Erreurs générales
    'DATABASE': 'database',
    'CONFIG': 'config',
    'UNKNOWN': 'unknown'
}

# Tâches Claude AI
CLAUDE_TASKS = {
    'CAPTION_GENERATION': 'caption_generation',
    'KEYWORD_EXTRACTION': 'keyword_extraction',
    'HASHTAG_GENERATION': 'hashtag_generation',
    'CONTENT_ANALYSIS': 'content_analysis'
}

# Limites de caractères
CHARACTER_LIMITS = {
    'INSTAGRAM_CAPTION': 2200,
    'TIKTOK_CAPTION': 150,
    'INSTAGRAM_HASHTAGS': 30,
    'TIKTOK_HASHTAGS': 10
}

# Dimensions des médias
MEDIA_DIMENSIONS = {
    'INSTAGRAM_SQUARE': (1080, 1080),
    'INSTAGRAM_PORTRAIT': (1080, 1350),
    'INSTAGRAM_LANDSCAPE': (1080, 608),
    'TIKTOK_PORTRAIT': (1080, 1920),
    'STORY': (1080, 1920)
}

# Hashtags génériques par catégorie
GENERIC_HASHTAGS = {
    'LEARNING': ['#DidYouKnow', '#TodayILearned', '#InterestingFacts', '#Knowledge', '#Learning'],
    'SCIENCE': ['#Science', '#ScienceFacts', '#STEM', '#Research', '#Discovery'],
    'HISTORY': ['#History', '#HistoricalFacts', '#OTD', '#OnThisDay', '#Heritage'],
    'TECH': ['#Technology', '#Tech', '#Innovation', '#Digital', '#Future'],
    'NATURE': ['#Nature', '#Wildlife', '#Environment', '#Planet', '#Earth'],
    'ART': ['#Art', '#Creativity', '#Design', '#Inspiration', '#Creative'],
    'FOOD': ['#Food', '#Foodie', '#Recipe', '#Cooking', '#Delicious'],
    'TRAVEL': ['#Travel', '#Adventure', '#Explore', '#Wanderlust', '#TravelTips'],
    'FITNESS': ['#Fitness', '#Health', '#Wellness', '#Exercise', '#Healthy'],
    'MOTIVATION': ['#Motivation', '#Inspiration', '#Goals', '#Success', '#Mindset']
}

# Emojis par catégorie
CATEGORY_EMOJIS = {
    'LEARNING': ['✨', '🧠', '💡', '📚', '🤓'],
    'SCIENCE': ['🔬', '🧪', '🔭', '🧬', '⚗️'],
    'HISTORY': ['📜', '🏛️', '⏳', '🗿', '🏺'],
    'TECH': ['💻', '🌐', '📱', '🤖', '⚙️'],
    'NATURE': ['🌿', '🌎', '🌳', '🐾', '🦋'],
    'ART': ['🎨', '🖌️', '✏️', '🎭', '🎬'],
    'FOOD': ['🍎', '🍜', '🥗', '🍳', '🥑'],
    'TRAVEL': ['✈️', '🗺️', '🧳', '🏝️', '🌄'],
    'FITNESS': ['💪', '🏃‍♀️', '🧘‍♂️', '🚴‍♀️', '🥗'],
    'MOTIVATION': ['🔥', '💪', '⭐', '🚀', '🏆']
}

# Templates de captions
CAPTION_TEMPLATES = {
    'TIL': "{emojis} Saviez-vous que {fact}?\n\n{additional_info}\n\nSource: Reddit r/{subreddit}\n\n{hashtags}",
    'FACT': "{emojis} Fait incroyable : {fact}\n\n{additional_info}\n\nSource: Reddit r/{subreddit}\n\n{hashtags}",
    'QUESTION': "{emojis} {question}\n\nRéponse : {answer}\n\nSource: Reddit r/{subreddit}\n\n{hashtags}"
}