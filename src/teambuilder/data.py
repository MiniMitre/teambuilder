from dataclasses import dataclass
from pathlib import Path

import duckdb
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[2]
FILES_PATH = ROOT / "champout" / "parse"
POKEDEX_PATH = FILES_PATH / "personal_dump.txt"
MOVES_PATH = FILES_PATH / "move_availability.txt"
POKES_PER_MOVE = FILES_PATH / "species_with_move.txt"

DB_PATH = ROOT / "teambuilder.duckdb"


@dataclass(slots=True)
class Pokemon:
    number: int
    name: str
    hp: int
    atk: int
    defense: int
    spa: int
    spd: int
    spe: int
    type1: str
    type2: str | None
    ability1: str
    ability2: str
    ability_hidden: str
    moves: list[str]


def parse_moves_line(line: str) -> tuple[int, str]:
    number, name = line.split("\t")
    return int(number), name.strip()


def parse_pokedex(text: str) -> list[Pokemon]:
    # Entries are separated by a blank line, so split on that instead of
    # tracking an offset by hand.
    return [parse_one_poke(block.splitlines()) for block in tqdm(text.strip().split("\n\n"), desc="Parsing Available Mons")]


def parse_one_poke(lines: list[str]) -> Pokemon:
    # "0003 - Venusaur-Mega" -> ("0003", "Venusaur-Mega"): split once, on the
    # separator with spaces around it, so dashes inside the name survive.
    number, name = lines[0].split(" - ", 1)
    stats = [int(stat) for stat in lines[1].split("/")]
    types = [t.strip() for t in lines[2].split("/")]
    abilities = [a.strip() for a in lines[3].split("/")]

    # lines[4] is just "Moves:"
    # Move names contain dashes too ("Double-Edge"), so strip the leading
    # "- " rather than splitting on "-".
    moves = [line.removeprefix("- ").strip() for line in lines[5:] if line.startswith("- ")]

    return Pokemon(
        number=int(number),
        name=name.strip(),
        hp=stats[0],
        atk=stats[1],
        defense=stats[2],
        spa=stats[3],
        spd=stats[4],
        spe=stats[5],
        type1=types[0],
        type2=second_type(types),
        ability1=abilities[0],
        ability2=abilities[1],
        ability_hidden=abilities[2],
        moves=moves,
    )


def second_type(types: list[str]) -> str | None:
    """The real second type, or None for genuine mono-types.

    The dump encodes mono-types by repeating the type ("Fire/Fire"), and it
    drops the second type entirely when that type is Normal ("Pyroar\nFire",
    though Pyroar is Fire/Normal) - Normal is type id 0, which the dumper
    evidently treats as "no type". So a missing second field means Normal,
    and a second field equal to the first means mono-type.
    """
    type2 = types[1] if len(types) > 1 else "Normal"
    return None if type2 == types[0] else type2


SCHEMA = """
DROP TABLE IF EXISTS pokemon_moves;
DROP TABLE IF EXISTS pokemon;
DROP TABLE IF EXISTS moves;

CREATE TABLE moves (
    number INTEGER,
    name   VARCHAR PRIMARY KEY
);

CREATE TABLE pokemon (
    number         INTEGER NOT NULL,
    name           VARCHAR PRIMARY KEY,
    hp             INTEGER NOT NULL,
    atk            INTEGER NOT NULL,
    def            INTEGER NOT NULL,
    spa            INTEGER NOT NULL,
    spd            INTEGER NOT NULL,
    spe            INTEGER NOT NULL,
    bst            INTEGER NOT NULL,
    type1          VARCHAR NOT NULL,
    type2          VARCHAR,
    ability1       VARCHAR,
    ability2       VARCHAR,
    ability_hidden VARCHAR
);

CREATE TABLE pokemon_moves (
    pokemon VARCHAR NOT NULL REFERENCES pokemon(name),
    move    VARCHAR NOT NULL,
    PRIMARY KEY (pokemon, move)
);
"""


def build() -> None:
    ingame_moves = [parse_moves_line(line) for line in tqdm(MOVES_PATH.read_text().splitlines(), desc="Parsing Moves") if line.strip()]
    ingame_pokemon = parse_pokedex(POKEDEX_PATH.read_text())

    pokemon_rows = [
        (
            p.number,
            p.name,
            p.hp,
            p.atk,
            p.defense,
            p.spa,
            p.spd,
            p.spe,
            p.hp + p.atk + p.defense + p.spa + p.spd + p.spe,
            p.type1,
            p.type2,
            p.ability1,
            p.ability2,
            p.ability_hidden,
        )
        for p in ingame_pokemon
    ]
    learnset_rows = [(p.name, move) for p in tqdm(ingame_pokemon, desc="Writing Learnset for Pokemon") for move in p.moves]

    print("Building DuckDB database")
    with duckdb.connect(DB_PATH) as con:
        con.execute(SCHEMA)
        con.executemany("INSERT INTO moves VALUES (?, ?)", ingame_moves)
        con.executemany("INSERT INTO pokemon VALUES (" + ", ".join(["?"] * 14) + ")", pokemon_rows)
        con.executemany("INSERT INTO pokemon_moves VALUES (?, ?)", learnset_rows)

    print(f"{DB_PATH}: {len(pokemon_rows)} pokemon, {len(ingame_moves)} moves, {len(learnset_rows)} learnset rows")
