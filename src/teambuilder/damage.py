"""Damage questions answered by running the calculator: how many stat points
does an attack need, how few does surviving one take, and which candidates can
manage a KO at all.

Everything here shells out through teambuilder.calc, so it is orders of
magnitude slower than a SQL filter. Narrow the field down with filters first,
then ask these about the survivors.
"""

from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

from teambuilder.calc import CalcError, build_request, calculate, move_category
from teambuilder.data import DB_PATH
from teambuilder.pokedex import get_abilities_for_poke, that_learn

# Champions gives each stat 0-32 points, so every search below is a scan over
# 33 candidates in one batch - ~20ms, and damage is monotonic in the invested
# stat, so the first spread that clears the bar is the cheapest one.
MAX_STAT_POINTS = 32


class Investment(NamedTuple):
    """The cheapest spread that met a threshold, and the calc that proves it."""

    points: int
    desc: str
    percent: tuple[float, float]

    def __str__(self):
        return f"{self.points} points: {self.desc}"


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


def _cheapest(requests: list[dict], accept) -> Investment | None:
    """First response that `accept` likes, which is the cheapest by monotonicity."""
    for points, response in enumerate(calculate(requests)):
        if "error" in response:
            raise CalcError(response["error"])
        if accept(response):
            return Investment(points, response["desc"], tuple(response["percent"]))
    return None


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
    abilities = get_abilities_for_poke(attacker)
    requests = [
        build_request(
            attacker, move, defender,
            attacker_evs=attacker_evs,
            # A new dict per request: mutating one shared dict would also
            # hand the caller's options back with an ability glued on.
            attacker_opts={**(attacker_opts or {}), "ability": name},
            defender_evs=defender_evs,
            defender_opts=defender_opts,
            move_opts=move_opts,
            field_opts=field_opts,
        )
        for name in abilities
    ]

    responses = calculate(requests)
    for response in responses:
        if "error" in response:
            raise CalcError(response["error"])

    # Rolls scale together, so the highest range is the hardest hit either
    # way; ties are every ability that matches it, which is the common case
    # when none of them touch this move at all.
    best = max(tuple(response["range"]) for response in responses)
    tied = tuple(
        name for name, response in zip(abilities, responses) if tuple(response["range"]) == best
    )
    desc = next(r["desc"] for r in responses if tuple(r["range"]) == best)
    return BestAbility(tied, best, desc)


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
    not count. `percent` above 100 asks for overkill (useful against Focus
    Sash or Sturdy), below 100 for a chip threshold such as a guaranteed 2HKO
    at 50.
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
    *,
    percent: float = 100.0,
    invest: str = "hp",
    attacker_evs: dict | None = None,
    attacker_opts: dict | None = None,
    defender_evs: dict | None = None,
    defender_opts: dict | None = None,
    move_opts: dict | None = None,
    field_opts: dict | None = None,
) -> Investment | None:
    """Fewest points in `invest` that hold the damage under `percent`%, or None.

    The mirror of min_evs_to_ko: there the lowest roll has to reach the bar,
    here the *highest* roll has to stay under it, since surviving has to hold
    for every roll. The comparison is strict because damage equal to the
    defender's HP is a KO, so "survives" is "takes less than 100%".

    `invest` is the stat the points go into - "hp" is usually the most
    efficient, but "def" or "spd" can win once a defence is already high.
    """
    if invest not in ("hp", "def", "spd"):
        raise ValueError(f"invest must be hp, def or spd, got {invest!r}")
    return _cheapest(
        [
            build_request(
                attacker, move, defender,
                attacker_evs=attacker_evs,
                attacker_opts=attacker_opts,
                # Points go into `invest`; any other stats the caller set stay.
                defender_evs={**(defender_evs or {}), invest: points},
                defender_opts=defender_opts,
                move_opts=move_opts,
                field_opts=field_opts,
            )
            for points in range(MAX_STAT_POINTS + 1)
        ],
        # range[1] is the highest roll: the damage in the worst case.
        lambda response: 100 * response["range"][1] / response["defenderMaxHP"] < percent,
    )


def can_ko(
    candidates: Iterable[str],
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
) -> dict[str, Investment]:
    """Which candidates can guarantee `percent`% damage, and at what cost.

    Returns {name: cheapest spread}, dropping the ones that cannot manage it
    at any investment. Each candidate is asked at its hardest-hitting ability,
    so a pokemon that is dropped here cannot do it with any ability - which is
    the point: no assumption about the opponent's set is needed to rule one
    out. A candidate that stays may need an ability it does not always run, so
    `.desc` on the result is worth reading before trusting it.

    This is a filter to run *after* the SQL ones, not another Filter: it costs
    two node processes per candidate, so narrow the field down first and hand
    the survivors over.

    The defender is calculated exactly as `defender_opts` describes it, which
    means its ability defaults to the first slot rather than its most annoying
    one. Thick Fat and friends have to be asked for.
    """
    names = list(candidates)
    # A list of dex numbers reaches DuckDB as ints and fails deep inside the
    # IN clause with a cast error, so say what went wrong here instead:
    # search() returns whole rows, and its default columns start with number.
    wrong = next((n for n in names if not isinstance(n, str)), None)
    if wrong is not None:
        raise TypeError(
            f"candidates must be species names, got {wrong!r} - "
            'select them with search(..., columns="name")'
        )
    if require_learns:
        names = that_learn(move, names, db=db)

    found = {}
    for name in names:
        best = most_damaging_ability(
            name, move, defender,
            # The strongest version of the question: max points in the stat
            # the move uses, so nothing is ruled out for lack of investment.
            attacker_evs={attacking_stat(move): MAX_STAT_POINTS},
            attacker_opts=attacker_opts,
            defender_evs=defender_evs,
            defender_opts=defender_opts,
            move_opts=move_opts,
            field_opts=field_opts,
        )
        investment = min_evs_to_ko(
            name, move, defender,
            percent=percent,
            attacker_opts={**(attacker_opts or {}), "ability": best.names[0]},
            defender_evs=defender_evs,
            defender_opts=defender_opts,
            move_opts=move_opts,
            field_opts=field_opts,
        )
        if investment is not None:
            found[name] = investment
    return found
