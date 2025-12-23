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
    default_ignores = [
        ".git/", ".aider*", ".env", "__pycache__/", "*.pyc", 
        "node_modules/", "dist/", "build/", ".DS_Store",
        ".venv", "venv", "*.egg-info", "target/"
    ]
    lines.extend(default_ignores)
    
    return pathspec.PathSpec.from_lines('gitwildmatch', lines)

def generate_tree(root_dir, spec):
    """Generates a visual tree structure of the included files."""
    tree_output = []
    # os.walk allows us to modify 'dirs' in-place to prevent descending into ignored folders
    for root, dirs, files in os.walk(root_dir):
        # Filter directories in place
        dirs[:] = [d for d in dirs if not spec.match_file(os.path.relpath(os.path.join(root, d), root_dir))]
        dirs.sort() # Sort for deterministic output
        
        level = root.replace(root_dir, '').count(os.sep)
        indent = '  ' * level
        subindent = '  ' * (level + 1)
        
        if root != root_dir:
            tree_output.append(f"{indent}{os.path.basename(root)}/")
        
        files.sort()
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), root_dir)
            if not spec.match_file(rel_path):
                tree_output.append(f"{subindent}{f}")
    
    return "\n".join(tree_output)

def is_text_file(filepath):
    """Simple heuristic to check if a file is text (not binary)."""
    try:
        # Read a small chunk to check for null bytes
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
        return b'\x00' not in chunk
    except Exception:
        return False

def run():
    """Entry point for the console script."""
    # Use current directory if no argument provided
    target_path = sys.argv[1] if len(sys.argv) > 1 else "."
    root_dir = os.path.abspath(target_path)
    
    if not os.path.isdir(root_dir):
        sys.stderr.write(f"Error: {root_dir} is not a directory.\n")
        sys.exit(1)

    spec = load_gitignore(root_dir)
    project_name = os.path.basename(root_dir)
    
    # Buffer for output to ensure atomic printing (helpful when piping)
    output_buffer = []
    
    # 1. Header & Tree
    output_buffer.append(f"# Project Audit: {project_name}")
    output_buffer.append("# Context Map:")
    output_buffer.append("project_structure: |")
    
    tree = generate_tree(root_dir, spec)
    # Indent the tree for YAML block scalar
    indented_tree = "\n".join(["  " + line for line in tree.splitlines()])
    output_buffer.append(indented_tree)
    output_buffer.append("\n---\n")

    # 2. File Content
    file_count = 0
    total_chars = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Filter directories
        dirs[:] = [d for d in dirs if not spec.match_file(os.path.relpath(os.path.join(root, d), root_dir))]
        dirs.sort()
        files.sort()
        
        for file in files:
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, root_dir)
            
            if spec.match_file(rel_path):
                continue
                
            if not is_text_file(filepath):
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors='ignore') as f:
                    content = f.read()
                    
                # Skip empty files
                if not content.strip():
                    continue

                output_buffer.append(f"path: {rel_path}")
                output_buffer.append("content: |")
                
                # Indent content by 2 spaces for valid YAML
                indented_content = "\n".join(["  " + line for line in content.splitlines()])
                output_buffer.append(indented_content)
                output_buffer.append("\n---\n")
                
                file_count += 1
                total_chars += len(content)
                
            except Exception as e:
                sys.stderr.write(f"Skipping {rel_path}: {e}\n")

    # 3. Output to STDOUT
    print("\n".join(output_buffer))

    # 4. Metrics to STDERR
    est_tokens = total_chars // 4
    sys.stderr.write(f"\n[Audit Ready] Scanned {file_count} files.\n")
    sys.stderr.write(f"[Audit Ready] Approx Tokens: {est_tokens}\n")
    
    if est_tokens > TOKEN_WARNING_THRESHOLD:
        sys.stderr.write(f"WARNING: Output exceeds {TOKEN_WARNING_THRESHOLD} tokens.\n")

if __name__ == "__main__":
    run()