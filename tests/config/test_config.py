from unittest.mock import MagicMock

class MockClient:
    def messages(self):
        return MagicMock()

# Mock API responses and configuration for tests
MOCK_CONFIG = {
    "anthropic_api_key": "test_api_key",
    "unsplash_api_key": "test_unsplash_key",
    "pexels_api_key": "test_pexels_key"
}

# Environment overrides for tests
def setup_test_environment():
    import os
    os.environ["ANTHROPIC_API_KEY"] = MOCK_CONFIG["anthropic_api_key"]
    os.environ["UNSPLASH_ACCESS_KEY"] = MOCK_CONFIG["unsplash_api_key"]
    os.environ["PEXELS_API_KEY"] = MOCK_CONFIG["pexels_api_key"]
