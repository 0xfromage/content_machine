# Content Machine

## Project Overview

Content Machine is an automated social media content generation tool that scrapes interesting posts from Reddit, processes them, finds relevant media, and prepares them for publication on Instagram and TikTok.

## Getting Started

### Prerequisites

- Python 3.9+
- pip
- Virtual environment (recommended)

### Installation Steps

1. Clone the repository

```bash
git clone https://github.com/yourusername/content-machine.git
cd content-machine
```

2. Create and activate a virtual environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt

# Download NLTK resources
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

4. Configure Environment

- Copy `.env.example` to `.env`
- Fill in your API credentials:
  - Reddit API credentials
  - Instagram/TikTok credentials
  - Anthropic Claude AI key
  - Image API keys (Unsplash, Pexels, Pixabay)

```bash
cp .env.example .env
# Edit the .env file with your credentials
```

## Running the Application

### Command Line Options

```bash
# Run full pipeline
python main.py --all

# Run specific components
python main.py --scrape      # Only scrape Reddit
python main.py --process     # Only process content
python main.py --media       # Only find media
python main.py --validate    # Launch web interface
```

### Daemon Mode (Continuous Operation)

```bash
# Run in background with 1-hour interval
python main.py --daemon --all

# Custom interval (in seconds)
python main.py --daemon --all --interval 1800  # 30 minutes
```

## Web Interface Usage

### Launching the Interface

```bash
streamlit run web_interface/app.py
```

### Interface Sections

1. **Contenu à valider (Content to Validate)**

   - View newly processed content
   - Manually review and edit captions
   - Validate or reject content

2. **Contenu scrapé (Scraped Content)**

   - See newly scraped Reddit posts
   - Manually process or delete posts

3. **Actions Available**
   - Edit captions
   - Select platforms for publishing
   - Bulk validate/reject content
   - Publish to Instagram/TikTok

### Interface Navigation

- Use sidebar to switch between different content views
- Select multiple posts for batch actions
- Modify captions before publishing

## Running Tests

### Test Types

- Unit Tests: Test individual components
- Integration Tests: Verify system workflow
- Media Tests: Check media processing
- Claude Client Tests: Validate AI interactions

### Running Tests

```bash
# Run all tests
python -m unittest discover tests

# Run specific test files
python -m unittest tests.test_processor
python -m unittest tests.test_integration
python -m unittest tests.test_media
```

### Specific Test Execution

```bash
# Run a specific test class
python -m unittest tests.test_processor.TestTextProcessor

# Run a specific test method
python -m unittest tests.test_processor.TestTextProcessor.test_clean_text
```

## Troubleshooting

- Check `logs/` directory for detailed logs
- Ensure all API credentials are correctly configured
- Verify internet connection
- Check Python and dependency versions

## Configuration Tips

- `config/settings.py`: Global application settings
- `config/constants.py`: Fixed constants and configurations
- `.env`: Personal API keys and sensitive information

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

[Specify your project's license]

```

Would you like me to elaborate on any specific section of the README or explain how to use any particular feature in more depth?
```
