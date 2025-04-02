#!/usr/bin/env python3
"""
Standalone script to launch the validation web interface.
"""
import os
import sys
import webbrowser
import subprocess
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def launch_web_interface(port=8501, headless=True, open_browser=True):
    """
    Launch the Streamlit web interface.
    
    Args:
        port: Port number to use
        headless: Whether to run in headless mode (no welcome screen)
        open_browser: Whether to open the browser automatically
    """
    # Get the path to app.py
    project_root = Path(__file__).parent
    app_path = project_root / "web_interface" / "app.py"
    
    # Make sure the app exists
    if not app_path.exists():
        print(f"❌ Error: Could not find {app_path}")
        return False
    
    # Prepare the command
    cmd = [
        "streamlit", "run", str(app_path),
        "--server.port", str(port),
        "--server.address", "localhost"
    ]
    
    if headless:
        cmd.extend(["--server.headless", "true"])
    
    # Launch Streamlit
    print(f"🚀 Launching web interface on http://localhost:{port}...")
    
    try:
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Wait a bit for Streamlit to start
        time.sleep(2)
        
        # Open browser if requested
        if open_browser:
            webbrowser.open(f"http://localhost:{port}")
        
        # Print the URL
        print(f"\n✅ Web interface running at: http://localhost:{port}")
        print("Press Ctrl+C to stop the server.\n")
        
        # Keep the script running until the user stops it
        while True:
            try:
                output = process.stdout.readline()
                if output:
                    # Skip welcome screen message
                    if "Welcome to Streamlit!" not in output and "swag" not in output:
                        print(output.strip())
                
                # Check if process is still running
                if process.poll() is not None:
                    break
                    
                time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n⏹️ Stopping web interface...")
                process.terminate()
                process.wait()
                print("✅ Server stopped.")
                break
        
        return True
        
    except Exception as e:
        print(f"❌ Error launching web interface: {e}")
        return False

if __name__ == "__main__":
    # Check for command line arguments
    port = 8501
    headless = True
    open_browser = True
    
    # Parse arguments
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--port" and i+2 <= len(sys.argv[1:]):
            try:
                port = int(sys.argv[i+2])
            except ValueError:
                print(f"Invalid port number: {sys.argv[i+2]}")
        elif arg == "--no-browser":
            open_browser = False
        elif arg == "--welcome":
            headless = False
    
    # Launch the interface
    launch_web_interface(port, headless, open_browser)