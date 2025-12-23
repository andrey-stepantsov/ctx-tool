import os
import sys
import pathspec

# --- CONFIGURATION ---
# Rough estimate: 1 token ~= 4 chars.
TOKEN_WARNING_THRESHOLD = 100000 

def load_gitignore(root_dir):
    """Loads .gitignore patterns using pathspec for Git-compliant matching."""
    gitignore_path = os.path.join(root_dir, ".gitignore")
    lines = []
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            sys.stderr.write(f"Warning: Could not read .gitignore: {e}\n")
    
    # Always add these defaults to prevent noise in the audit
    # Added lock files here to save tokens
    default_ignores = [
        ".git/", ".aider*", ".env", "__pycache__/", "*.py