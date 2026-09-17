"""A worked example of the whole pipeline, wired to `uv run demo`."""

from teambuilder.damage import (
    can_ko,
    ko_filter,
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


def main():
    f = (
        has_type("Grass")
        & stat_between("bst", 400, 600)
        & min_stat("atk", 90)
        & max_stat("spe", 120)
        & learns("Swords Dance")
        & (ability("Chlorophyll") | ability("Overgrow"))
    )
    print(f"Search Filter:\n{f}")
    print()
    for row in search(f, columns="name, type1, type2, atk, spe, bst"):
        print(row)

    print()
    print("Minimum points for Blaziken to always OHKO Incineroar:")
    print(" ", min_evs_to_ko("Blaziken", "Close Combat", "Incineroar", defender_evs={"def": 12}))

    print("Minimum points for Snorlax to take under 70% from max Atk Rillaboom:")
    print(" ", min_evs_to_survive("Rillaboom", "Wood Hammer", "Snorlax",
                                  attacker_evs={"atk": 32}, percent=70))

    print()
    print("Which pokemon can KO mega salamence with triple axel while being base 100 or higher")
    
    speedy = [row[0] for row in search(min_stat("spe", 100), columns="name")]
    for name, investment in can_ko(speedy, "Triple Axel", "Salamence-Mega").items():
        print(f"  {name:<20} {investment.points} points")


    print()
    trade = (ko_filter("Triple Axel", "Salamence-Mega") 
    & survive_filter(
            "Sneasler", "Dire Claw", attacker_evs={"atk": 32}, attacker_opts={"nature": "Adamant"}
    )& survive_filter(
            "Sneasler", "Close Combat", attacker_evs={"atk": 32}, attacker_opts={"nature": "Adamant"}
    ))

    print("Which base 100 spe mons do both of these")
    print(f"{trade}\n")
    for name, (ko, survive) in trade(speedy).items():
        print(f"  {name:<20} {ko.points} points to KO, {survive.points} to survive")


if __name__ == "__main__":
    main()
