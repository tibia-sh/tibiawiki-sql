# Changed by tibia.sh in 2026. See "About this copy" in README.md.
import datetime
import unittest

from tests import load_resource
from tibiawikisql.api import Article
from tibiawikisql.models import Creature
from tibiawikisql.parsers.creature import CreatureParser, parse_abilities, parse_mana_cost, parse_maximum_damage


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

    def test_parse_max_damage_thousands_separator(self):
        self.assertEqual({"total": 1000}, parse_maximum_damage("1,000"))
        self.assertEqual({"total": 1300}, parse_maximum_damage("1,300+"))

    def test_parse_max_damage_range(self):
        self.assertEqual({"total": 1200}, parse_maximum_damage("500-1,200"))
        self.assertEqual({"total": 100}, parse_maximum_damage("50-100"))
        self.assertEqual({"total": 1000}, parse_maximum_damage("600-1000?"))

    def test_parse_max_damage_leading_minus_is_a_sign(self):
        self.assertEqual({"total": 1000}, parse_maximum_damage("-1500 or 1000"))

    def test_parse_max_damage_no_template_no_number(self):
        max_damage_content = "Unknown."

        result = parse_maximum_damage(max_damage_content)

        self.assertEqual({}, result)

    def test_parse_max_damage_empty(self):
        max_damage_content = ""

        result = parse_maximum_damage(max_damage_content)

        self.assertEqual({}, result)


class TestCreatureParserNumbers(unittest.TestCase):
    def test_creature_thousands_separator(self):
        article = Article(
            article_id=1,
            title="Brain Head",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_creature_brain_head.txt"),
        )

        creature = CreatureParser.from_article(article)

        self.assertEqual(50000, creature.experience)
        self.assertEqual(230000, creature.hitpoints)
        self.assertEqual(1000, creature.max_damage.total)


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

    def test_creature_race_id_none_when_only_a_comment(self):
        creature = self._parse(self._edited("| race_id        = 35", "| race_id        = <!-- objectID: 51952-->"))

        self.assertIsNone(creature.race_id)

    def test_creature_race_id_ignores_a_trailing_comment(self):
        creature = self._parse(self._edited("| race_id        = 35", "| race_id        = 35 <!-- note -->"))

        self.assertEqual(35, creature.race_id)


class TestCreatureParserKnownValues(unittest.TestCase):
    def _parse(self, content: str) -> Creature:
        article = Article(
            article_id=1,
            title="Dragon",
            timestamp=datetime.datetime.fromisoformat("2026-06-25T06:40:57+00:00"),
            content=content,
        )

        return CreatureParser.from_article(article)

    def _edited(self, old: str, new: str) -> Creature:
        content = load_resource("content_creature_dragon.txt")
        self.assertIn(old, content)
        return self._parse(content.replace(old, new))

    def test_dragon(self):
        creature = self._parse(load_resource("content_creature_dragon.txt"))

        self.assertIs(False, creature.paralysable)
        self.assertEqual(0, creature.summon_cost)
        self.assertEqual(0, creature.convince_cost)
        self.assertEqual(1000, creature.hitpoints)
        self.assertEqual(700, creature.experience)
        self.assertEqual(25, creature.armor)
        self.assertEqual(1.56, creature.mitigation)
        self.assertEqual(86, creature.speed)
        self.assertEqual(300, creature.runs_at)
        self.assertIs(True, creature.illusionable)
        self.assertIs(False, creature.pushable)
        self.assertIs(True, creature.push_objects)
        self.assertIs(True, creature.sees_invisible)
        self.assertIs(False, creature.is_boss)
        self.assertEqual(0, creature.modifier_fire)
        self.assertEqual(20, creature.modifier_earth)

    def test_paralysable_when_not_immune(self):
        creature = self._edited("| paraimmune     = yes", "| paraimmune     = no")

        self.assertIs(True, creature.paralysable)

    def test_paralysable_unknown(self):
        creature = self._edited("| paraimmune     = yes", "| paraimmune     = ?")

        self.assertIsNone(creature.paralysable)

    def test_paralysable_absent(self):
        creature = self._edited("| paraimmune     = yes\n", "")

        self.assertIsNone(creature.paralysable)

    def test_armor_unknown(self):
        creature = self._edited("| armor          = 25", "| armor          = ?")

        self.assertIsNone(creature.armor)

    def test_armor_zero(self):
        creature = self._edited("| armor          = 25", "| armor          = 0")

        self.assertEqual(0, creature.armor)

    def test_stats_unknown(self):
        creature = self._parse(
            load_resource("content_creature_dragon.txt")
            .replace("| hp             = 1000", "| hp             = ?")
            .replace("| exp            = 700", "| exp            =")
            .replace("| mitigation     = 1.56", "| mitigation     = ?")
            .replace("| speed          = 86", "| speed          = --"),
        )

        self.assertIsNone(creature.hitpoints)
        self.assertIsNone(creature.experience)
        self.assertIsNone(creature.mitigation)
        self.assertIsNone(creature.speed)

    def test_runs_at_colour(self):
        creature = self._edited("| runsat         = 300", "| runsat         = deep red")

        self.assertIsNone(creature.runs_at)

    def test_runs_at_zero(self):
        creature = self._edited("| runsat         = 300", "| runsat         = 0")

        self.assertEqual(0, creature.runs_at)

    def test_summon_unknown(self):
        creature = self._edited("| summon         = --", "| summon         = ?")

        self.assertIsNone(creature.summon_cost)

    def test_convince_yes(self):
        creature = self._edited("| convince       = --", "| convince       = yes")

        self.assertIsNone(creature.convince_cost)

    def test_summon_number(self):
        creature = self._edited("| summon         = --", "| summon         = 1,000")

        self.assertEqual(1000, creature.summon_cost)

    def test_parse_mana_cost(self):
        self.assertEqual(0, parse_mana_cost("--"))
        self.assertEqual(0, parse_mana_cost(" No "))
        self.assertEqual(0, parse_mana_cost("0"))
        self.assertEqual(390, parse_mana_cost("390"))
        self.assertEqual(390, parse_mana_cost("390 <!-- note -->"))
        self.assertEqual(0, parse_mana_cost("-- <!-- note -->"))
        self.assertIsNone(parse_mana_cost("?"))
        self.assertIsNone(parse_mana_cost(""))
        self.assertIsNone(parse_mana_cost("yes"))
        self.assertIsNone(parse_mana_cost("<!-- 390 -->"))

    def test_push_objects_uncertain(self):
        creature = self._edited("| pushobjects    = Yes", "| pushobjects    = no?")

        self.assertIsNone(creature.push_objects)

    def test_flags_unknown(self):
        creature = self._parse(
            load_resource("content_creature_dragon.txt")
            .replace("| illusionable   = yes", "| illusionable   = ?")
            .replace("| pushable       = No", "| pushable       =")
            .replace("| senseinvis     = yes\n", ""),
        )

        self.assertIsNone(creature.illusionable)
        self.assertIsNone(creature.pushable)
        self.assertIsNone(creature.sees_invisible)

    def test_experience_only_in_a_comment(self):
        article = Article(
            article_id=109773,
            title="Bonelord Totem",
            timestamp=datetime.datetime.fromisoformat("2026-07-13T17:46:07+00:00"),
            content=load_resource("content_creature_bonelord_totem.txt"),
        )

        creature = CreatureParser.from_article(article)

        self.assertIsNone(creature.experience)
        self.assertIsNone(creature.hitpoints)
        self.assertEqual(0, creature.runs_at)
        self.assertEqual(0, creature.modifier_fire)

    def test_stat_ignores_a_trailing_comment(self):
        creature = self._edited("| hp             = 1000", "| hp             = 1000 <!-- 2000 -->")

        self.assertEqual(1000, creature.hitpoints)

    def test_stat_hidden_by_an_unclosed_comment(self):
        creature = self._edited("| hp             = 1000", "| hp             = <!-- 1000")

        self.assertIsNone(creature.hitpoints)

    def test_modifier_unknown(self):
        creature = self._edited("| fireDmgMod     = 0%", "| fireDmgMod     = ?")

        self.assertIsNone(creature.modifier_fire)

    def test_modifier_absent(self):
        creature = self._edited("| fireDmgMod     = 0%\n", "")

        self.assertIsNone(creature.modifier_fire)
