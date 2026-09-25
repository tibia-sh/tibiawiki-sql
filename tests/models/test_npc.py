import datetime
import sqlite3
import unittest

from tibiawikisql import schema
from tibiawikisql.models import Npc, NpcLocation
from tibiawikisql.schema import ItemTable, NpcBuyingTable, NpcDestinationTable, NpcJobTable, NpcLocationTable, \
    NpcRaceTable, \
    NpcSellingTable, \
    NpcTable, \
    SpellTable


class TestNpc(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(NpcTable.get_create_table_statement())
        self.conn.executescript(NpcJobTable.get_create_table_statement())
        self.conn.executescript(NpcRaceTable.get_create_table_statement())
        self.conn.executescript(NpcBuyingTable.get_create_table_statement())
        self.conn.executescript(NpcSellingTable.get_create_table_statement())
        self.conn.executescript(ItemTable.get_create_table_statement())
        self.conn.executescript(NpcDestinationTable.get_create_table_statement())
        self.conn.executescript(NpcLocationTable.get_create_table_statement())

    def test_npc_with_spells(self):
        # Arrange
        NpcTable.insert(
            self.conn,
            article_id=1,
            title="Azalea",
            name="Azalea",
            gender="Female",
            city="Rathleton",
            subarea="Oramond",
            location="The temple in Upper Rathleton",
            version="10.50",
            x=33593,
            y=31899,
            z=6,
            status="active",
            timestamp=datetime.datetime.fromisoformat("2024-07-29T16:37:09+00:00"),
        )
        NpcJobTable.insert(self.conn, npc_id=1, name="Druid")
        NpcJobTable.insert(self.conn, npc_id=1, name="Druid Guild Leader")
        NpcJobTable.insert(self.conn, npc_id=1, name="Cleric")
        NpcJobTable.insert(self.conn, npc_id=1, name="Healer")
        NpcJobTable.insert(self.conn, npc_id=1, name="Florist")
        NpcRaceTable.insert(self.conn, npc_id=1, name="Human")
        self.conn.executescript(SpellTable.get_create_table_statement())
        SpellTable.insert(
            self.conn,
            article_id=1,
            title="Food (Spell)",
            name="Food (Spell)",
            words="exevo pan",
            effect="Creates various kinds of food.",
            spell_type="Instant",
            group_spell="Support",
            level=14,
            mana=120,
            soul=1,
            is_premium=False,
            is_promotion=False,
            status="active",
            timestamp=datetime.datetime.fromisoformat("2024-07-29T16:37:09+00:00"),
        )

        npc = Npc.get_one_by_field(self.conn, "name", "Azalea")

        self.assertIsInstance(npc, Npc)
        self.assertEqual(5, len(npc.jobs))
        self.assertEqual("Human", npc.race)

    def test_npc_locations_round_trip(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        schema.create_tables(conn)
        npc = Npc(
            article_id=1,
            title="Buddel",
            name="Buddel",
            gender="Male",
            location=None,
            subarea=None,
            city="Svargrond",
            x=32254,
            y=31195,
            z=7,
            version="8.00",
            status="active",
            timestamp=datetime.datetime.fromisoformat("2024-07-29T16:37:09+00:00"),
            locations=[
                NpcLocation(position=3, city="Svargrond", subarea="Helheim", x=32464, y=31172, z=7),
                NpcLocation(position=1, city="Svargrond", geolabel="Harbour", x=32254, y=31195, z=7),
            ],
        )

        npc.insert(conn)
        loaded = Npc.get_one_by_field(conn, "article_id", 1)

        self.assertEqual(
            [
                NpcLocation(position=1, city="Svargrond", geolabel="Harbour", x=32254, y=31195, z=7),
                NpcLocation(position=3, city="Svargrond", subarea="Helheim", x=32464, y=31172, z=7),
            ],
            loaded.locations,
        )
