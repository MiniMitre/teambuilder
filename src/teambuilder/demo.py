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

    print()

    min_evs_to_survive("Salamence-Mega","Hyper Voice","Ariados",percent=100,attacker_opts={"nature":"","item":""},attacker_evs={"spa":32})
    min_evs_to_survive("Sneasler","Close Combat","Kingambit",percent=100,attacker_opts={"nature":"Adamant","item":""},attacker_evs={"atk":32},defender_opts={"item":"Chople Berry"},field_opts={"terrain":"Psychic"},showAll=True)

    slow = [row[0] for row in search(max_stat("spe", 45), columns="name")]
    mence_survival = survive_filter("Salamence-Mega", "Hyper Voice", attacker_evs={"spa": 32 } )
    for name, (investment, ) in mence_survival(slow).items(): 
        print(f"  {name:<20} {investment.points} points to Survive") 

    print("Which pokemon can KO mega salamence with triple axel while being base 100 or higher")
    
    speedy = [row[0] for row in search(min_stat("spe", 100), columns="name")]
    for name, investment in can_ko(speedy, "Triple Axel", "Salamence-Mega").items():
         print(f"  {name:<20} {investment.points} points")


    print()
    filter = (
         can_ko_any_atk("Salamence-Mega", defender_evs={"hp": 2})
    )

    print("Which base 100 spe mons manage this")
    print(f"{filter}\n")
    # One Investment per AND-ed filter, in composition order - so this unpacks
    # one while `filter` is a single check, and needs another name for every
    # check added to the chain.
    for name, (ko,) in filter(speedy).items():
        print(f"  {name:<20} {ko.points} points to KO with {ko.move}")


if __name__ == "__main__":
    main()
