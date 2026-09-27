# Changed by tibia.sh in 2026. See "About this copy" in README.md.
from typing import Any, ClassVar

import tibiawikisql.schema
from tibiawikisql.api import Article
from tibiawikisql.models.mount import Mount
from tibiawikisql.parsers.base import AttributeParser
from tibiawikisql.parsers import BaseParser
from tibiawikisql.utils import clean_links, client_color_to_rgb, parse_boolean, parse_client_id, parse_integer


def remove_mount(name: str) -> str:
    """Remove "(Mount)" from the name, if found.

    Args:
        name: The name to check.

    Returns:
        The name with "(Mount)" removed from it.

    """
    return name.replace("(Mount)", "").strip()

class MountParser(BaseParser):
    """Parser for mounts."""

    model = Mount
    table = tibiawikisql.schema.MountTable
    template_name = "Infobox_Mount"
    attribute_map: ClassVar = {
        "name": AttributeParser.required("name", remove_mount),
        "speed": AttributeParser.required("speed", int),
        "taming_method": AttributeParser.optional("taming_method", clean_links),
        "is_buyable": AttributeParser.optional("bought", parse_boolean, False),
        "price": AttributeParser.optional("price", parse_integer),
        "achievement": AttributeParser.optional("achievement"),
        "light_color": AttributeParser.optional("lightcolor", lambda x: client_color_to_rgb(parse_integer(x))),
        "light_radius": AttributeParser.optional("lightradius", int),
        "client_id": AttributeParser.optional("mount_id", parse_client_id),
        "version": AttributeParser.version(),
        "status": AttributeParser.status(),
    }

    @classmethod
    def parse_attributes(cls, article: Article) -> dict[str, Any]:
        row = super().parse_attributes(article)
        raw_attributes = row["_raw_attributes"]
        row["price_currency"] = None
        if row["price"] is not None:
            currency = clean_links(raw_attributes.get("pricecurrency", ""))
            if currency:
                row["price_currency"] = currency
            elif parse_boolean(raw_attributes.get("tournament", "")):
                row["price_currency"] = "Tournament Coins"
            else:
                row["price_currency"] = "Tibia Coins"
        return row
