import datetime
import sqlite3
import unittest

from tibiawikisql import schema
from tibiawikisql.models import Creature, CreatureAbility, CreatureDrop, Item, LocationCoordinate
from tibiawikisql.schema import ItemTable


class TestCreature(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        schema.create_tables(self.conn)

    def _creature(
        self,
        race_id: int | None,
        attack_type: str | None = None,
        uses_spells: bool | None = None,
        loot_statistics_kills: int | None = None,
        loot: list[CreatureDrop] | None = None,
    ) -> Creature:
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
            attack_type=attack_type,
            uses_spells=uses_spells,
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
            loot_statistics_kills=loot_statistics_kills,
            loot=loot or [],
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

    def test_creature_attack_type_and_uses_spells_round_trip(self):
        self._creature(35, attack_type="melee", uses_spells=False).insert(self.conn)

        loaded = Creature.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual("melee", loaded.attack_type)
        self.assertIs(False, loaded.uses_spells)

    def test_creature_attack_type_and_uses_spells_round_trip_none(self):
        self._creature(35).insert(self.conn)

        loaded = Creature.get_one_by_field(self.conn, "article_id", 1)

        self.assertIsNone(loaded.attack_type)
        self.assertIsNone(loaded.uses_spells)

    def test_creature_loot_statistics_kills_round_trip(self):
        self._creature(35, loot_statistics_kills=36488).insert(self.conn)

        loaded = Creature.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual(36488, loaded.loot_statistics_kills)

    def test_creature_loot_statistics_kills_round_trip_none(self):
        self._creature(35).insert(self.conn)

        loaded = Creature.get_one_by_field(self.conn, "article_id", 1)

        self.assertIsNone(loaded.loot_statistics_kills)

    def test_creature_drop_rarity_round_trip(self):
        timestamp = datetime.datetime.fromisoformat("2024-07-29T16:37:09+00:00")
        ItemTable.insert(self.conn, article_id=2, title="Gold Coin", name="Gold Coin", timestamp=timestamp)
        ItemTable.insert(self.conn, article_id=3, title="Demon Horn", name="Demon Horn", timestamp=timestamp)
        ItemTable.insert(self.conn, article_id=4, title="Talon", name="Talon", timestamp=timestamp)
        self._creature(35, loot=[
            CreatureDrop(item_title="Gold Coin", min=0, max=100, rarity="common"),
            CreatureDrop(item_id=3, item_title="Demon Horn", min=0, max=1, rarity="uncommon"),
            CreatureDrop(item_title="Talon", min=0, max=1),
        ]).insert(self.conn)

        loaded = Creature.get_one_by_field(self.conn, "article_id", 1)
        gold_coin = Item.get_one_by_field(self.conn, "article_id", 2)

        self.assertEqual(
            [("Gold Coin", 0, 100, "common"), ("Demon Horn", 0, 1, "uncommon"), ("Talon", 0, 1, None)],
            [(drop.item_title, drop.min, drop.max, drop.rarity) for drop in loaded.loot],
        )
        self.assertEqual(
            [("Demon", 0, 100, "common")],
            [(drop.creature_title, drop.min, drop.max, drop.rarity) for drop in gold_coin.dropped_by],
        )

    def test_creature_ability_condition_round_trip(self):
        creature = self._creature(35)
        creature.abilities = [
            CreatureAbility(
                name="Melee", effect="0-3098", element="physical", condition="poisoned", condition_value=25,
            ),
            CreatureAbility(name="Debuff", effect="value=80-100%; duration=10", element="debuff"),
        ]
        creature.insert(self.conn)

        loaded = Creature.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual(
            [
                ("Melee", "0-3098", "physical", "poisoned", 25),
                ("Debuff", "value=80-100%; duration=10", "debuff", None, None),
            ],
            [
                (ability.name, ability.effect, ability.element, ability.condition, ability.condition_value)
                for ability in loaded.abilities
            ],
        )

    def test_creature_location_coordinates_round_trip(self):
        creature = self._creature(35)
        creature.location_coordinates = [
            LocationCoordinate(x=32732, y=32601, z=14, label="here"),
            LocationCoordinate(x=32600, y=31802, z=4, label=None),
            LocationCoordinate(x=32448, y=32767, z=7, label="exactly here"),
        ]
        creature.insert(self.conn)

        loaded = Creature.get_one_by_field(self.conn, "article_id", 1)
        rows = self.conn.execute(
            "SELECT creature_id, x, y, z, label, position FROM creature_location_coordinate ORDER BY position",
        ).fetchall()

        self.assertEqual(creature.location_coordinates, loaded.location_coordinates)
        self.assertEqual(
            [
                (1, 32732, 32601, 14, "here", 0),
                (1, 32600, 31802, 4, None, 1),
                (1, 32448, 32767, 7, "exactly here", 2),
            ],
            [tuple(row) for row in rows],
        )

    def test_creature_location_coordinates_round_trip_none(self):
        self._creature(35).insert(self.conn)

        loaded = Creature.get_one_by_field(self.conn, "article_id", 1)

        self.assertEqual([], loaded.location_coordinates)
        self.assertEqual([], self.conn.execute("SELECT * FROM creature_location_coordinate").fetchall())
