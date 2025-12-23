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
          
          nativeBuildInputs = [ python.pkgs.setuptools python.pkgs.wheel ];
          propagatedBuildInputs = [ python.pkgs.pathspec ];

          # --- FIX IS HERE ---
          # Tell Nix the actual binary name is 'ctx', not 'ctx-tool'
          meta.mainProgram = "ctx"; 
        };
      in
      {
        packages.default = ctx-app;

        apps.default = flake-utils.lib.mkApp {
          drv = ctx-app;
          # --- OPTIONAL SAFETY ---
          # Explicitly pointing to the binary name helps flake-utils too
          name = "ctx"; 
        };

        devShells.default = pkgs.mkShell {
          packages = [ python ctx-app ];
        };
      }
    );
}