# teambuilder

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
