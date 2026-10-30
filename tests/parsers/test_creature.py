# Changed by tibia.sh in 2026. See "About this copy" in README.md.
import datetime
import unittest

from tests import load_resource
from tibiawikisql.api import Article
from tibiawikisql.models import Creature, CreatureDrop
from tibiawikisql.parsers.creature import (
    CreatureParser,
    format_debuff_effect,
    parse_abilities,
    parse_mana_cost,
    parse_maximum_damage,
)


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
        self.assertIsNone(creature.attack_type)
        self.assertIsNone(creature.uses_spells)

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

    def test_flag_ignores_a_trailing_comment(self):
        creature = self._edited("| pushable       = No", "| pushable       = yes <!-- x -->")

        self.assertIs(True, creature.pushable)

    def test_paralysable_ignores_a_trailing_comment(self):
        creature = self._edited("| paraimmune     = yes", "| paraimmune     = yes <!-- x -->")

        self.assertIs(False, creature.paralysable)

    def test_flag_typo(self):
        creature = self._edited("| pushable       = No", "| pushable       = yse")

        self.assertIsNone(creature.pushable)

    def test_mitigation_only_in_a_comment(self):
        creature = self._edited("| mitigation     = 1.56", "| mitigation     = <!-- 1.56 -->")

        self.assertIsNone(creature.mitigation)

    def test_stat_absent(self):
        creature = self._edited("| armor          = 25\n", "")

        self.assertIsNone(creature.armor)

    def test_summon_absent(self):
        creature = self._edited("| summon         = --\n", "")

        self.assertIsNone(creature.summon_cost)

    def test_convince_no(self):
        creature = self._edited("| convince       = --", "| convince       = no")

        self.assertEqual(0, creature.convince_cost)

    def test_attack_type_and_uses_spells(self):
        creature = self._parse(load_resource("content_creature_dragon.txt"))

        self.assertEqual("melee", creature.attack_type)
        self.assertIs(True, creature.uses_spells)

    def test_attack_type_unknown(self):
        creature = self._edited("| attacktype   = Melee", "| attacktype   = ?")

        self.assertIsNone(creature.attack_type)

    def test_attack_type_absent(self):
        creature = self._edited("| attacktype   = Melee\n", "")

        self.assertIsNone(creature.attack_type)

    def test_attack_type_ignores_a_trailing_comment(self):
        creature = self._edited("| attacktype   = Melee", "| attacktype   = Distance <!-- Melee? -->")

        self.assertEqual("distance", creature.attack_type)

    def test_uses_spells_no(self):
        creature = self._edited("| usespells    = yes", "| usespells    = no")

        self.assertIs(False, creature.uses_spells)

    def test_uses_spells_unknown(self):
        creature = self._edited("| usespells    = yes", "| usespells    = ?")

        self.assertIsNone(creature.uses_spells)

    def test_uses_spells_absent(self):
        creature = self._edited("| usespells    = yes\n", "")

        self.assertIsNone(creature.uses_spells)


class TestCreatureParserLoot(unittest.TestCase):
    GOLD_COIN = " |{{Loot Item|1-105|Gold Coin|common}}"

    def _parse(self, content: str) -> Creature:
        article = Article(
            article_id=1,
            title="Dragon",
            timestamp=datetime.datetime.fromisoformat("2026-06-25T06:40:57+00:00"),
            content=content,
        )

        return CreatureParser.from_article(article)

    def _gold_coin(self, line: str) -> CreatureDrop:
        content = load_resource("content_creature_dragon.txt")
        self.assertIn(self.GOLD_COIN, content)
        creature = self._parse(content.replace(self.GOLD_COIN, line))
        return next(drop for drop in creature.loot if drop.item_title == "Gold Coin")

    def test_rarity_with_amount(self):
        drop = self._gold_coin(" |{{Loot Item|1-3|Gold Coin|common}}")

        self.assertEqual("common", drop.rarity)
        self.assertEqual((1, 3), (drop.min, drop.max))

    def test_rarity_without_amount(self):
        drop = self._gold_coin(" |{{Loot Item|Gold Coin|common}}")

        self.assertEqual("common", drop.rarity)
        self.assertEqual((0, 1), (drop.min, drop.max))

    def test_rarity_absent(self):
        drop = self._gold_coin(" |{{Loot Item|1-3|Gold Coin}}")

        self.assertIsNone(drop.rarity)
        self.assertEqual((1, 3), (drop.min, drop.max))

    def test_rarity_absent_without_amount(self):
        drop = self._gold_coin(" |{{Loot Item|Gold Coin}}")

        self.assertIsNone(drop.rarity)
        self.assertEqual((0, 1), (drop.min, drop.max))

    def test_rarity_unknown(self):
        drop = self._gold_coin(" |{{Loot Item|1-3|Gold Coin|?}}")

        self.assertIsNone(drop.rarity)

    def test_rarity_typo(self):
        drop = self._gold_coin(" |{{Loot Item|1-3|Gold Coin|comon}}")

        self.assertIsNone(drop.rarity)

    def test_rarity_lower_cased_past_a_comment(self):
        drop = self._gold_coin(" |{{Loot Item|1-3|Gold Coin|Very Rare <!-- note -->}}")

        self.assertEqual("very rare", drop.rarity)

    def test_rarity_only_in_a_comment(self):
        drop = self._gold_coin(" |{{Loot Item|1-3|Gold Coin|<!-- common -->}}")

        self.assertIsNone(drop.rarity)

    def test_dragon_loot(self):
        creature = self._parse(load_resource("content_creature_dragon.txt"))

        # Item, min and max are pinned to what the parser gave before rarity was read.
        self.assertEqual(
            [
                ("Gold Coin", 1, 105, "common"),
                ("Dragon Ham", 1, 3, "common"),
                ("Steel Shield", 0, 1, "uncommon"),
                ("Crossbow", 0, 1, "uncommon"),
                ("Dragon's Tail", 0, 1, "uncommon"),
                ("Burst Arrow", 1, 10, "uncommon"),
                ("Longsword", 0, 1, "semi-rare"),
                ("Steel Helmet", 0, 1, "semi-rare"),
                ("Broadsword", 0, 1, "semi-rare"),
                ("Plate Legs", 0, 1, "semi-rare"),
                ("Green Dragon Leather", 0, 1, "rare"),
                ("Wand of Inferno", 0, 1, "rare"),
                ("Strong Health Potion", 0, 1, "rare"),
                ("Green Dragon Scale", 0, 1, "rare"),
                ("Double Axe", 0, 1, "rare"),
                ("Dragon Hammer", 0, 1, "rare"),
                ("Serpent Sword", 0, 1, "rare"),
                ("Small Diamond", 0, 1, "very rare"),
                ("Dragon Shield", 0, 1, "very rare"),
                ("Life Crystal", 0, 1, "very rare"),
                ("Dragonbone Staff", 0, 1, "very rare"),
                ("Dragon Trophy", 0, 1, "very rare"),
            ],
            [(drop.item_title, drop.min, drop.max, drop.rarity) for drop in creature.loot],
        )


class TestCreatureParserAbilities(unittest.TestCase):
    def _abilities(self, resource: str) -> list[tuple]:
        article = Article(
            article_id=1,
            title=resource,
            timestamp=datetime.datetime.fromisoformat("2026-10-30T00:00:00+00:00"),
            content=load_resource(resource),
        )
        creature = CreatureParser.from_article(article)
        return [
            (ability.name, ability.effect, ability.element, ability.condition, ability.condition_value)
            for ability in creature.abilities
        ]

    def _rows(self, content: str) -> list[tuple]:
        return [
            (row["name"], row.get("effect"), row["element"], row.get("condition"), row.get("condition_value"))
            for row in parse_abilities(content)
        ]

    def test_debuff_effect(self):
        self.assertEqual("value=50%; duration=10; flags=distance,melee",
                         format_debuff_effect("50%", "10", {"melee", "distance"}))

    def test_debuff_effect_orders_every_flag(self):
        self.assertEqual("flags=distance,melee,magic,shielding",
                         format_debuff_effect("", "", ["shielding", "magic", "melee", "distance"]))

    def test_debuff_effect_without_flags(self):
        self.assertEqual("value=50%; duration=10", format_debuff_effect("50%", "10", ()))

    def test_debuff_effect_without_value(self):
        self.assertEqual("duration=10; flags=melee", format_debuff_effect("", "10", {"melee"}))

    def test_debuff_effect_only_duration(self):
        self.assertEqual("duration=10", format_debuff_effect("", "10", ()))

    def test_debuff_effect_empty(self):
        self.assertEqual("", format_debuff_effect("", "", ()))

    def test_unchanged_without_new_kinds(self):
        # Pinned to what the parser gave before conditions were read: the new columns are the only change.
        self.assertEqual(
            [
                ("Melee", "0-500", "physical", None, None),
                ("Great Fireball", "150-250", "fire", None, None),
                ("Great Energy Beam", "300-480", "lifedrain", None, None),
                ("Close-range Energy Strike", "210-300", "energy", None, None),
                ("Mana Drain", "30-120", "manadrain", None, None),
                ("Self-Healing", "80-250", "healing", None, None),
                ("Shoots Fire Fields", "", "fire", None, None),
                ("Distance Paralyze", "", "paralyze", None, None),
                ("Fire Elemental", "1", "summon", None, None),
            ],
            self._abilities("content_creature.txt"),
        )

    def test_apocalypse(self):
        self.assertEqual(
            [
                ("Melee", "0-3098", "physical", "poisoned", 25),
                ("Armageddon", "450-4000?", "death", None, None),
                ("Great fireball", "100-900", "fire", None, None),
                ("Teleport Wave", "600-1100", "mana drain", None, None),
                ("Explosion Wave", "300-900", "physical", None, None),
                ("Explosion Exori", "100?-500?", "energy", None, None),
                ("Yellow Energy Beam", "500-1500", "energy", None, None),
                ("Death Beam", "300?-1000?", "death", None, None),
                ("Poisoning Beam", "up to 100 hp/turn", "physical", "poisoned", None),
                ("Paralyze", "210-220 points for 60 seconds", "physical", "slowed", None),
                # The unnamed yes after the name is not a flag.
                ("Debuff", "value=80-100%; duration=10", "debuff", None, None),
                ("Strong Haste", "", "haste", None, None),
                ("Weak Self-Healing", "2000-3000", "healing", None, None),
                ("Strong Self-Healing", "6000-10000", "healing", None, None),
            ],
            self._abilities("content_creature_apocalypse.txt"),
        )

    def test_gnorre_chyllson_debuff_flags_in_fixed_order(self):
        abilities = self._abilities("content_creature_gnorre_chyllson.txt")

        self.assertIn(("Debuff", "value=34-54%; duration=4; flags=distance,melee,shielding", "debuff", None, None),
                      abilities)
        self.assertIn(("Strong Haste", "", "haste", None, None), abilities)
        self.assertIn(("Paralyze", "?", "", "slowed", None), abilities)
        self.assertEqual(11, len(abilities))

    def test_abyssador_debuffs_differ_by_flags(self):
        abilities = self._abilities("content_creature_abyssador.txt")

        self.assertEqual(
            [("Debuff", "flags=distance", "debuff", None, None), ("Debuff", "flags=melee", "debuff", None, None)],
            [ability for ability in abilities if ability[2] == "debuff"],
        )
        self.assertIn(("Poisoning Bomb", "?", "physical", "poisoned", None), abilities)
        self.assertIn(("Melee", "0-1400+", "physical", None, None), abilities)
        self.assertEqual(13, len(abilities))

    def test_dreadbeast_unknown_poison(self):
        abilities = self._abilities("content_creature_dreadbeast.txt")

        self.assertEqual(
            [
                ("Melee", "0-50", "physical", "poisoned", None),
                ("Drown Hit", "70-90", "drowning", None, None),
                ("Life Drain Berserk", "0-80", "life drain", None, None),
                ("Poisoning Berserk", "up to 6?hp/turn", "earth", "poisoned", None),
                ("Debuff", "value=20-30%; duration=20secs; flags=melee", "debuff", None, None),
                ("Self-Healing", "35-65", "healing", None, None),
            ],
            abilities,
        )

    def test_son_of_verminor_outfits(self):
        abilities = self._abilities("content_creature_son_of_verminor.txt")

        self.assertEqual(
            [
                ("Rat", "no", "outfit", None, None),
                ("Larva", "no", "outfit", None, None),
                ("Scorpion", "no", "outfit", None, None),
                ("Slime", "no", "outfit", None, None),
            ],
            [ability for ability in abilities if ability[2] == "outfit"],
        )
        # The template reads poison=, not poisoned=.
        self.assertIn(("Melee", "0-460", "physical", None, None), abilities)
        self.assertEqual(9, len(abilities))

    def test_mimic_outfits(self):
        self.assertEqual(
            [
                ("Teddy Bear", "no", "outfit", None, None),
                ("Demon Shield", "no", "outfit", None, None),
                ("Warlord Sword", "no", "outfit", None, None),
                ("Piggy Bank", "no", "outfit", None, None),
                ("Green Frog", "no", "outfit", None, None),
                ("Treasure Chest", "no", "outfit", None, None),
                ("Rat", "no", "outfit", None, None),
                ("Slime", "no", "outfit", None, None),
                ("Pumpkin", "no", "outfit", None, None),
                ("Jewel Case", "no", "outfit", None, None),
                ("Giant Mushroom", "no", "outfit", None, None),
                ("Present Box", "no", "outfit", None, None),
                ("The Orb of Nature", "no", "outfit", None, None),
                ("Vashresamun", "no", "outfit", None, None),
                ("Turns Invisible", "very rare 1s", "invisible", None, None),
            ],
            self._abilities("content_creature_mimic.txt"),
        )

    def test_green_djinn_outfit_scene_is_not_a_name(self):
        abilities = self._abilities("content_creature_green_djinn.txt")

        self.assertEqual([("rat", "yes", "outfit", None, None)],
                         [ability for ability in abilities if ability[2] == "outfit"])
        self.assertIn(("Drunkenness", "30 seconds", "drunk", None, None), abilities)

    def test_outfit_named_parameters(self):
        rows = self._rows("{{Ability List|{{Outfit|victim=Yes|thing=Massive Fire Elemental|scene=|thing2=Football"
                          "|thing3=|thing4=Snowman}}}}")

        self.assertEqual(
            [
                ("Massive Fire Elemental", "yes", "outfit", None, None),
                ("Football", "yes", "outfit", None, None),
                ("Snowman", "yes", "outfit", None, None),
            ],
            rows,
        )

    def test_outfit_positional_extra_wins_over_named(self):
        rows = self._rows("{{Ability List|{{Outfit|no|Rat||Larva|thing2=Bug}}}}")

        self.assertEqual([("Rat", "no", "outfit", None, None), ("Larva", "no", "outfit", None, None)], rows)

    def test_haste_without_name(self):
        self.assertEqual([("Haste", "", "haste", None, None)], self._rows("{{Ability List|{{Haste}}}}"))

    def test_haste_named_name(self):
        self.assertEqual([("Strong Haste", "", "haste", None, None)],
                         self._rows("{{Ability List|{{Haste|name=[[Strong Haste]]}}}}"))

    def test_template_name_matches_exactly(self):
        self.assertEqual([], self._rows("{{Ability List|{{Haste\n  |scene=}}|{{haste}}}}"))

    def test_debuff_named_name(self):
        self.assertEqual([("Icicle", "value=50%; flags=melee,shielding", "debuff", None, None)],
                         self._rows("{{Ability List|{{Debuff|Icicle|shielding=yes|melee=yes|value=50%}}}}"))

    def test_debuff_without_parameters(self):
        self.assertEqual([("Debuff", "", "debuff", None, None)], self._rows("{{Ability List|{{Debuff}}}}"))

    def test_debuff_flag_not_yes(self):
        self.assertEqual([("Debuff", "flags=magic", "debuff", None, None)],
                         self._rows("{{Ability List|{{Debuff|melee=no|distance=|magic=Yes <!-- c -->}}}}"))

    def test_condition_unknown(self):
        self.assertEqual([("Bomb", "?", "physical", None, None)],
                         self._rows("{{Ability List|{{Ability|Bomb|condition=?}}}}"))

    def test_condition_ignores_comments_and_case(self):
        self.assertEqual([("Bomb", "?", "physical", "burning", None)],
                         self._rows("{{Ability List|{{Ability|Bomb|condition=Burning <!-- note -->}}}}"))

    def test_melee_condition(self):
        self.assertEqual([("Melee", "0-50", "physical", "bleeding", None)],
                         self._rows("{{Ability List|{{Melee|0-50|condition=bleeding}}}}"))

    def test_melee_empty_poison(self):
        self.assertEqual([("Melee", "0-50", "physical", None, None)],
                         self._rows("{{Ability List|{{Melee|0-50|poison= <!-- 5 -->}}}}"))

    def test_healing_and_summon_have_no_condition(self):
        self.assertEqual(
            [("Self-Healing", "10-20", "healing", None, None), ("Rat", "2", "summon", None, None)],
            self._rows("{{Ability List|{{Healing|range=10-20|condition=x}}|{{Summon|Rat|2|condition=x}}}}"),
        )

    def test_no_template_and_plain_text_have_no_condition(self):
        self.assertEqual([("Bites", None, "no_template", None, None)], self._rows("Bites"))
        self.assertEqual([("Melee", "0-5", "physical", None, None), ("Bites", None, "plain_text", None, None)],
                         self._rows("{{Ability List|{{Melee|0-5}}|Bites}}"))

    def test_debuff_effect_rejects_an_unknown_flag(self):
        with self.assertRaises(ValueError):
            format_debuff_effect("50%", "10", {"melee", "speed"})

    def test_outfit_named_victim_and_thing_win_over_positional(self):
        self.assertEqual([("Bug", "yes", "outfit", None, None)],
                         self._rows("{{Ability List|{{Outfit|no|Rat|victim=yes|thing=Bug}}}}"))

    def test_outfit_far_extra_is_read_without_a_range_scan(self):
        self.assertEqual([("Bug", "yes", "outfit", None, None), ("Rat", "yes", "outfit", None, None)],
                         self._rows("{{Ability List|{{Outfit|yes|Bug||thing1000000000=Rat}}}}"))

    def test_outfit_far_positional_extra(self):
        self.assertEqual([("Bug", "yes", "outfit", None, None), ("Rat", "yes", "outfit", None, None)],
                         self._rows("{{Ability List|{{Outfit|yes|Bug||1000000000=Rat}}}}"))

    def test_outfit_ignores_non_ascii_digits(self):
        self.assertEqual([("Bug", "yes", "outfit", None, None)],
                         self._rows("{{Ability List|{{Outfit|yes|Bug|thing²=Rat|²=Cat}}}}"))

    def test_outfit_ignores_a_number_too_long_to_read(self):
        self.assertEqual([("Bug", "yes", "outfit", None, None)],
                         self._rows("{{Ability List|{{Outfit|yes|Bug|thing" + "9" * 5000 + "=Rat}}}}"))

    def test_outfit_extras_with_a_gap(self):
        self.assertEqual([("A", "no", "outfit", None, None), ("B", "no", "outfit", None, None)],
                         self._rows("{{Ability List|{{Outfit|no|thing2=A|thing5=B}}}}"))
