from math import ceil
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from tqdm import tqdm

from teambuilder.calc import CalcError, build_request, calculate, move_category
from teambuilder.data import DB_PATH
from teambuilder.pokedex import get_abilities_for_poke, learnset, that_learn

# Champions gives each stat 0-32 points, so every search below is a scan over
# 33 candidates in one batch - ~20ms, and damage is monotonic in the invested
# stat, so the first spread that clears the bar is the cheapest one.
MAX_STAT_POINTS = 32

class Investment(NamedTuple):
    points: int
    desc: str
    percent: tuple[float, float]
    damage: tuple[int, int]
    user_hp: int
    move: str | None = None        # set when the filter picked the move, not the caller

    def __str__(self):
        with_move = f" with {self.move}" if self.move else ""
        return f"{self.points} points{with_move}: {self.desc}"
class BestAbility(NamedTuple):
    """The attacker's hardest-hitting ability, and the damage that proves it."""

    names: tuple[str, ...]
    damage: tuple[int, int]
    desc: str

    def __str__(self):
        return f"{' / '.join(self.names)}: {self.damage[0]}-{self.damage[1]}"

def attacking_stat(move: str) -> str:
    """Which stat a move attacks off, by category.

    Not reliable for the handful of moves that break the rule - Body Press is
    Physical but uses Def, Psyshock is Special but hits Def - so investing by
    category will do nothing for those. The calculator still gets their damage
    right; it is only this choice of stat to invest in that is wrong.
    """
    category = move_category(move)
    if category is None:
        raise ValueError(f"{move!r} is not in the Champions move data")
    if category == "Status":
        raise ValueError(f"{move!r} is a Status move and deals no damage")
    return "spa" if category == "Special" else "atk"


def _evaluate(requests: list[dict]):
    """Runs every request through the calculator, yielding (response, Investment) pairs.

    Shared core for _cheapest, _breakpoints, and friends: handles error
    checking and Investment construction once, so callers only decide what
    to do with each result.
    """
    for points, response in enumerate(calculate(requests)):
        if "error" in response:
            raise CalcError(response["error"])
        investment = Investment(
            points, response["desc"], tuple(response["percent"]),
            tuple(response["range"]), response["defenderMaxHP"],
        )
        yield response, investment


def _cheapest(requests: list[dict], accept) -> Investment | None:
    """First response that `accept` likes, which is the cheapest by monotonicity."""
    for response, investment in _evaluate(requests):
        if accept(response):
            return investment
    return None


def _breakpoints(requests: list[dict], key) -> list[Investment]:
    """One Investment per distinct value of `key(response)`, at the fewest points that reach it."""
    breakpoints: list[Investment] = []
    previous = object()  # sentinel: never equals a real key value, so points=0 is always recorded
    for response, investment in _evaluate(requests):
        current = key(response)
        if current != previous:
            breakpoints.append(investment)
            previous = current
    return breakpoints

def _all(requests: list[dict]) -> list[Investment]:
    """Every Investment, one per request, in order."""
    return [investment for _, investment in _evaluate(requests)]

def calculate_HP_from_Breakpoints(breakpoints:list[Investment], PERCENT, HP, INVEST_IN
):
    #Initialise the min points used at 32/32
    minPoints:int = 64
    minPairs:list[dict[str, int]] = []

    for inv in breakpoints:
        dealt = inv.damage[1]
        current_hp = inv.user_hp
        points = inv.points
        pct = PERCENT/100
        calculated_HP = (ceil((dealt-pct*current_hp)/pct))
        adjusted_HP = max(calculated_HP,0)
        total_points_used = adjusted_HP + points

        if minPoints > total_points_used:
            #Set the new best points
            minPoints = total_points_used
            #Empty the list
            minPairs.clear()
            #Add the new best combination
            minPairs.append({HP: adjusted_HP, INVEST_IN: points})

        elif minPoints == total_points_used:
            #Add an equally good combination
            minPairs.append({HP: adjusted_HP, INVEST_IN: points})

        if calculated_HP < 0:
            #We do not need to check any more values
            break
    
    return minPairs

def verify_Min_EVs (
    minPairs: list[dict[str, int]],
    attacker: str,
    move: str,
    defender: str,
    *,
    attacker_evs: dict | None = None,
    attacker_opts: dict | None = None,
    defender_evs: dict | None = None,
    defender_opts: dict | None = None,
    move_opts: dict | None = None,
    field_opts: dict | None = None):

    requests = [
    build_request(
        attacker, move, defender,
        attacker_evs=attacker_evs,
        attacker_opts=attacker_opts,
        # Points go into `invest`; any other stats the caller set stay.
        defender_evs={**(defender_evs or {}), **pair},
        defender_opts=defender_opts,
        move_opts=move_opts,
        field_opts=field_opts,
    )
    for pair in minPairs
    ] 

    return _all(requests)

def _ability_scan(attacker: str, move: str, defender: str, *, vary: str, pick, options: dict):
    """Calculate this matchup once per ability of one side, and pick an extreme.

    `vary` is "attacker" or "defender" and says whose abilities are swapped;
    `pick` is max or min over the damage range. One node process covers every
    ability, since they all go into a single batch.
    """
    subject = attacker if vary == "attacker" else defender
    key = f"{vary}_opts"
    abilities = get_abilities_for_poke(subject)

    responses = calculate([
        # A new dict per request: mutating one shared dict would also hand the
        # caller's options back with an ability glued on.
        build_request(attacker, move, defender,
                      **{**options, key: {**(options.get(key) or {}), "ability": name}})
        for name in abilities
    ])
    for response in responses:
        if "error" in response:
            raise CalcError(response["error"])

    # Rolls scale together, so comparing ranges orders the abilities the same
    # way any single roll would. Ties are every ability that matches the
    # extreme, which is the common case: usually none of them touch this move.
    damage = pick(tuple(response["range"]) for response in responses)
    tied = tuple(
        name for name, response in zip(abilities, responses) if tuple(response["range"]) == damage
    )
    desc = next(r["desc"] for r in responses if tuple(r["range"]) == damage)
    return BestAbility(tied, damage, desc)


def most_damaging_ability(
    attacker: str,
    move: str,
    defender: str,
    *,
    attacker_evs: dict | None = None,
    attacker_opts: dict | None = None,
    defender_evs: dict | None = None,
    defender_opts: dict | None = None,
    move_opts: dict | None = None,
    field_opts: dict | None = None,
) -> BestAbility:
    """Which of the attacker's abilities hits hardest here, ties included.

    The usual reason to want this is to ask the strongest version of a
    question: if the hardest-hitting ability cannot manage a KO, no set of
    that pokemon can, so the answer holds without knowing which ability the
    opponent actually runs.

    Conditional abilities are calculated with their condition unmet, and the
    two kinds are switched on differently: the pinch abilities (Overgrow,
    Blaze, Torrent, Swarm) key off current HP, so they need
    `attacker_opts={"originalCurHP": n}` with n at or under a third of max,
    while Flash Fire, Stakeout and the like key off
    `attacker_opts={"abilityOn": True}`.
    """
    return _ability_scan(
        attacker, move, defender, vary="attacker", pick=max,
        options=dict(
            attacker_evs=attacker_evs, attacker_opts=attacker_opts,
            defender_evs=defender_evs, defender_opts=defender_opts,
            move_opts=move_opts, field_opts=field_opts,
        ),
    )


def least_damaged_ability(
    defender: str,
    attacker: str,
    move: str,
    *,
    attacker_evs: dict | None = None,
    attacker_opts: dict | None = None,
    defender_evs: dict | None = None,
    defender_opts: dict | None = None,
    move_opts: dict | None = None,
    field_opts: dict | None = None,
) -> BestAbility:
    """Which of the defender's abilities takes the hit best, ties included.

    The mirror of most_damaging_ability, and the same argument in reverse: if
    the most resistant ability still cannot survive, no set of that pokemon
    survives either. Defensive abilities are where this matters most - Thick
    Fat halves the damage, Levitate and Flash Fire zero it - and the ones that
    cancel a type entirely are exactly the ones a type chart would miss.

    The defender leads the signature because it is the one being asked about.
    """
    return _ability_scan(
        attacker, move, defender, vary="defender", pick=min,
        options=dict(
            attacker_evs=attacker_evs, attacker_opts=attacker_opts,
            defender_evs=defender_evs, defender_opts=defender_opts,
            move_opts=move_opts, field_opts=field_opts,
        ),
    )


def min_evs_to_ko(
    attacker: str,
    move: str,
    defender: str,
    *,
    percent: float = 100.0,
    attacker_opts: dict | None = None,
    defender_evs: dict | None = None,
    defender_opts: dict | None = None,
    move_opts: dict | None = None,
    field_opts: dict | None = None,
) -> Investment | None:
    """Fewest attacking stat points that guarantee `percent`% damage, or None.

    Guaranteed means the *lowest* roll clears the bar, which is the usual
    reading of "this OHKOes": a range that only sometimes reaches 100% does
    not count. For a Garanteed 2HKO set percent to 50.
    """
    stat = attacking_stat(move)
    return _cheapest(
        [
            build_request(
                attacker, move, defender,
                attacker_evs={stat: points},
                attacker_opts=attacker_opts,
                defender_evs=defender_evs,
                defender_opts=defender_opts,
                move_opts=move_opts,
                field_opts=field_opts,
            )
            for points in range(MAX_STAT_POINTS + 1)
        ],
        # range[0] is the lowest roll: the damage that is always dealt.
        lambda response: 100 * response["range"][0] / response["defenderMaxHP"] >= percent,
    )


def min_evs_to_survive(
    attacker: str,
    move: str,
    defender: str,
    invest:str,
    *,
    percent: float = 100.0,
    attacker_opts: dict | None = None,
    attacker_evs: dict | None = None,
    defender_evs: dict | None = None,
    defender_opts: dict | None = None,
    move_opts: dict | None = None,
    field_opts: dict | None = None,
) -> Investment | None:

    hp = "hp"

    print(f"Minimum {hp}/{invest} for {defender} to take under {percent}% from {attacker} {move}:")
    
    breakpoints = find_damage_breakpoints(
        attacker, move, defender,
        invest=invest,
        attacker_evs=attacker_evs,
        attacker_opts=attacker_opts,
        defender_evs=defender_evs,
        defender_opts=defender_opts,
        move_opts=move_opts,
        field_opts=field_opts
    )

    optimal_EVs = calculate_HP_from_Breakpoints(breakpoints,percent,hp,invest)

    min_total = sum(optimal_EVs[0].values())

    for res in verify_Min_EVs(optimal_EVs,attacker,move,defender,attacker_evs=attacker_evs,attacker_opts=attacker_opts):
        print(f"{min_total} Points: {res.desc}")

def find_damage_breakpoints(
    attacker: str,
    move: str,
    defender: str,
    *,
    invest: str = "def",
    attacker_evs: dict | None = None,
    attacker_opts: dict | None = None,
    defender_evs: dict | None = None,
    defender_opts: dict | None = None,
    move_opts: dict | None = None,
    field_opts: dict | None = None,
) -> list[Investment]:
    """The fewest `invest` EVs needed to reach each distinct max-damage value."""
    if invest not in ("hp", "def", "spd"):
        raise ValueError(f"invest must be hp, def or spd, got {invest!r}")

    requests = [
        build_request(
            attacker, move, defender,
            attacker_evs=attacker_evs,
            attacker_opts=attacker_opts,
            defender_evs={**(defender_evs or {}), invest: points},
            defender_opts=defender_opts,
            move_opts=move_opts,
            field_opts=field_opts,
        )
        for points in range(MAX_STAT_POINTS + 1)
    ]
    return _breakpoints(requests, key=lambda response: response["range"][1])



@dataclass(frozen=True, slots=True)
class DamageFilter:
    """A question for the calculator, deferred until it has candidates.

    The SQL filters in teambuilder.filters compose into one query; these
    cannot, because each one has to run the calculator per candidate. They
    compose the same way regardless: `&` runs the second check only on the
    names the first kept, so chaining narrows the work instead of doubling it.

    `run` returns {name: one Investment per check, in composition order}.
    """

    natural: str
    run: "Callable[[Iterable[str]], dict[str, tuple[Investment, ...]]]"

    def __and__(self, other: "DamageFilter") -> "DamageFilter":
        def run(candidates: Iterable[str]) -> dict[str, tuple[Investment, ...]]:
            kept = self.run(candidates)
            # A dict iterates as its keys, so this hands the survivors on.
            passed = other.run(kept)
            return {name: kept[name] + passed[name] for name in passed}

        return DamageFilter(f"{self.natural} AND\n{other.natural}", run)

    def __call__(self, candidates: Iterable[str]) -> dict[str, tuple[Investment, ...]]:
        return self.run(candidates)

    def __str__(self):
        return self.natural


def ko_filter(
    move: str,
    defender: str,
    *,
    percent: float = 100.0,
    require_learns: bool = True,
    attacker_opts: dict | None = None,
    defender_evs: dict | None = None,
    defender_opts: dict | None = None,
    move_opts: dict | None = None,
    field_opts: dict | None = None,
    db: Path = DB_PATH,
) -> DamageFilter:
    """Keeps candidates that can guarantee `percent`% damage on `defender`.

    Each candidate is asked at its own hardest-hitting ability, so one that is
    dropped cannot do it with any ability. One that is kept may need an
    ability it does not always run - read `.desc` before trusting it.

    The defender is calculated exactly as `defender_opts` describes it, so its
    ability is whatever slot one happens to be. Thick Fat and friends have to
    be asked for; `survive_filter` is the side that picks abilities for the
    defender.
    """
    def run(candidates: Iterable[str]) -> dict[str, tuple[Investment, ...]]:
        names = _species_names(candidates)
        if require_learns:
            names = that_learn(move, names, db=db)

        kept = {}
        for name in names:
            best = most_damaging_ability(
                name, move, defender,
                # The strongest version of the question: max points in the
                # stat the move uses, so nothing is ruled out for lack of
                # investment before the ability is even chosen.
                attacker_evs={attacking_stat(move): MAX_STAT_POINTS},
                attacker_opts=attacker_opts,
                defender_evs=defender_evs, defender_opts=defender_opts,
                move_opts=move_opts, field_opts=field_opts,
            )
            investment = min_evs_to_ko(
                name, move, defender,
                percent=percent,
                attacker_opts={**(attacker_opts or {}), "ability": best.names[0]},
                defender_evs=defender_evs, defender_opts=defender_opts,
                move_opts=move_opts, field_opts=field_opts,
            )
            if investment is not None:
                kept[name] = (investment,)
        return kept

    threshold = "KOes" if percent == 100.0 else f"deals {percent}% to"
    return DamageFilter(f"{threshold} {defender} with {move}", run)

def can_ko_any_atk(
    defender: str,
    *,
    percent: float = 100.0,
    attacker_opts: dict | None = None,
    defender_evs: dict | None = None,
    defender_opts: dict | None = None,
    move_opts: dict | None = None,
    field_opts: dict | None = None,
    db: Path = DB_PATH,
) -> DamageFilter:
    """Keeps candidates with any attack that guarantees `percent`% on `defender`.

    The cheapest such move wins, and the result records which one it was.
    Slow by construction: every damaging move in the learnset costs two node
    processes, so this is the filter you run last, on a short list.
    """
    def run(candidates: Iterable[str]) -> dict[str, tuple[Investment, ...]]:
        kept = {}
        for name in tqdm(_species_names(candidates), desc=f"Attacks that KO {defender}"):
            cheapest = None
            for move in _damaging_moves(name, db=db):
                best = most_damaging_ability(
                    name, move, defender,
                    attacker_evs={attacking_stat(move): MAX_STAT_POINTS},
                    attacker_opts=attacker_opts,
                    defender_evs=defender_evs, defender_opts=defender_opts,
                    move_opts=move_opts, field_opts=field_opts,
                )
                investment = min_evs_to_ko(
                    name, move, defender,
                    percent=percent,
                    attacker_opts={**(attacker_opts or {}), "ability": best.names[0]},
                    defender_evs=defender_evs, defender_opts=defender_opts,
                    move_opts=move_opts, field_opts=field_opts,
                )
                if investment is None:
                    continue
                investment = investment._replace(move=move)
                if cheapest is None or investment.points < cheapest.points:
                    cheapest = investment
                if cheapest.points == 0:
                    break          # free already, nothing can beat it
            if cheapest is not None:
                kept[name] = (cheapest,)
        return kept

    return DamageFilter(f"KOes {defender} with some attack", run)


def _damaging_moves(name: str, *, db: Path = DB_PATH) -> list[str]:
    """The learnset minus Status moves and minus what the calculator lacks.

    move_category is None for moves champout carries that the Champions data
    does not, and attacking_stat raises on those, so they go out together.
    """
    return [m for m in learnset(name, db=db) if move_category(m) in ("Physical", "Special")]
def survive_filter(
    attacker: str,
    move: str,
    *,
    percent: float = 100.0,
    invest: str = "hp",
    require_learns: bool = True,
    attacker_evs: dict | None = None,
    attacker_opts: dict | None = None,
    defender_opts: dict | None = None,
    move_opts: dict | None = None,
    field_opts: dict | None = None,
    db: Path = DB_PATH,
) -> DamageFilter:
    """Keeps candidates that can hold `attacker`'s `move` under `percent`%.

    The mirror of ko_filter: there the candidate attacks and picks its best
    ability, here the candidate defends and picks the ability that takes the
    hit best. So a candidate dropped here cannot survive with any ability, and
    one kept may be relying on an ability it does not always run.

    The attacker is calculated as given, which is the same asymmetry ko_filter
    has with its defender: if the attacker's own ability matters, pass it in
    `attacker_opts`, or ask most_damaging_ability for it first.
    """
    if require_learns and not that_learn(move, [attacker], db=db):
        raise ValueError(f"{attacker} does not learn {move}")

    def run(candidates: Iterable[str]) -> dict[str, tuple[Investment, ...]]:
        kept = {}
        for name in _species_names(candidates):
            best = least_damaged_ability(
                name, attacker, move,
                attacker_evs=attacker_evs, attacker_opts=attacker_opts,
                # Max points in the stat being invested, for the same reason
                # ko_filter maxes the attacking stat before choosing.
                defender_evs={invest: MAX_STAT_POINTS},
                defender_opts=defender_opts,
                move_opts=move_opts, field_opts=field_opts,
            )
            investment = min_evs_to_survive(
                attacker, move, name,
                percent=percent, invest=invest,
                attacker_evs=attacker_evs, attacker_opts=attacker_opts,
                defender_opts={**(defender_opts or {}), "ability": best.names[0]},
                move_opts=move_opts, field_opts=field_opts,
            )
            if investment is not None:
                kept[name] = (investment,)
        return kept

    threshold = "survives" if percent == 100.0 else f"takes under {percent}% from"
    spread = "" if invest == "hp" else f" ({invest})"
    return DamageFilter(f"{threshold} {move} from {attacker}{spread}", run)


def can_ko(candidates: Iterable[str], move: str, defender: str, **options) -> dict[str, Investment]:
    """ko_filter run on one set of candidates: {name: cheapest spread}.

    `options` are ko_filter's, which is where they are documented; this only
    unwraps the single-check result so the common case stays a plain mapping.
    """
    return _one_check(ko_filter(move, defender, **options), candidates)


def can_survive(
    candidates: Iterable[str], attacker: str, move: str, **options
) -> dict[str, Investment]:
    """survive_filter run on one set of candidates: {name: cheapest spread}."""
    return _one_check(survive_filter(attacker, move, **options), candidates)


def _one_check(check: DamageFilter, candidates: Iterable[str]) -> dict[str, Investment]:
    return {name: found[0] for name, found in check.run(candidates).items()}


def _species_names(candidates: Iterable[str]) -> list[str]:
    """Candidates as a list, with the one mistake worth catching caught.

    A list of dex numbers reaches DuckDB as ints and fails deep inside an IN
    clause with a cast error, so say what went wrong here instead: search()
    returns whole rows, and its default columns start with the number.
    """
    names = list(candidates)
    wrong = next((n for n in names if not isinstance(n, str)), None)
    if wrong is not None:
        raise TypeError(
            f"candidates must be species names, got {wrong!r} - "
            'select them with search(..., columns="name")'
        )
    return names
