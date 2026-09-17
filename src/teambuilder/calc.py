
import json
import re
import subprocess
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CALC_JS = ROOT / "calc.js"

# Champions. calc.js documents why 0 is the Champions generation.
DEFAULT_GEN = 0

# One node process dumps every move's category, which beats paying for a
# process per lookup. Printed as {move id: "Physical" | "Special" | "Status"},
# with null for the entries (Z-moves, Max moves) that carry no category.
_CATEGORY_DUMP = """
const {Generations} = require('@smogon/calc');
const gen = Generations.get(Number(process.argv[1]));
const categories = {};
for (const move of gen.moves) categories[move.id] = move.category || null;
console.log(JSON.stringify(categories));
"""


class CalcError(RuntimeError):
    """A request the calculator refused, or a node process that failed."""


def move_category(move: str, gen: int = DEFAULT_GEN) -> str | None:
    """"Physical", "Special", "Status", or None if the move is not in `gen`.

    None means the move exists in champout but not in this generation's data
    (or is a Z/Max entry with no category), so it is worth distinguishing from
    "Status" rather than treating every unknown as a non-attacking move.
    """
    return _categories(gen).get(_to_id(move))


def calculate(request: dict | list[dict]) -> dict | list[dict]:
    """Run one request, or a list of them in a single node process.

    A list returns a list of responses in the same order, errors included as
    `{"error": ...}` entries so one bad request does not lose the batch. A
    single request returns a single response, and raises CalcError instead.
    """
    batch = request if isinstance(request, list) else [request]
    stdout = _node([str(CALC_JS)], "\n".join(json.dumps(r) for r in batch))
    responses = [json.loads(line) for line in stdout.splitlines() if line.strip()]

    if isinstance(request, list):
        return responses
    if "error" in responses[0]:
        raise CalcError(responses[0]["error"])
    return responses[0]


# Champout names 42 species the calculator does not have, and every one of them
# resolves cleanly - each mapping below was checked by comparing base stats.
#
# The cosmetic families are one species to the calculator: Furfrou's nine trims,
# Vivillon's eighteen patterns, Florges' flower colours, Alcremie's creams and
# swirls, and Maushold's Family of Four all share their base form's stats.
COSMETIC_FORMS = ("Furfrou", "Vivillon", "Florges", "Alcremie", "Maushold")

# These two are not missing, only named differently. Gourgeist-Jumbo is
# 85/100/122/58/75/54, which is the calculator's Gourgeist-Super, and champout's
# bare Aegislash is 60/50/140/50/140/60, its Shield forme - the one it stands in
# until it attacks. Ask for Aegislash-Blade explicitly if you want that side.
RENAMED = {"Gourgeist-Jumbo": "Gourgeist-Super", "Aegislash": "Aegislash-Shield"}


def species(name: str) -> str:
    """The calculator's name for a champout species.

    Applied to both sides of every request, so the rest of the code can keep
    using champout's names throughout. A response describes whoever was
    calculated, so a Furfrou-Star request comes back talking about Furfrou.
    """
    if name in RENAMED:
        return RENAMED[name]
    for base in COSMETIC_FORMS:
        if name.startswith(base):
            return base
    return name


def build_request(
    attacker: str,
    move: str,
    defender: str,
    *,
    attacker_evs: dict | None = None,
    defender_evs: dict | None = None,
    attacker_opts: dict | None = None,
    defender_opts: dict | None = None,
    move_opts: dict | None = None,
    field_opts: dict | None = None,
    gen: int = DEFAULT_GEN,
    request_id=None,
) -> dict:
    """Assemble one calculate() request.
    The `*_opts` dicts are merged over the defaults, so passing
    `field_opts={"gameType": "Singles"}` overrides the gameType below, and
    `attacker_opts={"evs": ...}` overrides attacker_evs.
    """
    request = {
        "gen": gen,
        "attacker": {
            "name": species(attacker),
            "opts": {"evs": attacker_evs or {}, **(attacker_opts or {})},
        },
        "defender": {
            "name": species(defender),
            "opts": {"evs": defender_evs or {}, **(defender_opts or {})},
        },
        "move": {"name": move, **(move_opts or {})},
        # Champions is played in doubles.
        "field": {"gameType": "Doubles", **(field_opts or {})},
    }
    # Only worth sending when there is one: calc.js echoes it back, which is
    # how a response is matched to its request in a batch.
    if request_id is not None:
        request["id"] = request_id
    return request


@cache
def _categories(gen: int) -> dict[str, str | None]:
    return json.loads(_node(["-e", _CATEGORY_DUMP, str(gen)]))


def _node(args: list[str], stdin: str = "") -> str:
    # cwd is the project root so node resolves @smogon/calc from node_modules.
    # calc.js keeps stdout to one JSON response per line - failures included -
    # and pushes the library's own chatter to stderr, so stderr only matters
    # when nothing came back at all.
    process = subprocess.run(
        ["node", *args], input=stdin, capture_output=True, text=True, cwd=ROOT
    )
    if not process.stdout.strip():
        raise CalcError(process.stderr.strip() or "node produced no output")
    return process.stdout


def _to_id(name: str) -> str:
    # The library keys its data by id: "Grassy Glide" is grassyglide, and
    # "Farfetch'd" (with either apostrophe) is farfetchd.
    return re.sub(r"[^a-z0-9]+", "", name.lower())
