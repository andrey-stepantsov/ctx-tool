# Maintainer Guide

This document outlines the release process for `ctx-tool`.

## 1. Update Version Numbers

You must manually update the version string in **three** locations to ensure consistency between Python and Nix.

1.  **`pyproject.toml`**:
    '''toml
    [project]
    version = "0.2.0"  # <--- Update this
    '''

2.  **`src/ctx/__init__.py`**:
    '''python
    __version__ = "0.2.0"  # <--- Update this
    '''

3.  **`flake.nix`**:
    '''nix
    ctx-app = python.pkgs.buildPythonApplication {
      pname = "ctx-tool";
      version = "0.2.0";  # <--- Update this
      # ...
    '''

## 2. Verify Build & Tests

Before committing, ensure the Nix build succeeds and tests pass.

```bash
# This runs the pytest suite defined in the checkPhase
nix flake check
```

## 3. Tagging & Releasing

Once the version numbers are updated and tests pass, run the following sequence:

```bash
# 1. Stage the version changes
git add pyproject.toml src/ctx/__init__.py flake.nix

# 2. Commit (Conventional Commits style)
git commit -m "chore: bump version to 0.2.0"

# 3. Create an annotated tag
# Note: It is standard to use 'v' prefix for tags, but not inside the files.
git tag -a v0.2.0 -m "Release v0.2.0"

# 4. Push commit and tags to GitHub
git push origin main
git push origin v0.2.0
```

## 4. Post-Release Verification

After pushing, users can run the new version immediately via Nix:

```bash
nix run github:andrey-stepantsov/ctx-tool/v0.2.0 -- --help
```