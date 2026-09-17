# teambuilder

## On the use of AI

Claude was used in building this, mostly on the glue code between
[@smogon/calc](https://github.com/smogon/damage-calc) and the code here: the
node wrapper, the subprocess plumbing, and the parsing of the data dumps.
This is not a tool that was prompted into existence and shipped unread. Human
eyes were on every part of it - the design decisions, the data model, and the
output - and the parts that matter were checked against the calculator and the
game data rather than taken on trust. If you find something wrong anyway, that
is on the humans, and an issue is welcome.

## What this is

A search tool for Pokemon Champions, and a small damage calculator built on
top of it. It answers the two questions that come up while building a team and
that nothing else quite answers together:

- **Which pokemon fit these criteria?** Filter the roster by type, ability,
  learnset and any stat - `atk`, `spe`, `bst` and the rest - combining
  conditions freely with and/or/not.
- **How many stat points does this actually take?** Find the fewest points
  needed to guarantee a KO, or to survive a hit - and not just live-or-die,
  but any threshold: deal at least 85% of the target's HP, or stay under 40%
  of your own.

The idea is a one stop shop for the pieces that are missing when you sit down
to build: the roster is searchable, the damage numbers come from the real
calculator, and the two can be scripted together from Python.

**The search and the calculator are not integrated yet.** You can find
pokemon, and you can calculate for pokemon, but you cannot yet ask "which
grass types can guarantee an OHKO on this defender". That is the obvious next
step and it is not done.

## Usage

Requires - [UV (Python Project Manager)](https://docs.astral.sh/uv/) to be installed.

Set up the data and the calculator first - see the two sections [Getting the champout data](Getting the champout data)and [Getting the damage calculator](Getting the damage calculator) below, which are the parts that need cloning - then:

```bash
uv run teambuilder build-db                 # parse the dumps into DuckDB

uv run teambuilder find --type Grass --min atk=90 --between bst=400:600 \
                        --learns "Swords Dance" --ability Chlorophyll --ability Overgrow

uv run teambuilder ko Blaziken "Close Combat" Incineroar --defender-evs '{"def": 12}'
uv run teambuilder survive Rillaboom "Wood Hammer" Snorlax \
                           --attacker-evs '{"atk": 32}' --percent 70

uv run teambuilder calc Rillaboom "Grassy Glide" Snorlax \
                        --attacker-opts '{"nature": "Adamant"}' --field-opts '{"terrain": "Grassy"}'
uv run teambuilder category "Grassy Glide"  # Physical, Special or Status
```

Types, moves and stat bounds are ANDed together; repeated `--ability` options
are ORed, since a pokemon only has one at a time. `--help` on any command
lists the rest.

For anything the flags cannot express, `teambuilder raw` takes newline-
delimited calculator requests on stdin and prints one JSON response per line.
Everything the CLI does is a thin wrapper over `teambuilder.search` and
`teambuilder.calc`, so the Python API is the better surface for a loop.

## Known caveats

**Body Press and Psyshock cannot be sized up.** The point search picks which
stat to invest in from the move's category, so moves that attack off a
different stat than their category implies - Body Press is Physical but uses
Def, Psyshock is Special but targets Def - will pour points into a stat that
does nothing and report that no spread works. Their damage is still calculated
correctly; it is only the "how many points" search that cannot handle them.

**Everything about the battle state has to be in the request.** A calculation
with no options is a bare level-50 pokemon: neutral nature, no item, no
ability that needs turning on, no boosts, no weather, no terrain, no screens.
Sun does not happen because the attacker has Drought - you pass
`--field-opts '{"weather": "Sun"}'`. The same goes for natures, items,
abilities, boosts, Helping Hand, Reflect and the rest. The option names are
the calculator's own, which is the Showdown vocabulary, and it is fair to say
this is not obvious if you have not used the Smogon calculator before. The
full option list is in the [damage calculator](#getting-the-damage-calculator)
section below.

What you do _not_ have to specify is anything intrinsic to the move itself:
always-crit moves such as Flower Trick already crit, multi-hit moves already
roll their hits, and spread damage follows from the game type.

**The roster is Champions only.** Both the pokedex and the calculator use the
Champions data, so a pokemon that is not in the game is not here either -
asking for Urshifu gets you `unknown species: Urshifu`, not a guess.

## Contributing

Contributions are open, and issues pointing at wrong numbers are especially
welcome - a damage calculation that is quietly off is worse than one that
errors.

LLM-assisted contributions are welcome too. What is asked in return is that
some human work and verification went into it: that you ran the thing, that
you checked the numbers against the calculator, and that you can explain what
the change does and why. A pull request that its author has not read is not a
contribution, it is a review request with extra steps.

## Next steps and contribution suggestions

Roughly in order of how achievable they are.

**Damage filters in the search.** The obvious missing piece: `can_ko(move,
defender)` and `survives(attacker, move)` as filters, so a search can ask for
grass types that guarantee an OHKO on something. This one cannot be a SQL
fragment like the others - it has to run the candidates from the SQL result
through the calculator - but the batching makes that cheap: the whole roster
is 396 requests in one node process, a fraction of a second.

**Type matchup filters.** Give it a pokemon, or a team, and ask for coverage:
"shares no weakness with these five", or "can hit this super effectively",
either by its own types or by the moves it actually learns. The type chart is
already in the calculator's data (`calc/src/data/types.ts`), so it does not
need rebuilding, and `move_category` tells you which of a pokemon's moves can
use a given type offensively.

The part that needs care is abilities. Levitate, Flash Fire, Water Absorb,
Volt Absorb, Motor Drive, Sap Sipper, Lightning Rod, Storm Drain and Dry Skin
cancel a type outright; Thick Fat and Heatproof only halve it. A weakness
filter that ignores those will confidently recommend pokemon that are not
weak to the thing at all.

**A repository of common sets.** The Smogon calculator has its set dropdown,
and the same data exists for Champions: `src/js/data/sets/champions.js` in the
damage-calc checkout, a `SETDEX_CHAMPIONS` object of about 85KB, keyed by
species and then by set name, with level, ability, item, nature, moves and
stat points. Importing it into DuckDB would mean searching and calculating
against sets people actually run, rather than bare stat lines. One wrinkle:
its spreads use short keys (`hp`, `at`, `df`, `sa`, `sd`, `sp`) under `sps`,
so they need mapping to the calculator's `evs` names.

**A frontend.** It would be nice. The author is not going to build one - this
is a command line tool by preference, not by accident - so it is wide open to
anyone who wants it.

Smaller, self-contained jobs:

- Import move metadata (type, category, base power) into DuckDB, so a filter
  can ask for "learns a physical grass move of at least 90 base power" instead
  of naming moves one at a time.
- Special-case Body Press and Psyshock in `attacking_stat` so the point search
  works for them - see the caveats above.
- Reconcile names between the champout dumps and the calculator's data. They
  mostly agree, but not entirely: the dumps carry moves the calculator does
  not have, and apostrophes and form suffixes are an obvious place for a
  silent mismatch.
- A speed benchmark helper, in the shape of the existing two: the fewest stat
  points needed to outspeed a given pokemon.

If you have an idea that is not here, open an issue - the list above is what
one person could see from inside the problem, which is not the same as what
the tool needs.

## License

[MIT](LICENSE), Copyright (c) 2026 Mateo Puente.

## Getting the champout data

The learnset/moveset data comes from the `parse/` folder of the
[champout](https://github.com/projectpokemon/champout) repository. Only that
folder is needed, so the repo is cloned with a blob-less, sparse checkout
instead of pulling everything down.

```bash
git clone --filter=blob:none --no-checkout git@github.com:projectpokemon/champout.git
cd champout
git sparse-checkout init --cone
git sparse-checkout set parse
git checkout main
```

What each step does:

- `--filter=blob:none` fetches the commit and tree objects but no file
  contents; blobs are downloaded lazily, only for the files actually checked
  out.
- `--no-checkout` skips populating the working tree, so nothing is written
  before the sparse rules are set.
- `sparse-checkout init --cone` turns on sparse checkout in cone mode, which
  matches whole directories rather than arbitrary gitignore-style patterns.
- `sparse-checkout set parse` limits the working tree to the repository root
  files plus `parse/`.
- `git checkout main` finally materialises the working tree — this is where
  the blobs for `parse/` (and the root files) are fetched.

The result is `champout/parse/` containing:

- `move_availability.txt`
- `personal_dump.txt`
- `species_with_move.txt`

`champout/` is a separate git repository and is not tracked here — re-run the
commands above to obtain it on a fresh clone.

## Getting the damage calculator

Damage calculation goes through [`calc.js`](calc.js), which wraps
[@smogon/calc](https://github.com/smogon/damage-calc). **Pokémon Champions is
generation 0** in that library: `calc/src/calc.ts` dispatches on
`MECHANICS[gen.num]` and slot 0 is `calculateChampions`, ahead of RBY at 1.

That only exists on `master`. The published npm package (0.11.0, the latest as
of September 2026) declares `GenerationNum` as `1 | ... | 9`, ships no
`champions.ts`, and never mentions Champions — asking it for gen 0 runs RBY
mechanics against data that isn't there and dies with `Cannot read properties
of undefined (reading 'hp')`. So the library is built from source.

npm cannot install a subdirectory of a repository, and the package lives in
`calc/` of a monorepo, so the checkout is sparse like champout's and the build
is run by hand:

```bash
git clone --filter=blob:none --no-checkout https://github.com/smogon/damage-calc.git
cd damage-calc
git sparse-checkout init --cone
git sparse-checkout set calc
git checkout e7fd7e59f3eef7ea42fba3c8b83261cb4a14109d
cd calc
npm install
npm run compile
```

That commit (`Update sets`, 2026-09-11) is the one this project is built
against. Champions support is unreleased and still moving, so `master` may
have changed the mechanics or the roster by the time you read this - check out
`master` instead if you want the newer behaviour, and update the SHA here once
the calcs still look right.

Then, from the project root, point the dependency at that checkout:

```bash
npm install ./damage-calc/calc
```

which writes `"@smogon/calc": "file:damage-calc/calc"` into `package.json` and
symlinks `node_modules/@smogon/calc` at the build.

Notes on the build:

- `npm run compile` (`tsc -p .`) is the whole build for our purposes: it
  produces `dist/`, which is what `require('@smogon/calc')` loads.
- `npm run build` additionally runs `npm run bundle`, which fails here — it
  reaches up to the repository root for a bundler that the sparse checkout
  leaves uninstalled. It only produces the browser bundle, so the failure does
  not matter. `npm install` reports the same failure for the same reason,
  through the package's `prepare` script, after it has installed and compiled.

`damage-calc/` is a separate git repository and is not tracked here — re-run
the commands above on a fresh clone.

### Running calcs

`calc.js` reads newline-delimited JSON on stdin and writes one JSON response
per line to stdout, in the same order, so a whole batch runs in one node
process instead of paying ~50ms of startup per calc:

```bash
printf '%s\n' "$REQUEST_ONE" "$REQUEST_TWO" | node calc.js
```

A single request on its own line is just the one-line case. Give a request an
`"id"` and it comes back on the response - including on an error - which is
how a response is matched to its request without relying on ordering. A line
that fails reports its own error and the rest still run; the exit code is 1 if
any line failed.

The request shape is documented at the top of [`calc.js`](calc.js).

### Stat points, not EVs

Champions replaced EVs with stat points, 0-32 per stat, and the calculator
models that inside the generation rather than through a new field: at gen 0 it
reads `evs` as stat points and uses them directly
(`calc/src/stats.ts`, `calcStatChampions`).

```
hp    = base + sp + 75
other = floor(nature * (base + sp + 20))
```

So pass the stat point value as-is. There is no `EV = 8 * sp - 4` conversion
to do, and doing it anyway would be far out of range: nothing in the library
clamps the number, and 252 "stat points" quietly yields a 436 Atk Rillaboom.
`calc.js` rejects anything outside 0-32 for gen 0 for that reason.

Two related things gen 0 ignores outright: `level` (`pokemon.ts` forces 50)
and `ivs` (forced to 31). Natures still apply their usual ±10%.
