import datetime
import sqlite3
import unittest

from tibiawikisql import schema
from tibiawikisql.models import Mount


class TestMount(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        schema.create_tables(self.conn)

    def _mount(self, client_id: int | None) -> Mount:
        return Mount(
            article_id=1,
            title="Doombringer",
            name="Doombringer",
            speed=10,
            taming_method="Buying it on Tibia.com or via the Store.",
            is_buyable=True,
            price=780,
            achievement=None,
            light_color=None,
            light_radius=None,
            client_id=client_id,
            version="10.56",
            status="active",
            timestamp=datetime.datetime.fromisoformat("2024-07-29T16:37:09+00:00"),
        )

    def test_mount_client_id_round_trip(self):
        self._mount(644).insert(self.conn)

        loaded = Mount.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual(644, loaded.client_id)

    def test_mount_client_id_round_trip_none(self):
        self._mount(None).insert(self.conn)

        loaded = Mount.get_one_by_field(self.conn, "article_id", 1)

        self.assertIsNone(loaded.client_id)
