{
  description = "Bug study utilities";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };

    llm-agents-nix.url = "github:numtide/llm-agents.nix";
  };

  outputs =
    {
      nixpkgs,
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
      llm-agents-nix,
      ...
    }:
    let
      inherit (nixpkgs) lib;
      forAllSystems = lib.genAttrs lib.systems.flakeExposed;

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };

      editableOverlay = workspace.mkEditablePyprojectOverlay {
        root = "$REPO_ROOT";
      };

      pyprojectOverrides = _self: _super: { };

      pythonSets = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python3;
        in
        (pkgs.callPackage pyproject-nix.build.packages { inherit python; }).overrideScope (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.default
            overlay
            pyprojectOverrides
          ]
        )
      );

      devDeps = workspace.deps.all // { bug-study-utils = [ "dev" ]; };

      mkApp = system: name: description: {
        type = "app";
        program = "${pythonSets.${system}.mkVirtualEnv "${name}-env" { ${name} = [ ]; }}/bin/${name}";
        meta.description = description;
      };
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pi = llm-agents-nix.packages.${system}.pi;
          bugClassifierEnv =
            pythonSets.${system}.mkVirtualEnv "bug-classifier-env" { bug-classifier = [ ]; };
          bugClassifierWrapped = pkgs.writeShellScriptBin "bug-classifier" ''
            export PATH="${pi}/bin:$PATH"
            exec ${bugClassifierEnv}/bin/bug-classifier "$@"
          '';
        in
        {
          scrape = pythonSets.${system}.mkVirtualEnv "scrape-env" { scrape = [ ]; };
          bug-classifier = bugClassifierEnv;
          bug-classifier-full = bugClassifierWrapped;
          analyze-csv = pythonSets.${system}.mkVirtualEnv "analyze-csv-env" { analyze-csv = [ ]; };
          analyze-diff = pythonSets.${system}.mkVirtualEnv "analyze-diff-env" { analyze-diff = [ ]; };
          analyze-results = pythonSets.${system}.mkVirtualEnv "analyze-results-env" {
            analyze-results = [ ];
          };
          word-count = pythonSets.${system}.mkVirtualEnv "word-count-env" { word-count = [ ]; };
          default = pythonSets.${system}.mkVirtualEnv "bug-study-env" workspace.deps.default;
        });

      apps = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pi = llm-agents-nix.packages.${system}.pi;
          bugClassifierEnv =
            pythonSets.${system}.mkVirtualEnv "bug-classifier-env" { bug-classifier = [ ]; };
          # Wrap the bug-classifier binary so that `pi` is always on PATH,
          # even for users who have not installed it via their own nix config.
          bugClassifierWrapped = pkgs.writeShellScriptBin "bug-classifier" ''
            export PATH="${pi}/bin:$PATH"
            exec ${bugClassifierEnv}/bin/bug-classifier "$@"
          '';
        in
        {
          scrape = mkApp system "scrape" "Scrape bug reports from GitHub, GitLab, or mailing lists";
          bug-classifier = {
            type = "app";
            program = "${bugClassifierEnv}/bin/bug-classifier";
            meta.description = "Classify bugs using zero-shot or LLMs (local backends only)";
          };
          bug-classifier-full = {
            type = "app";
            program = "${bugClassifierWrapped}/bin/bug-classifier";
            meta.description = "Classify bugs with all backends including pi";
          };
          analyze-csv = mkApp system "analyze-csv" "Summarize classifier output as category counts";
          analyze-diff = mkApp system "analyze-diff" "Diff two classifier runs to find category changes";
          analyze-results = mkApp system "analyze-results" "Check known bugs against classification";
          word-count = mkApp system "word-count" "Report word count statistics for bug report files";
        });

      checks = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          testEnv = pythonSets.${system}.mkVirtualEnv "bug-study-test-env" devDeps;
        in
        {
          pytest = pkgs.runCommand "pytest" { } ''
            cd ${./.}
            ${testEnv}/bin/pytest tests/ -v
            touch $out
          '';
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          # Every workspace package uses hatchling, which requires `editables`
          # at build time for editable installs.  It is not a runtime dep so it
          # never appears in uv.lock; resolve it via resolveBuildSystem so it
          # lands in each package's nativeBuildInputs.
          pyprojectOverridesEditable = self: super:
            lib.genAttrs [
              "bug-study-utils"
              "buglib"
              "scrape"
              "bug-classifier"
              "analyze-csv"
              "analyze-diff"
              "analyze-results"
              "word-count"
            ] (name:
              super.${name}.overrideAttrs (old: {
                nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++
                  self.resolveBuildSystem { editables = [ ]; };
              })
            );
          pythonSet = pythonSets.${system}.overrideScope (
            lib.composeManyExtensions [
              editableOverlay
              pyprojectOverridesEditable
            ]
          );
          virtualenv = pythonSet.mkVirtualEnv "bug-study-dev-env" devDeps;
        in
        let
          commonShell = {
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = pythonSet.python.interpreter;
              UV_PYTHON_DOWNLOADS = "never";
            };
            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
              export BUG_STUDY_DEV=1
            '';
          };
        in
        {
          default = pkgs.mkShell (commonShell // {
            packages = [
              virtualenv
              pkgs.uv
            ];
          });

          full = pkgs.mkShell (commonShell // {
            packages = [
              virtualenv
              pkgs.uv
              llm-agents-nix.packages.${system}.pi
            ];
          });
        }
      );
    };
}
