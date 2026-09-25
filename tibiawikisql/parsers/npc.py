from typing import Any, ClassVar

import mwparserfromhell
import tibiawikisql.schema
from tibiawikisql.api import Article
from tibiawikisql.models.npc import Npc, NpcDestination, NpcLocation
from tibiawikisql.parsers import BaseParser
from tibiawikisql.parsers.base import AttributeParser
from tibiawikisql.utils import clean_links, convert_tibiawiki_position, find_template, strip_code


class NpcParser(BaseParser):
    """Parser for NPCs."""

    table = tibiawikisql.schema.NpcTable
    model = Npc
    template_name = "Infobox_NPC"
    attribute_map: ClassVar = {
        "name": AttributeParser(lambda x: x.get("actualname") or x.get("name")),
        "gender": AttributeParser.optional("gender"),
        "location": AttributeParser.optional("location", clean_links),
        "subarea": AttributeParser.optional("subarea"),
        "city": AttributeParser.required("city"),
        "x": AttributeParser.optional("posx", convert_tibiawiki_position),
        "y": AttributeParser.optional("posy", convert_tibiawiki_position),
        "z": AttributeParser.optional("posz", int),
        "version": AttributeParser.optional("implemented"),
        "status": AttributeParser.status(),
    }

    @classmethod
    def parse_attributes(cls, article: Article) -> dict[str, Any]:
        row = super().parse_attributes(article)
        raw_attributes = row["_raw_attributes"]
        cls._parse_jobs(row)
        cls._parse_races(row)
        cls._parse_locations(row)

        row["destinations"] = []
        destinations = []
        if "notes" in raw_attributes and "{{Transport" in raw_attributes["notes"]:
            destinations.extend(cls._parse_destinations(raw_attributes["notes"]))
        for destination, price, notes in destinations:
            name = destination.strip()
            clean_notes = clean_links(notes.strip())
            if not notes:
                clean_notes = None
            row["destinations"].append(NpcDestination(
                name=name,
                price=price,
                notes=clean_notes,
            ))
        return row


    # region Auxiliary Methods

    @classmethod
    def _parse_jobs(cls, row: dict[str, Any]) -> None:
        """Read the possible multiple job parameters of an NPC's page and put them together in a list."""
        raw_attributes = row["_raw_attributes"]
        row["jobs"] = [
            clean_links(value)
            for key, value in raw_attributes.items()
            if key.startswith("job")
        ]

    @classmethod
    def _parse_races(cls, row: dict[str, Any]) -> None:
        """Read the possible multiple race parameters of an NPC's page and put them together in a list."""
        raw_attributes = row["_raw_attributes"]
        row["races"] = [
            clean_links(value)
            for key, value in raw_attributes.items()
            if key.startswith("race")
        ]

    @classmethod
    def _parse_locations(cls, row: dict[str, Any]) -> None:
        """Read every position of an NPC's page into a list, in position order.

        Position 1 uses the unsuffixed fields, positions 2 to 7 the fields suffixed with their number.
        A position exists when any of its fields is present, and missing positions are skipped.
        """
        raw_attributes = row["_raw_attributes"]
        row["locations"] = []
        for position in range(1, 8):
            suffix = "" if position == 1 else str(position)
            fields = {
                name: raw_attributes.get(f"{name}{suffix}", "").strip()
                for name in ("city", "subarea", "geolabel", "posx", "posy", "posz")
            }
            if not any(fields.values()):
                continue
            row["locations"].append(NpcLocation(
                position=position,
                city=clean_links(fields["city"]) or None,
                subarea=clean_links(fields["subarea"]) or None,
                geolabel=clean_links(fields["geolabel"]) or None,
                x=cls._parse_location_coordinate(fields["posx"]),
                y=cls._parse_location_coordinate(fields["posy"]),
                z=cls._parse_int(fields["posz"]),
            ))

    @classmethod
    def _parse_location_coordinate(cls, value: str) -> int | None:
        """Convert a TibiaWiki ``major.minor`` coordinate, returning ``None`` for anything malformed.

        Unlike :func:`convert_tibiawiki_position`, which falls back to 0, this rejects a non-integer part
        or more than two parts. An absent or empty minor counts as 0.
        """
        parts = value.split(".")
        if len(parts) > 2:
            return None
        major = cls._parse_int(parts[0])
        minor = cls._parse_int(parts[1]) if len(parts) == 2 and parts[1].strip() else 0
        if major is None or minor is None:
            return None
        return (major << 8) + minor

    @classmethod
    def _parse_int(cls, value: str) -> int | None:
        """Convert a string to an integer, returning ``None`` if it is not one."""
        try:
            return int(value)
        except ValueError:
            return None

    @classmethod
    def _parse_destinations(cls, value: str) -> list[tuple[str, int, str]]:
        """Parse an NPC destinations into a list of tuples.

        The tuple contains the  destination's name, price and notes.
        Price and notes may not be present.

        Args:
            value: A string containing the Transport template with destinations.

        Returns:
            A list of tuples, where each element is the name of the destination, the price and additional notes.
        """
        result = cls._parse_transport_cells(value)
        if result:
            return result

        template = find_template(value, "Transport")
        if not template:
            return []
        result = []
        for param in template.params:
            if param.showkey:
                continue
            data, *notes = strip_code(param).split(";", 1)
            notes = notes[0] if notes else ""
            destination, price_str = data.split(",")
            try:
                price = int(price_str)
            except ValueError:
                price = 0
            result.append((destination, price, notes))
        return result

    @classmethod
    def _parse_transport_cells(cls, value: str) -> list[tuple[str, int, str]]:
        """Parse TransportCell entries from the NPC notes field."""
        result = []
        parsed = mwparserfromhell.parse(value)
        for template in parsed.ifilter_templates(recursive=True):
            template_name = strip_code(template.name).lower().replace("_", " ")
            if template_name != "transportcell":
                continue
            destination = strip_code(template.get(1, ""))
            price_str = strip_code(template.get(2, "0"))
            notes = strip_code(template.get(3, ""))
            try:
                price = int(price_str)
            except ValueError:
                price = 0
            result.append((destination, price, notes))
        return result

    # endregion
