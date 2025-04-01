# scripts/setup_nltk.py
import nltk

def download_nltk_resources():
    """Download required NLTK resources."""
    print("Downloading NLTK resources...")
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')
    print("NLTK resources downloaded successfully.")

if __name__ == "__main__":
    download_nltk_resources()