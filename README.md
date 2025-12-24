# ctx: LLM Context Generator

**ctx** is a specialized CLI tool designed to bridge the gap between your codebase and Large Language Models (LLMs) like Claude, GPT-4, and Gemini. 

It packages your code into a **Multi-Document YAML** format that is token-efficient, explicitly structured, and optimized for "Auditor" workflows (e.g., asking an AI to review an Aider session).

## Features

- **Context-Aware Output:** GGenerates a file tree map at the top of the output to ground the LLM.
- **Dependency Tracing:** Can heuristically follow C/C++ `#include` directives to bundle related headers automatically.
- **Smart Filtering:** Strictly obeys `.gitignore` and automatically excludes lockfiles/binaries to save context window.
- **Token Estimation:** Prints token usage to `stderr` so you know if you fit in the context window.
- **Pipe-Friendly:** Outputs to `stdout` by default for seamless integration with `pbcopy` or `clip`.

## Installation

### Option 1: Via Nix (Recommended)
If you have a Nix-enabled system (macOS/Linux):

```bash
# Run directly without installing
nix run github:andrey-stepantsov/ctx-tool -- .

# Install into your profile
nix profile install github:andrey-stepantsov/ctx-tool
```

### Option 2: Via pipx (Universal)
Works on any system with Python 3.8+:

```bash
# Install from local source
pipx install .

# Or install from git
pipx install git+https://github.com/andrey-stepantsov/ctx-tool.git
```

## Usage

### 1. The "Project Audit" (Default)
Bundles the entire current directory (recursive), respecting `.gitignore`.

```bash
ctx . | pbcopy
```
*Paste the result into your LLM prompt: "Review this architecture..."*

### 2. The "Focused Trace" (C/C++)
Bundles specific files and automatically finds their local headers (`#include "..."`).

```bash
# Traces main.c, finds 'utils.h', bundles both.
ctx src/main.c --deep | pbcopy
```

### 3. Mixed Mode
You can combine explicit files and directories.

```bash
ctx src/main.c src/experimental/ --deep
```

## Output Format

The tool produces a single YAML stream designed for machine reading:

```yaml
# Project Audit: my-project
# Context Map:
project_structure: |
  src/
    main.c
    utils.h

---
path: src/main.c
content: |
  #include "utils.h"
  int main() { ... }
---
path: src/utils.h
content: |
  void helper();
```

## Comparison with Repomix

**[Repomix](https://github.com/yamadashy/repomix)** is a popular Node.js tool for packing codebases. Why use `ctx` instead?

| Feature | Repomix | ctx |
| :--- | :--- | :--- |
| **Primary Output** | XML / Markdown | **Multi-Document YAML** (Optimized for LLM readability) |
| **C/C++ Support** | Blind directory walking | **Heuristic Tracing** (Follows `#include` to save tokens) |
| **Ecosystem** | Node.js / NPM | **Python / Nix** (Zero-dependency binary) |
| **Philosophy** | "Pack Everything" | "Trace & Audit" |

Use **Repomix** for generic web projects. Use **ctx** if you need surgical context for C/C++/SystemVerilog or prefer a Nix-native workflow.## Advanced Usage

### Working with External SDKs / PDKs
`ctx` is designed to provide complete context, even if dependencies live outside your project root.

1. **Relative Includes (Supported Automatically):**
   If your code uses relative paths to reach a sibling directory (common in hardware design or monorepos), `ctx` will resolve, bundle, and correctly label them.
   
   *Source:* `#include "../pdk/std_defs.h"`
   *Output:* ```yaml
   path: ../pdk/std_defs.h
   content: |
     ...
   ```

2. **Explicit External Files:**
   If you have a critical header in a global location that isn't referenced relatively, you can explicitly add it to the bundle.
   
   ```bash
   ctx src/main.c /opt/sdk/critical_def.h --deep
   ```

