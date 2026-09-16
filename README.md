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
