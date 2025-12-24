{
  description = "ctx: LLM Context Generator";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;
        
        ctx-app = python.pkgs.buildPythonApplication {
          pname = "ctx-tool";
          version = "0.1.0";
          src = ./.;
          format = "pyproject";
          
          # Build dependencies
          nativeBuildInputs = [ python.pkgs.setuptools python.pkgs.wheel ];
          propagatedBuildInputs = [ python.pkgs.pathspec ];

          # --- TEST CONFIGURATION ---
          # 1. Add pytest to the check inputs
          nativeCheckInputs = [ python.pkgs.pytest ];
          
          # 2. Run pytest in the check phase (ensures reliability before build)
          checkPhase = ''
            pytest tests/
          '';

          # Metadata to help Nix find the binary
          meta.mainProgram = "ctx"; 
        };
      in
      {
        packages.default = ctx-app;

        apps.default = flake-utils.lib.mkApp {
          drv = ctx-app;
          name = "ctx"; 
        };

        # Development shell with pytest ready
        devShells.default = pkgs.mkShell {
          packages = [ python ctx-app python.pkgs.pytest ];
        };
      }
    );
}