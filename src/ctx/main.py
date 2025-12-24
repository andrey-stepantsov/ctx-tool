import os
import sys
import argparse
import pathspec
import re

# --- CONFIGURATION ---
TOKEN_WARNING_THRESHOLD = 100000 
DEFAULT_IGNORES = [
    ".git/", ".aider*", ".env", "__pycache__/", "*.pyc", 
    "node_modules/", "dist/", "build/", ".DS_Store",
    ".venv", "venv", "*.egg-info", "target/",
    "flake.lock", "package-lock.json", "yarn.lock", "poetry.lock", "Cargo.lock"
]

# Regex for heuristic C/C++ includes: #include "file.h"
# We deliberately ignore <system_headers> to save tokens.
INCLUDE_PATTERN = re.compile(r'^\s*#include\s+"([^"]+)"')

def load_gitignore(root_dir):
    """Loads .gitignore patterns and adds internal defaults."""
    gitignore_path = os.path.join(root_dir, ".gitignore")
    lines = []
    
    # Read user's .gitignore
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            sys.stderr.write(f"Warning: Could not read .gitignore: {e}\n")
    
    lines.extend(DEFAULT_IGNORES)
    return pathspec.PathSpec.from_lines('gitwildmatch', lines)

def is_text_file(filepath):
    """Checks if file is text by looking for null bytes in the first 1kb."""
    try:
        if not os.path.isfile(filepath):
            return False
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
        return b'\x00' not in chunk
    except Exception:
        return False

def resolve_include(include_path, current_file_path, root_dir):
    """
    Resolves an #include path. 
    1. Checks relative to the current file.
    2. Checks relative to the project root.
    """
    current_dir = os.path.dirname(current_file_path)
    
    # 1. Check relative to current file
    candidate = os.path.normpath(os.path.join(current_dir, include_path))
    if os.path.exists(candidate):
        return candidate
        
    # 2. Check relative to root
    candidate_root = os.path.normpath(os.path.join(root_dir, include_path))
    if os.path.exists(candidate_root):
        return candidate_root
        
    return None

def scan_for_includes(content, filepath, root_dir):
    """Scans content for #include directives and returns a list of resolved paths."""
    found = []
    for line in content.splitlines():
        match = INCLUDE_PATTERN.match(line)
        if match:
            inc_rel = match.group(1)
            resolved = resolve_include(inc_rel, filepath, root_dir)
            if resolved:
                found.append(resolved)
    return found

def generate_tree_from_list(file_list, root_dir):
    """Generates a visual tree string from a flat list of absolute paths."""
    # Convert to relative paths
    rel_paths = [os.path.relpath(p, root_dir) for p in file_list]
    rel_paths.sort()
    
    if not rel_paths:
        return ""

    tree_lines = []
    # Simple hierarchy builder
    for path in rel_paths:
        parts = path.split(os.sep)
        indent = 0
        for i, part in enumerate(parts):
            # Only print the leaf (file) with full indentation
            # Directories are implied by the structure, but simpler to just list flat-ish for context
            if i == len(parts) - 1:
                tree_lines.append("  " * i + part)
            else:
                # Optional: Add directory markers if you want a fuller tree. 
                # For LLM context, a simplified list often suffices, 
                # but let's stick to the visual indentation.
                pass 
                
    # A robust tree requires building a nested dict, but for this tool, 
    # a sorted list with indentation is usually 90% as effective and cheaper on tokens.
    # Let's do a pure sorted list with indentation for visual hierarchy.
    formatted_tree = []
    for path in rel_paths:
        depth = path.count(os.sep)
        name = os.path.basename(path)
        formatted_tree.append(f"{'  ' * depth}{name}")
        
    return "\n".join(formatted_tree)

def run():
    parser = argparse.ArgumentParser(description="Pack code into LLM-ready context.")
    parser.add_argument("inputs", nargs="*", default=["."], help="Files or directories to scan")
    parser.add_argument("--deep", action="store_true", help="Recursively follow #include directives")
    args = parser.parse_args()

    # Determine root based on the first argument or cwd
    first_input = os.path.abspath(args.inputs[0])
    if os.path.isdir(first_input):
        root_dir = first_input
    else:
        root_dir = os.path.dirname(first_input)
    
    spec = load_gitignore(root_dir)
    
    # 1. Build Initial Work Queue
    queue = []
    processed_paths = set()
    final_files = [] # List of (rel_path, content) tuples

    # Populate queue
    for inp in args.inputs:
        abs_inp = os.path.abspath(inp)
        
        if os.path.isfile(abs_inp):
            queue.append(abs_inp)
        elif os.path.isdir(abs_inp):
            # If dir, walk it and add all valid files
            for r, dirs, files in os.walk(abs_inp):
                # Filter dirs in-place for ignore logic
                dirs[:] = [d for d in dirs if not spec.match_file(os.path.relpath(os.path.join(r, d), root_dir))]
                
                for f in files:
                    full_path = os.path.join(r, f)
                    queue.append(full_path)

    # 2. Process Queue (BFS)
    while queue:
        current_path = queue.pop(0)
        
        if current_path in processed_paths:
            continue
            
        processed_paths.add(current_path)
        
        # Validation Checks
        rel_path = os.path.relpath(current_path, root_dir)
        
        if spec.match_file(rel_path):
            continue
        
        if not is_text_file(current_path):
            continue

        try:
            with open(current_path, "r", encoding="utf-8", errors='ignore') as f:
                content = f.read()
                
            if not content.strip():
                continue
                
            # Add to results
            final_files.append((rel_path, content))
            
            # Feature: Deep Scan
            if args.deep:
                # If it's a C/C++ file, look for includes
                if current_path.endswith(('.c', '.cpp', '.h', '.hpp', '.cc')):
                    new_includes = scan_for_includes(content, current_path, root_dir)
                    for inc in new_includes:
                        if inc not in processed_paths:
                            queue.append(inc)
                            
        except Exception as e:
            sys.stderr.write(f"Skipping {rel_path}: {e}\n")

    # 3. Output Generation
    final_files.sort(key=lambda x: x[0]) # Sort by path
    
    # Buffer output
    output_buffer = []
    project_name = os.path.basename(root_dir)
    
    output_buffer.append(f"# Project Audit: {project_name}")
    output_buffer.append("# Context Map:")
    output_buffer.append("project_structure: |")
    
    # Generate tree from the actual files we found
    files_only_list = [os.path.join(root_dir, f[0]) for f in final_files]
    tree_str = generate_tree_from_list(files_only_list, root_dir)
    indented_tree = "\n".join(["  " + line for line in tree_str.splitlines()])
    output_buffer.append(indented_tree)
    output_buffer.append("\n---\n")
    
    total_chars = 0
    
    for rel_path, content in final_files:
        output_buffer.append(f"path: {rel_path}")
        output_buffer.append("content: |")
        indented_content = "\n".join(["  " + line for line in content.splitlines()])
        output_buffer.append(indented_content)
        output_buffer.append("\n---\n")
        total_chars += len(content)

    print("\n".join(output_buffer))

    # 4. Metrics
    est_tokens = total_chars // 4
    sys.stderr.write(f"\n[Audit Ready] Scanned {len(final_files)} files.\n")
    sys.stderr.write(f"[Audit Ready] Approx Tokens: {est_tokens}\n")
    
    if est_tokens > TOKEN_WARNING_THRESHOLD:
        sys.stderr.write(f"WARNING: Output exceeds {TOKEN_WARNING_THRESHOLD} tokens.\n")

if __name__ == "__main__":
    run()