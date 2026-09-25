import datetime
import sqlite3
import unittest

from tibiawikisql import schema
from tibiawikisql.models import Outfit


class TestOutfit(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        schema.create_tables(self.conn)

    def _outfit(self, male_client_id: int | None, female_client_id: int | None) -> Outfit:
        return Outfit(
            article_id=1,
            title="Barbarian Outfits",
            name="Barbarian",
            outfit_type="Premium",
            is_premium=True,
            is_bought=False,
            is_tournament=False,
            full_price=None,
            achievement="Brutal Politeness",
            male_client_id=male_client_id,
            female_client_id=female_client_id,
            version="7.8",
            status="active",
            timestamp=datetime.datetime.fromisoformat("2024-07-29T16:37:09+00:00"),
        )

    def test_outfit_client_ids_round_trip(self):
        self._outfit(143, 147).insert(self.conn)

        loaded = Outfit.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual((143, 147), (loaded.male_client_id, loaded.female_client_id))

    def test_outfit_client_ids_round_trip_none(self):
        self._outfit(None, None).insert(self.conn)

        loaded = Outfit.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual((None, None), (loaded.male_client_id, loaded.female_client_id))
