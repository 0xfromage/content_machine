#!/usr/bin/env python3
"""
Wrapper script to run Streamlit with the correct Python path.
This ensures that all project modules can be properly imported.
"""
import os
import sys
import subprocess
from pathlib import Path

def run_streamlit():
    """Run Streamlit with the correct project path."""
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()
    
    # Path to the web interface app
    app_path = project_root / "web_interface" / "app.py"
    
    if not app_path.exists():
        print(f"Error: Could not find the app at {app_path}")
        return 1
    
    # Get the port from config
    try:
        sys.path.insert(0, str(project_root))
        from config.settings import config
        port = config.web_interface_port
    except Exception as e:
        print(f"Warning: Could not import config, using default port 8501. Error: {e}")
        port = 8501
    
    # Determine Streamlit command arguments
    streamlit_args = [
        "streamlit", "run", str(app_path),
        "--server.port", str(port),
        "--server.headless", "true"
    ]
    
    # Set PYTHONPATH environment variable to include project root
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"
    
    print(f"Starting Streamlit with PYTHONPATH={project_root}")
    print(f"Launching web interface at http://localhost:{port}")
    
    # Run Streamlit with the modified environment
    result = subprocess.run(streamlit_args, env=env)
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_streamlit())