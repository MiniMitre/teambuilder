"""Composable SQL filters over the pokemon table.

A filter is a WHERE fragment plus the values its placeholders need. Keeping
those two things together is what makes filters composable: when you glue two
fragments with AND, you glue their parameter lists in the same order, so the
values still line up with the `?`s left to right in the final query.
"""

from dataclasses import dataclass
from pathlib import Path

import duckdb

from teambuilder.data import DB_PATH


@dataclass(frozen=True, slots=True)
class Filter:
    """A `WHERE` fragment and the values for its `?` placeholders."""

    sql: str
    natural: str 
    params: tuple[object, ...] = ()

    def __and__(self, other: "Filter") -> "Filter":
        return self._combine("AND", other)

    def __or__(self, other: "Filter") -> "Filter":
        return self._combine("OR", other)

    def __invert__(self) -> "Filter":
        return Filter(f"NOT ({self.sql})", f"not {self.natural} ", self.params)

    def _combine(self, op: str, other: "Filter") -> "Filter":
        # Parens keep precedence explicit in the SQL, so mixing & and | never
        # surprises. The description uses layout instead of parens: AND ends
        # the line, OR keeps its operands together on one.
        # self.params first because self.sql comes first in the string.
        separator = f" {op}\n" if op == "AND" else f" {op} "
        return Filter(
            f"({self.sql} {op} {other.sql})",
            f"{self.natural}{separator}{other.natural}",
            self.params + other.params,
        )

    def __str__(self): return self.natural


def has_type(type_: str) -> Filter:
    return Filter("? IN (p.type1, coalesce(p.type2, p.type1))", f"Is of type: {type_}",  (type_,))

def learns(move: str) -> Filter:
    return Filter("EXISTS (SELECT 1 FROM pokemon_moves m WHERE m.pokemon = p.name AND m.move=? )", f"Learns: {move}",  (move,))

def ability(ability: str) -> Filter:
    return Filter("? IN (p.ability1, p.ability2, p.ability_hidden)", f"Ability: {ability}", (ability,))



STATS = ("hp", "atk", "def", "spa", "spd", "spe", "bst")


def _column(stat: str) -> str:
    """Validate a stat name, since a column has to be interpolated, not bound.

    Placeholders only stand for values, never identifiers, so `stat` ends up
    in the SQL as text - checking it against STATS is what keeps that safe.
    The quotes let "def" through: it is a column here but a keyword in SQL.
    """
    if stat not in STATS:
        raise ValueError(f"unknown stat {stat!r}, expected one of {', '.join(STATS)}")
    return f'p."{stat}"'


def min_stat(stat: str, value: int) -> Filter:
    return Filter(f"{_column(stat)} >= ?", f"At Least {value} {stat}", (value,))


def max_stat(stat: str, value: int) -> Filter:
    return Filter(f"{_column(stat)} <= ?", f"At Most {value} {stat}", (value,))


def stat_between(stat: str, low: int, high: int) -> Filter:
    # BETWEEN is inclusive on both ends, like min_stat & max_stat would be.
    return Filter(f"{_column(stat)} BETWEEN ? AND ?", f"{stat} between {low} and {high}", (low, high))

def search(
    filters: Filter | None = None,
    *,
    columns: str = "number, name, type1, type2",
    order_by: str = "number",
    db: Path = DB_PATH,
) -> list[tuple]:
    # "TRUE" is a valid WHERE, so no-filters needs no special case.
    where = filters.sql if filters else "TRUE"
    params = filters.params if filters else ()
    sql = f"SELECT {columns} FROM pokemon p WHERE {where} ORDER BY {order_by}"

    with duckdb.connect(db, read_only=True) as con:
        return con.execute(sql, list(params)).fetchall()

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
