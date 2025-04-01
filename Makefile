.PHONY: setup test clean run web fixed-tests

# Directory setup
SCRIPT_DIR = scripts
MKDIR_P = mkdir -p

setup:
	$(MKDIR_P) $(SCRIPT_DIR)
	$(MKDIR_P) media/images
	$(MKDIR_P) media/videos
	$(MKDIR_P) resources
	$(MKDIR_P) logs
	python -m pip install -r requirements.txt
	python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
	python database/models.py

init-db:
	python -c "from database.models import Base, engine; Base.metadata.create_all(engine)"

run:
	python main.py --all

web:
	streamlit run web_interface/app.py

test:
	python -m unittest discover tests

fixed-tests:
	# Run individual tests that are likely to pass after fixes
	python -m unittest tests.test_processor.TestTextProcessor.test_clean_text

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".DS_Store" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "*.egg" -exec rm -r {} +