import os
import pytest
from ctx.main import run
import sys
from io import StringIO

@pytest.fixture
def capture_output(capsys):
    def _runner(args):
        sys.argv = ["ctx"] + args
        try:
            run()
        except SystemExit:
            pass 
        return capsys.readouterr()
    return _runner

def test_basic_output_structure(tmp_path, capture_output):
    p = tmp_path / "hello.py"
    p.write_text("print('hello')", encoding="utf-8")
    out, err = capture_output([str(tmp_path)])
    assert "path: hello.py" in out

def test_gitignore_respect(tmp_path, capture_output):
    (tmp_path / ".gitignore").write_text("secret.txt", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("I am seen", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("I am hidden", encoding="utf-8")
    out, err = capture_output([str(tmp_path)])
    assert "path: visible.txt" in out
    assert "path: secret.txt" not in out

def test_ctxignore_respect(tmp_path, capture_output):
    """Test that .ctxignore works alongside .gitignore"""
    # .gitignore hides git_secret.txt
    (tmp_path / ".gitignore").write_text("git_secret.txt", encoding="utf-8")
    # .ctxignore hides llm_noise.txt
    (tmp_path / ".ctxignore").write_text("llm_noise.txt", encoding="utf-8")
    
    (tmp_path / "git_secret.txt").write_text("x", encoding="utf-8")
    (tmp_path / "llm_noise.txt").write_text("y", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("z", encoding="utf-8")
    
    out, err = capture_output([str(tmp_path)])
    
    assert "path: visible.txt" in out
    assert "path: git_secret.txt" not in out
    assert "path: llm_noise.txt" not in out

def test_c_tracing(tmp_path, capture_output):
    (tmp_path / "main.c").write_text('#include "header.h"\nint main(){}', encoding="utf-8")
    (tmp_path / "header.h").write_text('void helper();', encoding="utf-8")
    (tmp_path / "unused.h").write_text('void nothing();', encoding="utf-8")
    target_file = str(tmp_path / "main.c")
    out, err = capture_output([target_file, "--deep"])
    assert "path: main.c" in out
    assert "path: header.h" in out
    assert "path: unused.h" not in out

def test_c_circular_tracing(tmp_path, capture_output):
    (tmp_path / "a.h").write_text('#include "b.h"', encoding="utf-8")
    (tmp_path / "b.h").write_text('#include "a.h"', encoding="utf-8")
    target_file = str(tmp_path / "a.h")
    out, err = capture_output([target_file, "--deep"])
    assert "path: a.h" in out
    assert "path: b.h" in out
    assert out.count("path: a.h") == 1

def test_missing_include(tmp_path, capture_output):
    (tmp_path / "broken.c").write_text('#include "ghost_file.h"', encoding="utf-8")
    target_file = str(tmp_path / "broken.c")
    out, err = capture_output([target_file, "--deep"])
    assert "path: broken.c" in out
    assert "path: ghost_file.h" not in out

def test_binary_skipping(tmp_path, capture_output):
    bin_file = tmp_path / "data.bin"
    with open(bin_file, "wb") as f:
        f.write(b'\x00\x01\x02')
    out, err = capture_output([str(tmp_path)])
    assert "path: data.bin" not in out

def test_doc_flag(capture_output):
    out, err = capture_output(["--doc"])
    assert "ctx: LLM Context Generator" in out