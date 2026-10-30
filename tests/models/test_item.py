# Changed by tibia.sh in 2026. See "About this copy" in README.md.
import datetime
import sqlite3
import unittest

from tests import load_resource
from tibiawikisql import schema
from tibiawikisql.api import Article
from tibiawikisql.models import Item
from tibiawikisql.parsers import ItemParser


class TestItemParser(unittest.TestCase):

    def test_item_parser_from_article_success(self):
        article = Article(
            article_id=1,
            title="Fire Sword",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item.txt"),
        )

        item = ItemParser.from_article(article)

        self.assertIsInstance(item, Item)
        self.assertEqual(len(item.attributes_dict.keys()), len(item.attributes))
        fire_sword_look_text = ("You see a fire sword (Atk:24 physical + 11 fire, Def:20 +1)."
                                " It can only be wielded properly by players of level 30 or higher."
                                "\nIt weights 23.00 oz.\n"
                                "The blade is a magic flame.")
        self.assertEqual(fire_sword_look_text, item.look_text)

    def test_item_parser_from_article_no_attrib(self):
        article = Article(
            article_id=1,
            title="Football",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item_no_attrib.txt"),
        )

        item = ItemParser.from_article(article)

        self.assertIsInstance(item, Item)

    def test_item_parser_from_article_perfect_shot(self):
        article = Article(
            article_id=1,
            title="Gilded Eldritch Wand",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item_perfect_shot.txt"),
        )

        item = ItemParser.from_article(article)

        self.assertIsInstance(item, Item)
        self.assertIn("perfect_shot", item.attributes_dict)
        self.assertIn("perfect_shot_range", item.attributes_dict)
        self.assertEqual("+2", item.attributes_dict["magic_level"])
        self.assertEqual("+1", item.attributes_dict["magic_level_fire"])

    def test_item_parser_from_article_damage_reflection(self):
        article = Article(
            article_id=1,
            title="Spiritthorn Armor",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item_damage_reflection.txt"),
        )

        item = ItemParser.from_article(article)

        self.assertIsInstance(item, Item)
        self.assertIn("damage_reflection", item.attributes_dict)


class TestItem(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        schema.create_tables(self.conn)

    def test_item_value_buy_currency_round_trip(self):
        article = Article(
            article_id=1,
            title="25 Years Backpack",
            timestamp=datetime.datetime.fromisoformat("2025-12-08T17:54:57+00:00"),
            content=load_resource("content_item_25_years_backpack.txt"),
        )
        ItemParser.from_article(article).insert(self.conn)

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual(7197, loaded.value_buy)
        self.assertEqual("Theons", loaded.value_buy_currency)

    def test_item_slot_and_usable_round_trip(self):
        article = Article(
            article_id=1,
            title="Amethyst Necklace",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item_amethyst_necklace.txt"),
        )
        ItemParser.from_article(article).insert(self.conn)

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual("neck", loaded.slot)
        self.assertIs(False, loaded.is_usable)

    def test_item_slot_and_usable_round_trip_none(self):
        article = Article(
            article_id=1,
            title="Shallow Water",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item_shallow_water.txt"),
        )
        ItemParser.from_article(article).insert(self.conn)

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)

        self.assertIsNone(loaded.slot)
        self.assertIsNone(loaded.is_usable)

    def test_item_client_ids_round_trip(self):
        article = Article(
            article_id=1,
            title="Shallow Water",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item_shallow_water.txt"),
        )
        ItemParser.from_article(article).insert(self.conn)

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)
        rows = self.conn.execute(
            "SELECT item_id, client_id, position FROM item_client_id ORDER BY position",
        ).fetchall()

        self.assertEqual(629, loaded.client_id)
        self.assertEqual([629, 630, 631, 632, 633, 634], loaded.client_ids)
        self.assertEqual(
            [(1, 629, 0), (1, 630, 1), (1, 631, 2), (1, 632, 3), (1, 633, 4), (1, 634, 5)],
            [tuple(row) for row in rows],
        )

    def test_item_client_ids_round_trip_single(self):
        article = Article(
            article_id=1,
            title="Amethyst Necklace",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item_amethyst_necklace.txt"),
        )
        ItemParser.from_article(article).insert(self.conn)

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)
        rows = self.conn.execute("SELECT item_id, client_id, position FROM item_client_id").fetchall()

        self.assertEqual([35609], loaded.client_ids)
        self.assertEqual([(1, 35609, 0)], [tuple(row) for row in rows])

    def test_item_location_round_trip(self):
        article = Article(
            article_id=1,
            title="Sneeze Blossom",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item_sneeze_blossom.txt"),
        )
        ItemParser.from_article(article).insert(self.conn)

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)
        rows = self.conn.execute(
            "SELECT item_id, x, y, z, label, position FROM item_location_coordinate ORDER BY position",
        ).fetchall()

        self.assertEqual("An example can be found at spot.", loaded.location)
        self.assertEqual([(32709, 31842, 7, "spot")], [(c.x, c.y, c.z, c.label) for c in loaded.location_coordinates])
        self.assertEqual([(1, 32709, 31842, 7, "spot", 0)], [tuple(row) for row in rows])

    def test_item_location_coordinates_round_trip_in_listed_order(self):
        content = load_resource("content_item_sneeze_blossom.txt")
        location = "{{Mapper Coords|127.197|124.98|7|3|text=spot}}"
        self.assertIn(location, content)
        article = Article(
            article_id=1,
            title="Sneeze Blossom",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content.replace(
                location,
                location + ", {{Mapper Coords|126.4|128.108|7|2}} and {{Mapper Coords|125.1|128.109|3|4|text=x}}",
            ),
        )
        ItemParser.from_article(article).insert(self.conn)

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual("An example can be found at spot, and x.", loaded.location)
        self.assertEqual(
            [(32709, 31842, 7, "spot"), (32260, 32876, 7, None), (32001, 32877, 3, "x")],
            [(c.x, c.y, c.z, c.label) for c in loaded.location_coordinates],
        )

    def test_item_location_round_trip_none(self):
        article = Article(
            article_id=1,
            title="Amethyst Necklace",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item_amethyst_necklace.txt"),
        )
        ItemParser.from_article(article).insert(self.conn)

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)

        self.assertIsNone(loaded.location)
        self.assertEqual([], loaded.location_coordinates)
        self.assertEqual([], self.conn.execute("SELECT * FROM item_location_coordinate").fetchall())

    def test_item_trade_value_note_round_trip(self):
        article = Article(
            article_id=1,
            title="Amazon Armor",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item_amazon_armor.txt"),
        )
        ItemParser.from_article(article).insert(self.conn)

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual("55,000,000 - 70,000,000", loaded.trade_value_note)

    def test_item_trade_value_note_round_trip_none(self):
        article = Article(
            article_id=1,
            title="Shallow Water",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_item_shallow_water.txt"),
        )
        ItemParser.from_article(article).insert(self.conn)

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)

        self.assertIsNone(loaded.trade_value_note)

    def _insert_amethyst_necklace_with_itemid(self, itemid: str) -> None:
        content = load_resource("content_item_amethyst_necklace.txt")
        self.assertIn("| itemid        = 35609", content)
        article = Article(
            article_id=1,
            title="Amethyst Necklace",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content.replace("| itemid        = 35609", f"| itemid        = {itemid}"),
        )
        ItemParser.from_article(article).insert(self.conn)

    def test_item_client_ids_round_trip_leading_comment(self):
        self._insert_amethyst_necklace_with_itemid("<!-- 7 -->644,645")

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)
        rows = self.conn.execute(
            "SELECT item_id, client_id, position FROM item_client_id ORDER BY position",
        ).fetchall()

        self.assertEqual(7, loaded.client_id)
        self.assertEqual([644, 645], loaded.client_ids)
        self.assertEqual([(1, 644, 0), (1, 645, 1)], [tuple(row) for row in rows])

    def test_item_client_ids_round_trip_comment_only(self):
        self._insert_amethyst_necklace_with_itemid("<!-- 7 -->")

        loaded = Item.get_one_by_field(self.conn, "article_id", 1)
        rows = self.conn.execute("SELECT item_id, client_id, position FROM item_client_id").fetchall()

        self.assertEqual(7, loaded.client_id)
        self.assertEqual([], loaded.client_ids)
        self.assertEqual([], rows)
