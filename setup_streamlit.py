#!/usr/bin/env python3
"""
Setup script for Streamlit configuration.
"""
import os
import sys
import shutil
from pathlib import Path

def setup_streamlit_config():
    """Create the .streamlit directory and config file."""
    # Create .streamlit directory if it doesn't exist
    streamlit_dir = Path('.streamlit')
    streamlit_dir.mkdir(exist_ok=True)
    
    # Check if config.toml already exists
    config_path = streamlit_dir / 'config.toml'
    if config_path.exists():
        print(f"The file {config_path} already exists.")
        overwrite = input("Do you want to overwrite it? (y/n): ").lower()
        if overwrite != 'y':
            print("Operation canceled.")
            return False
    
    # Write the config file
    config_content = """
# Streamlit configuration file

[browser]
serverAddress = "localhost"
gatherUsageStats = false

[server]
headless = true
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 200
maxMessageSize = 200

[theme]
primaryColor = "#3CB371"  # Medium Sea Green
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F8FF"  # AliceBlue
textColor = "#262730"
font = "sans serif"

[logger]
level = "info"
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"✅ Streamlit configuration file created at {config_path}")
    return True

if __name__ == "__main__":
    setup_streamlit_config()