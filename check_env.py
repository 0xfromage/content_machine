import os
from dotenv import load_dotenv

print("Checking .env file loading...")

# Print the current directory
print(f"Current directory: {os.path.abspath('.')}")

# Check if .env file exists
env_path = os.path.join(os.path.abspath('.'), '.env')
if os.path.exists(env_path):
    print(f".env file exists at: {env_path}")
    
    # Print file contents
    with open(env_path, 'r') as f:
        content = f.read()
        print("\n.env file content (sensitive info masked):")
        for line in content.split('\n'):
            if line.startswith('#') or not line.strip():
                print(line)  # Print comments and empty lines as-is
            elif '=' in line:
                key, value = line.split('=', 1)
                # Mask the value if it looks like a key or password
                if any(term in key.lower() for term in ['key', 'secret', 'password', 'token']):
                    masked_value = value[:3] + '****' if len(value) > 3 else '****'
                    print(f"{key}={masked_value}")
                else:
                    print(line)
            else:
                print(line)
else:
    print(f"No .env file found at: {env_path}")

# Try to load the .env file
load_dotenv()

# Check specific variables
anthropic_key = os.getenv('ANTHROPIC_API_KEY')
if anthropic_key:
    print("\nANTHROPIC_API_KEY: Found (value masked)")
else:
    print("\nANTHROPIC_API_KEY: Not found")

print("\nOther relevant environment variables:")
for var in ['UNSPLASH_ACCESS_KEY', 'PEXELS_API_KEY', 'PIXABAY_API_KEY']:
    value = os.getenv(var)
    if value:
        print(f"{var}: Found (value masked)")
    else:
        print(f"{var}: Not found")
