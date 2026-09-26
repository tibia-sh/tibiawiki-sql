# Changed by tibia.sh in 2026. See "About this copy" in README.md.
import datetime
import unittest

from tests import load_resource
from tibiawikisql.api import Article
from tibiawikisql.models import Creature
from tibiawikisql.parsers.creature import CreatureParser, parse_abilities, parse_maximum_damage


class TestCreatureParser(unittest.TestCase):

    def test_parse_mitigation_as_float(self):
        mitigation_parser = CreatureParser.attribute_map["mitigation"]

        self.assertEqual(1.5, mitigation_parser({"mitigation": "1.5"}))

    def test_parse_abilities_with_template(self):
        ability_content = ("{{Ability List|{{Melee|0-500}}|{{Ability|Great Fireball|150-250|fire|scene="
                           "{{Scene|spell=5sqmballtarget|effect=Fireball Effect|caster=Demon|look_direction="
                           "|effect_on_target=Fireball Effect|missile=Fire Missile|missile_direction=south-east"
                           "|missile_distance=5/5|edge_size=32}}}}|{{Ability|[[Great Energy Beam]]|300-480|lifedrain"
                           "|scene={{Scene|spell=8sqmbeam|effect=Blue Electricity Effect|caster=Demon|"
                           "look_direction=east}}}}|{{Ability|Close-range Energy Strike|210-300|energy}}|"
                           "{{Ability|Mana Drain|30-120|manadrain}}|{{Healing|range=80-250}}|{{Ability|"
                           "Shoots [[Fire Field]]s||fire}}|{{Ability|Distance Paralyze||paralyze}}|"
                           "{{Summon|Fire Elemental|1}}}}")

        result = parse_abilities(ability_content)

        self.assertEqual(9, len(result))


    def test_parse_abilities_no_template(self):
        ability_content = ("[[Melee]] (0-220), [[Physical Damage|Smoke Strike]] (0-200; does [[Physical Damage]]), "
                           "[[Life Drain|Smoke Wave]] (0-380; does [[Life Drain]]), [[Paralyze|Ice Wave]] (very strong "
                           "[[Paralyze]]), [[Avalanche (rune)|Avalanche]] (0-240) or (strong [[Paralyze]]), "
                           "[[Berserk|Ice Berserk]] (0-120), [[Paralyze|Smoke Berserk]] (strong [[Paralyze]]), "
                           "[[Self-Healing]] (around 200 [[Hitpoints]]), [[Haste]].")

        result = parse_abilities(ability_content)

        self.assertEqual(1, len(result))
        self.assertEqual("no_template", result[0]["element"])

    def test_parse_parse_abilities_mixed(self):
        ability_content = "{{Ability List|{{Melee|0-500}}|Plain text}}"

        result = parse_abilities(ability_content)

        self.assertEqual(2, len(result))
        self.assertEqual("Plain text", result[-1]["name"])
        self.assertEqual("plain_text", result[-1]["element"])

    def test_parse_parse_abilities_empty(self):
        ability_content = ""

        result = parse_abilities(ability_content)

        self.assertEqual(0, len(result))

    def test_parse_max_damage_template(self):
        max_damage_content = "{{Max Damage|physical=500|fire=250|lifedrain=480|energy=300|manadrain=120|summons=250}}"

        result = parse_maximum_damage(max_damage_content)

        self.assertIsInstance(result, dict)
        self.assertEqual(500, result["physical"])
        self.assertEqual(250, result["fire"])
        self.assertEqual(480, result["lifedrain"])
        self.assertEqual(300, result["energy"])
        self.assertEqual(120, result["manadrain"])
        self.assertEqual(250, result["summons"])
        self.assertEqual(1530, result["total"])

    def test_parse_max_damage_no_template(self):
        max_damage_content = "1500 (2000 with UE)"

        result = parse_maximum_damage(max_damage_content)

        self.assertIsInstance(result, dict)
        self.assertEqual(2000, result["total"])

    def test_parse_max_damage_no_template_no_number(self):
        max_damage_content = "Unknown."

        result = parse_maximum_damage(max_damage_content)

        self.assertEqual({}, result)

    def test_parse_max_damage_empty(self):
        max_damage_content = ""

        result = parse_maximum_damage(max_damage_content)

        self.assertEqual({}, result)


class TestCreatureParserRaceId(unittest.TestCase):
    def _parse(self, content: str) -> Creature:
        article = Article(
            article_id=1,
            title="Demon",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        return CreatureParser.from_article(article)

    def _edited(self, old: str, new: str) -> str:
        content = load_resource("content_creature.txt")
        self.assertIn(old, content)
        return content.replace(old, new)

    def test_creature_race_id(self):
        creature = self._parse(load_resource("content_creature.txt"))

        self.assertEqual(35, creature.race_id)

    def test_creature_race_id_none_without_line(self):
        creature = self._parse(self._edited("| race_id        = 35\n", ""))

        self.assertIsNone(creature.race_id)

    def test_creature_race_id_none_when_empty(self):
        creature = self._parse(self._edited("| race_id        = 35", "| race_id        ="))

        self.assertIsNone(creature.race_id)
        self.assertEqual(128, creature.speed)

    def test_creature_race_id_none_when_not_numeric(self):
        creature = self._parse(self._edited("| race_id        = 35", "| race_id        = abc"))

        self.assertIsNone(creature.race_id)
