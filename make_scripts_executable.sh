#!/bin/bash
# Make Python scripts executable

# Make the launch script executable
chmod +x launch_web.py
echo "✅ Made launch_web.py executable"

# Make the setup script executable
chmod +x setup_streamlit.py
echo "✅ Made setup_streamlit.py executable"

# Make the streamlit wrapper executable
chmod +x run_streamlit.py
echo "✅ Made run_streamlit.py executable"

echo "✅ All done! You can now run ./run_streamlit.py to start the web interface."