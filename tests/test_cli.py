import os
import pytest
from ctx.main import run
import sys
from io import StringIO

# --- Helper to capture stdout/stderr ---
@pytest.fixture
def capture_output(capsys):
    """Runs a function and captures stdout/stderr."""
    def _runner(args):
        # Mock sys.argv
        sys.argv = ["ctx"] + args
        try:
            run()
        except SystemExit:
            pass # Handle exit(1) gracefully
        return capsys.readouterr()
    return _runner

def test_basic_output_structure(tmp_path, capture_output):
    """Test that valid files appear in the YAML output."""
    p = tmp_path / "hello.py"
    p.write_text("print('hello')", encoding="utf-8")
    
    out, err = capture_output([str(tmp_path)])
    
    assert "# Project Audit:" in out
    assert "path: hello.py" in out
    assert "print('hello')" in out

def test_gitignore_respect(tmp_path, capture_output):
    """Test that ignored files are NOT in the output."""
    (tmp_path / ".gitignore").write_text("secret.txt", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("I am seen", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("I am hidden", encoding="utf-8")
    
    out, err = capture_output([str(tmp_path)])
    
    assert "path: visible.txt" in out
    assert "path: secret.txt" not in out

def test_c_tracing(tmp_path, capture_output):
    """Test the --deep flag for C includes."""
    (tmp_path / "main.c").write_text('#include "header.h"\nint main(){}', encoding="utf-8")
    (tmp_path / "header.h").write_text('void helper();', encoding="utf-8")
    (tmp_path / "unused.h").write_text('void nothing();', encoding="utf-8")
    
    target_file = str(tmp_path / "main.c")
    out, err = capture_output([target_file, "--deep"])
    
    assert "path: main.c" in out
    assert "path: header.h" in out
    assert "path: unused.h" not in out

def test_c_circular_tracing(tmp_path, capture_output):
    """Test that circular dependencies (A -> B -> A) do not cause an infinite loop."""
    # A includes B
    (tmp_path / "a.h").write_text('#include "b.h"', encoding="utf-8")
    # B includes A
    (tmp_path / "b.h").write_text('#include "a.h"', encoding="utf-8")
    
    target_file = str(tmp_path / "a.h")
    # This should finish instantly. If it hangs, the test fails.
    out, err = capture_output([target_file, "--deep"])
    
    assert "path: a.h" in out
    assert "path: b.h" in out
    # Ensure each appears only once
    assert out.count("path: a.h") == 1
    assert out.count("path: b.h") == 1

def test_missing_include(tmp_path, capture_output):
    """Test that a missing include file doesn't crash the tool."""
    (tmp_path / "broken.c").write_text('#include "ghost_file.h"', encoding="utf-8")
    
    target_file = str(tmp_path / "broken.c")
    out, err = capture_output([target_file, "--deep"])
    
    assert "path: broken.c" in out
    # ghost_file.h obviously shouldn't be there, and it shouldn't crash
    assert "path: ghost_file.h" not in out

def test_binary_skipping(tmp_path, capture_output):
    """Ensure binary files are skipped automatically."""
    bin_file = tmp_path / "data.bin"
    with open(bin_file, "wb") as f:
        f.write(b'\x00\x01\x02')
        
    out, err = capture_output([str(tmp_path)])
    assert "path: data.bin" not in out