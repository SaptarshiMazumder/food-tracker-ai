import os
import sys
import glob
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app

def print_env_files():
    """Print all environment files found in the project directory"""
    print("=== Environment Files Found ===")
    
    # Get the project root directory (parent of app directory)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"Searching in project root: {project_root}")
    
    # Common environment file patterns
    env_patterns = [
        "*.env",
        "*.env.*",
        ".env*",
        "env.*",
        "environment.*",
        "config.env",
        "settings.env"
    ]
    
    found_files = []
    
    # Search for environment files in project root and subdirectories
    for pattern in env_patterns:
        # Search in project root
        files = glob.glob(os.path.join(project_root, pattern))
        found_files.extend(files)
        
        # Search in app directory
        app_dir = os.path.join(project_root, "app")
        if os.path.exists(app_dir):
            files = glob.glob(os.path.join(app_dir, pattern))
            found_files.extend(files)
        
        # Search recursively in all subdirectories
        for root, dirs, files in os.walk(project_root):
            for file in files:
                if any(file.endswith(ext) for ext in ['.env', '.env.local', '.env.production', '.env.development']):
                    found_files.append(os.path.join(root, file))
    
    # Remove duplicates and sort
    found_files = sorted(list(set(found_files)))
    
    if found_files:
        print(f"Found {len(found_files)} environment file(s):")
        for file_path in found_files:
            print(f"  - {file_path}")
            
            # Try to read and print the first few lines of each env file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    print(f"    Content (first 5 lines):")
                    for i, line in enumerate(lines[:5]):
                        # Mask sensitive values (like API keys)
                        if '=' in line and any(keyword in line.lower() for keyword in ['key', 'secret', 'password', 'token']):
                            parts = line.split('=', 1)
                            if len(parts) == 2:
                                masked_value = '*' * min(len(parts[1].strip()), 10)
                                print(f"      {parts[0]}={masked_value}")
                            else:
                                print(f"      {line.rstrip()}")
                        else:
                            print(f"      {line.rstrip()}")
                    if len(lines) > 5:
                        print(f"      ... ({len(lines) - 5} more lines)")
            except Exception as e:
                print(f"    Error reading file: {e}")
    else:
        print("No environment files found.")
    
    print("=== End Environment Files ===\n")

# Print environment files before creating the app
print_env_files()

# Create the Flask application
app = create_app()

# if __name__ == "__main__":
#     port = int(os.getenv("PORT", "5000"))
#     app.run(host="127.0.0.1", port=port, debug=True, threaded=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)