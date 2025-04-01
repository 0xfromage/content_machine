import nltk

def download_resources():
    """Download all required NLTK resources."""
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')
    # Also download punkt_tab
    try:
        nltk.download('punkt_tab')
    except:
        nltk.download('punkt')  # Fallback

if __name__ == "__main__":
    download_resources()
    print("NLTK resources downloaded successfully")
