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
        # Parens keep precedence explicit, so mixing & and | never surprises.
        # self.params first because self.sql comes first in the string.
        return Filter(f"({self.sql} {op} {other.sql})", f"{self.natural}\n{other.natural}", self.params + other.params)

    def __str__(self): return self.natural


def has_type(type_: str) -> Filter:
    return Filter("? IN (p.type1, coalesce(p.type2, p.type1))", f"Is of type: {type_}",  (type_,))

def learns(move: str) -> Filter:
    return Filter("EXISTS (SELECT 1 FROM pokemon_moves m WHERE m.pokemon = p.name AND m.move=? )", f"Learns: {move}",  (move,))

def ability(ability: str) -> Filter:
    return Filter("? IN (p.ability1, p.ability2, p.ability_hidden)", f"Ability: {ability}", (ability,))



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
    f =  learns("Simple Beam")
    print(f)
    for row in search(f):
        print(row)
    
