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
  };

  outputs =
    {
      nixpkgs,
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
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

      mkApp = system: name: description: {
        type = "app";
        program = "${pythonSets.${system}.mkVirtualEnv "${name}-env" { ${name} = [ ]; }}/bin/${name}";
        meta.description = description;
      };
    in
    {
      packages = forAllSystems (system: rec {
        scrape-github = pythonSets.${system}.mkVirtualEnv "scrape-github-env" { scrape-github = [ ]; };
        scrape-gitlab = pythonSets.${system}.mkVirtualEnv "scrape-gitlab-env" { scrape-gitlab = [ ]; };
        scrape-mailinglist = pythonSets.${system}.mkVirtualEnv "scrape-mailinglist-env" {
          scrape-mailinglist = [ ];
        };
        bug-classifier = pythonSets.${system}.mkVirtualEnv "bug-classifier-env" { bug-classifier = [ ]; };
        analyze-csv = pythonSets.${system}.mkVirtualEnv "analyze-csv-env" { analyze-csv = [ ]; };
        analyze-diff = pythonSets.${system}.mkVirtualEnv "analyze-diff-env" { analyze-diff = [ ]; };
        analyze-results = pythonSets.${system}.mkVirtualEnv "analyze-results-env" {
          analyze-results = [ ];
        };
        word-count = pythonSets.${system}.mkVirtualEnv "word-count-env" { word-count = [ ]; };
        default = pythonSets.${system}.mkVirtualEnv "bug-study-env" workspace.deps.default;
      });

      apps = forAllSystems (system: {
        scrape-github = mkApp system "scrape-github" "Download GitHub issues as plain text bug reports";
        scrape-gitlab = mkApp system "scrape-gitlab" "Download GitLab issues with structured metadata";
        scrape-mailinglist = mkApp system "scrape-mailinglist" "Scrape mail archives for bug reports";
        bug-classifier = mkApp system "bug-classifier" "Classify bugs using zero-shot or LLMs";
        analyze-csv = mkApp system "analyze-csv" "Summarize classifier output as category counts";
        analyze-diff = mkApp system "analyze-diff" "Diff two classifier runs to find category changes";
        analyze-results = mkApp system "analyze-results" "Check known bugs against classification";
        word-count = mkApp system "word-count" "Report word count statistics for bug report files";
      });

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonSet = pythonSets.${system}.overrideScope editableOverlay;
          virtualenv = pythonSet.mkVirtualEnv "bug-study-dev-env" workspace.deps.all;
        in
        {
          default = pkgs.mkShell {
            packages = [
              virtualenv
              pkgs.uv
            ];
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = pythonSet.python.interpreter;
              UV_PYTHON_DOWNLOADS = "never";
            };
            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
            '';
          };
        }
      );
    };
}
