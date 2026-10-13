"""A worked example of the whole pipeline, wired to `uv run demo`."""

from teambuilder.damage import (
    can_ko,
    can_ko_any_atk,
    min_evs_to_ko,
    min_evs_to_survive,
    survive_filter,
)
from teambuilder.filters import (
    ability,
    has_type,
    learns,
    max_stat,
    min_stat,
    stat_between,
)
from teambuilder.pokedex import search

def print_survival_result(attacker, move, defender, **kwargs):
    result = min_evs_to_survive(attacker, move, defender, **kwargs)
    print(f"{attacker} {move} vs {defender}:")
    if result:
        for inv in result:
            print(f"  {inv}")
    else:
        print("  No viable spread found")

def main():
    print()
    print_survival_result(
        "Charizard-Mega-Y",
        "Weather Ball",
        "Kingambit",
        percent=100,
        defender_opts={"item":"Occa Berry"},
        attacker_evs="0+",
        field_opts={"weather":"Sun"},
        showAll=True
    )
if __name__ == "__main__":
    main()
