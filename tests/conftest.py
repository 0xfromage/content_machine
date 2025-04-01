import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import test config
from tests.config.test_config import setup_test_environment

@pytest.fixture(scope="session", autouse=True)
def setup_tests():
    """Set up test environment before all tests run."""
    # Setup test environment variables
    setup_test_environment()
    
    # Initialize database if needed
    from database.models import Base, engine
    Base.metadata.create_all(engine)
EOFcat > tests/conftest.py << 'EOF'
import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import test config
from tests.config.test_config import setup_test_environment

@pytest.fixture(scope="session", autouse=True)
def setup_tests():
    """Set up test environment before all tests run."""
    # Setup test environment variables
    setup_test_environment()
    
    # Initialize database if needed
    from database.models import Base, engine
    Base.metadata.create_all(engine)
