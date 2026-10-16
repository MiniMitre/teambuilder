{
  description = "Pokemon Champions team building: pokedex search and damage calculation";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAllSystems (pkgs:
        let
          inherit (pkgs) lib;

          # nixpkgs' default Python rather than .python-version's 3.12: only the
          # default package set is prebuilt by Hydra, and the 3.12 one compiles and
          # test-runs every package on the server, which is slow and can fail
          # there. With what pyproject.toml asks for, plus gunicorn to serve the
          # app in place of Flask's debug server.
          python = pkgs.python3.withPackages (ps: with ps; [ duckdb flask gunicorn tqdm typer ]);

          # The @smogon/calc package-lock.json pins, by the same integrity hash -
          # bump the two together. Its one dependency is @types/node, which only
          # matters to TypeScript, so the tarball alone is a working node_modules
          # entry.
          smogonCalc = pkgs.fetchurl {
            url = "https://registry.npmjs.org/@smogon/calc/-/calc-0.12.0.tgz";
            hash = "sha512-rNkdYV/ZGIugxD+hZlHdDaZLdGPYRIm+AaMFM18X2T2Pf8jpuuro9aoeiaZh51zcRR4tN3NRjSPoEXZ5ZDTuuA==";
          };

          # Only parse/ is read, as in the README's sparse clone. Bump rev (and
          # hash) for newer game data; build-db stops on anything it cannot name.
          champout = pkgs.fetchgit {
            url = "https://github.com/projectpokemon/champout.git";
            rev = "50e7233b78c3b81df29563f9695386c28e77fc95";
            sparseCheckout = [ "parse" ];
            hash = "sha256-bSU51/aTBnOfgZow25acb2XH98zs5fH64tzPd4QJP08=";
          };

          # The repository layout the code expects - calc.js, node_modules and
          # teambuilder.duckdb all sit next to src/, which ROOT is found from - laid
          # out in the store. Every runtime connection to the database is
          # read-only, so it is built here once instead of on the server.
          teambuilder = pkgs.stdenvNoCC.mkDerivation {
            pname = "teambuilder";
            version = "0.1.0";
            src = lib.fileset.toSource {
              root = ./.;
              fileset = lib.fileset.unions [ ./src ./calc.js ];
            };
            nativeBuildInputs = [ python ];
            dontConfigure = true;
            dontBuild = true;
            installPhase = ''
              runHook preInstall
              root=$out/share/teambuilder
              mkdir -p $root/node_modules/@smogon/calc $root/champout
              cp -r src calc.js $root/
              tar -xzf ${smogonCalc} -C $root/node_modules/@smogon/calc --strip-components=1
              ln -s ${champout}/parse $root/champout/parse
              PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$root/src \
                python -c 'from teambuilder.data import build; build()'
              # The dumps are only read by build(); keep them out of what runs.
              rm -r $root/champout
              runHook postInstall
            '';
          };

          # TEAMBUILDER_BIND picks the address; anything else is passed to gunicorn.
          # --timeout leaves room for a whole-roster Bulk KO, and the threads are
          # for its streaming endpoint, which holds one for the whole run. The
          # control socket goes: nothing uses it, and its default lives under
          # /run/user/<uid>, which a system service's user does not have.
          web = pkgs.writeShellApplication {
            name = "teambuilder-web";
            runtimeInputs = [ python pkgs.nodejs-slim ];
            text = ''
              export PYTHONPATH=${teambuilder}/share/teambuilder/src
              exec gunicorn --chdir ${teambuilder}/share/teambuilder \
                --bind "''${TEAMBUILDER_BIND:-127.0.0.1:8000}" \
                --workers 2 --threads 4 --timeout 120 --no-control-socket \
                "$@" teambuilder.web_server:app
            '';
          };

          cli = pkgs.writeShellApplication {
            name = "teambuilder";
            runtimeInputs = [ python pkgs.nodejs-slim ];
            text = ''
              export PYTHONPATH=${teambuilder}/share/teambuilder/src
              exec python -m teambuilder.main "$@"
            '';
          };
        in
        {
          inherit teambuilder web cli;
          default = web;
        });

      apps = forAllSystems (pkgs:
        let packages = self.packages.${pkgs.stdenv.hostPlatform.system}; in
        {
          default = {
            type = "app";
            program = "${packages.web}/bin/teambuilder-web";
            meta.description = "Serve the web app with gunicorn on TEAMBUILDER_BIND (127.0.0.1:8000)";
          };
          cli = {
            type = "app";
            program = "${packages.cli}/bin/teambuilder";
            meta.description = "The teambuilder command line: find, ko, survive, calc";
          };
        });
    };
}
