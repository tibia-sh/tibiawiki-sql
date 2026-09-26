import datetime
import sqlite3
import unittest

from tibiawikisql import schema
from tibiawikisql.models import Creature


class TestCreature(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        schema.create_tables(self.conn)

    def _creature(self, race_id: int | None) -> Creature:
        return Creature(
            article_id=1,
            title="Demon",
            article="a",
            name="Demon",
            plural="Demons",
            library_race="Demon",
            creature_class="Demons",
            type_primary="Demons",
            type_secondary=None,
            bestiary_class="Demon",
            bestiary_level="Hard",
            bestiary_occurrence="Common",
            bosstiary_class=None,
            hitpoints=8200,
            experience=6000,
            armor=44,
            mitigation=1.52,
            speed=128,
            runs_at=0,
            summon_cost=0,
            convince_cost=0,
            illusionable=False,
            pushable=False,
            push_objects=True,
            sees_invisible=True,
            paralysable=False,
            spawn_type=None,
            is_boss=False,
            cooldown=None,
            modifier_physical=75,
            modifier_earth=60,
            modifier_fire=0,
            modifier_energy=50,
            modifier_ice=112,
            modifier_death=80,
            modifier_holy=112,
            modifier_drown=0,
            modifier_lifedrain=0,
            modifier_healing=None,
            walks_through="Fire, Energy, Poison",
            walks_around=None,
            location="Demona, Edron Demon Forge.",
            race_id=race_id,
            version="4.0",
            status="active",
            timestamp=datetime.datetime.fromisoformat("2024-07-29T16:37:09+00:00"),
        )

    def test_creature_race_id_round_trip(self):
        self._creature(35).insert(self.conn)

        loaded = Creature.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual(35, loaded.race_id)

    def test_creature_race_id_round_trip_none(self):
        self._creature(None).insert(self.conn)

        loaded = Creature.get_one_by_field(self.conn, "article_id", 1)

        self.assertIsNone(loaded.race_id)
