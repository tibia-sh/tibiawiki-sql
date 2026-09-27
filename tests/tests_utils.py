# Changed by tibia.sh in 2026. See "About this copy" in README.md.
import unittest

import datetime

import tibiawikisql
from tests import load_resource
from tibiawikisql.utils import (clean_links, client_color_to_rgb, parse_boolean, parse_client_id, parse_currency,
                                parse_first_integer, parse_float, parse_integer,
                                parse_date, parse_loot_statistics, parse_min_max, parse_sounds,
                                parse_weapon_proficiency_name, parse_weapon_proficiency_tables)


class TestUtils(unittest.TestCase):
    def test_clean_links(self):
        # Regular link
        self.assertEqual(clean_links("[[Holy Damage]]"), "Holy Damage")
        # Named link
        self.assertEqual(clean_links("[[Curse (Charm)|Curse]]"), "Curse")
        # Comments
        self.assertEqual(clean_links("Hello <!-- world -->"), "Hello")

    def test_clean_links_list(self):
        content = """* The new ice islands [[Grimlund]], [[Helheim]], [[Hrodmir]], [[Nibelor]], [[Okolnir]] and [[Tyrsung]] were added
** A new hometown, the city of [[Svargrond]], in [[Hrodmir]].
* New creatures such as the [[Chakoyas]], [[Barbarians]] and more ice themed creatures.
* The [[Svargrond Arena]] was added.
* Many vocation balancing changes
** Magic damage formula changes.
** Added over 60 new weapons and ammunition.
** Added vocation and level requirements to weapons."""

        clean_content = clean_links(content)

        expected = """- The new ice islands Grimlund, Helheim, Hrodmir, Nibelor, Okolnir and Tyrsung were added
	- A new hometown, the city of Svargrond, in Hrodmir.
- New creatures such as the Chakoyas, Barbarians and more ice themed creatures.
- The Svargrond Arena was added.
- Many vocation balancing changes
	- Magic damage formula changes.
	- Added over 60 new weapons and ammunition.
	- Added vocation and level requirements to weapons."""
        self.assertEqual(expected, clean_content)

    def test_parse_boolean(self):
        self.assertTrue(parse_boolean("yes"))
        self.assertFalse(parse_boolean("no"))
        self.assertFalse(parse_boolean("--"))
        self.assertTrue(parse_boolean("--", True))
        self.assertTrue(parse_boolean("no", invert=True))

    def test_parse_float(self):
        self.assertEqual(parse_float("1.45"), 1.45)
        self.assertEqual(parse_float("?"), 0.0)
        self.assertIsNone(parse_float("?", None))
        self.assertEqual(parse_float("2.55%"), 2.55)

    def test_parse_integer(self):
        self.assertEqual(parse_integer("100 tibia coins"), 100)
        self.assertEqual(parse_integer("10056"), 10056)
        self.assertEqual(parse_integer("--"), 0)

    def test_parse_integer_thousands_separator(self):
        self.assertEqual(50000, parse_integer("50,000"))
        self.assertEqual(1000000, parse_integer("1,000,000"))
        self.assertEqual(4000, parse_integer("4,000 gp"))
        self.assertEqual(12500, parse_integer("12,500"))
        self.assertEqual(-1000, parse_integer("-1,000"))

    def test_parse_integer_not_thousands_separator(self):
        self.assertEqual(12, parse_integer("12,34"))
        self.assertEqual(1, parse_integer("1,2345"))
        self.assertIsNone(parse_integer("Negotiable", None))

    def test_parse_first_integer(self):
        self.assertEqual(629, parse_first_integer("629,630,631"))
        self.assertEqual(-5, parse_first_integer("-5 and 7"))
        self.assertEqual(0, parse_first_integer("--"))
        self.assertIsNone(parse_first_integer("--", None))

    def test_parse_client_id(self):
        self.assertEqual(35, parse_client_id("35"))
        self.assertEqual(35, parse_client_id(" 35 <!-- note -->"))
        self.assertEqual(644, parse_client_id("<!-- 7 -->644"))
        self.assertEqual(421, parse_client_id("421,437,438,747"))
        self.assertEqual(35, parse_client_id("35<!-- note -->7"))
        self.assertIsNone(parse_client_id("<!-- objectID: 51952-->"))
        self.assertIsNone(parse_client_id("\n<!-- objectID: 51952-->\n"))
        self.assertIsNone(parse_client_id("<!-- 51952"))
        self.assertEqual(35, parse_client_id("35 <!-- note"))
        self.assertEqual(35, parse_client_id("<!-- a --> 35 <!-- b"))
        self.assertIsNone(parse_client_id("<!-- a --> <!-- 35"))
        self.assertEqual(35, parse_client_id("<nowiki><!-- note --></nowiki>35"))
        self.assertEqual(35, parse_client_id("<nowiki><!--</nowiki>35"))
        self.assertIsNone(parse_client_id("<span><!-- 51952</span>"))
        self.assertIsNone(parse_client_id("{{x|<!-- 51952}}"))
        self.assertIsNone(parse_client_id("[[x|<!-- 51952]]"))
        self.assertIsNone(parse_client_id("<span><!--</span>35"))
        self.assertEqual(35, parse_client_id("<pre><!--</pre>35"))
        self.assertEqual(35, parse_client_id("<span><nowiki><!--</nowiki></span>35"))
        self.assertEqual(35, parse_client_id("<span><pre><!--</pre></span>35"))
        self.assertEqual(35, parse_client_id("<span><NOWIKI ><!--</NOWIKI ></span>35"))
        self.assertEqual(51952, parse_client_id("<span><nowiki><!-- 51952 --></nowiki></span>35"))
        self.assertEqual(35, parse_client_id('<nowiki title="<pre>x</pre>">y</nowiki>35'))
        self.assertEqual(35, parse_client_id('<pre title="<nowiki><!--</nowiki>">y</pre>35'))
        self.assertEqual(35, parse_client_id('<pre title="<nowiki>x</nowiki>">35</pre>'))
        self.assertIsNone(parse_client_id("abc"))
        self.assertIsNone(parse_client_id(""))

    def test_parse_date_ignores_comma_separated_time(self):
        self.assertEqual(datetime.date(2026, 1, 27), parse_date("January 27, 2026, 16:00"))

    def test_parse_currency_link_target(self):
        self.assertEqual("Silver Token", parse_currency("[[Silver Token]]s"))
        self.assertEqual("Hunting Task Points", parse_currency("{{Icon|Hunting Task Points}} [[Hunting Task Points]]"))
        self.assertEqual("Theons", parse_currency("[[theons]]"))
        self.assertEqual("Silver Token", parse_currency("[[Silver_Token|tokens]]"))

    def test_parse_currency_section_link_display_text(self):
        self.assertEqual("Hunting Task Points", parse_currency("[[Task Board#Hunting Task Points|Hunting Task Points]]"))
        self.assertEqual("Hunting Task Points", parse_currency("[[Task Board#Hunting Task Points]]"))

    def test_parse_currency_gold(self):
        self.assertEqual("Gold Coin", parse_currency("gp"))
        self.assertEqual("Gold Coin", parse_currency("{{GP}}"))

    def test_parse_currency_plain_text(self):
        self.assertEqual("Event Points", parse_currency("Event Points"))

    def test_parse_currency_coin_templates(self):
        self.assertEqual("Tibia Coins", parse_currency("{{TC}}"))
        self.assertEqual("Tournament Coins", parse_currency("{{tC3}}"))

    def test_parse_currency_empty(self):
        self.assertIsNone(parse_currency(""))
        self.assertIsNone(parse_currency("  "))
        self.assertIsNone(parse_currency("<!-- none -->"))

    def test_parse_currency_skips_file_and_category_links(self):
        self.assertEqual("Theons", parse_currency("[[File:Theons.gif]] [[Theons]]"))
        self.assertEqual("Theons", parse_currency("[[image:Theons.gif|16px]] [[Theons]]"))
        self.assertEqual("Theons", parse_currency("[[Category:Currencies]] [[Theons]]"))

    def test_parse_currency_template_without_parameters(self):
        self.assertEqual("Foo", parse_currency("{{Foo}}"))
        self.assertEqual("Tibia Coins", parse_currency("{{ TC }}"))
        self.assertEqual("Tournament Coins", parse_currency("{{ tC3 }}"))
        self.assertEqual("about Tibia Coins", parse_currency("about {{TC}}"))

    def test_parse_currency_nested_templates(self):
        self.assertEqual("Bar", parse_currency("{{Foo|{{Bar}}}}"))
        self.assertEqual("x", parse_currency("{{Foo|{{Bar|x}}}}"))
        self.assertEqual("Bar", parse_currency("{{ {{Bar}} }}"))
        self.assertEqual("A", parse_currency("[[a|{{b}}]]"))

    def test_parse_currency_never_raises(self):
        for value in ("{{A|{}}{{B|{x}}}}", "{{A|{{}}{{B|x}}}}", "{{A|{{B|{}}{{C|{x}}}}}}", "{{A|{{B|{}}}}{{C|{x}}}}"):
            with self.subTest(value=value):
                # The braces left by the templates are text, not parsed again.
                self.assertEqual("{{x}}", parse_currency(value))
        self.assertIsNone(parse_currency("[[File:A|[[File:B]]]]"))
        self.assertEqual("{{Foo}}", parse_currency("<nowiki>{{Foo}}</nowiki>"))

    def test_parse_currency_none_for_empty_links(self):
        for value in ("[[]]", "[[#]]", "[[|]]", "[[_]]", "[[#|]]", "[[Task Board# |]]"):
            with self.subTest(value=value):
                self.assertIsNone(parse_currency(value))

    def test_parse_currency_none_with_only_skipped_links(self):
        self.assertIsNone(parse_currency("[[Category:Currencies]]"))
        self.assertIsNone(parse_currency("[[File:Theons.gif]]"))
        self.assertIsNone(parse_currency("[[Image:Theons.gif]] <!-- x -->"))
        self.assertEqual("Theons", parse_currency("[[File:Theons.gif]] Theons"))

    def test_parse_currency_ignores_formatting(self):
        self.assertEqual("Gold Coin", parse_currency("<span>gp</span>"))
        self.assertEqual("Gold Coin", parse_currency("gp <!-- x -->"))
        self.assertEqual("Gold Coin", parse_currency("<span>{{GP}}</span>"))
        self.assertIsNone(parse_currency("?"))

    def test_parse_min_max(self):
        self.assertEqual(parse_min_max("5-20"), (5, 20))
        self.assertEqual(parse_min_max("50"), (0, 50))
        self.assertEqual((0, 1000), parse_min_max("1,000"))

    def test_parse_sounds(self):
        sound_string = "{{Sound List|Sound 1|Sound 2|Sound 3}}"
        sounds = parse_sounds(sound_string)
        self.assertEqual(len(sounds), 3)

        self.assertFalse(parse_sounds("?"))

    def test_parse_loot_statistics(self):
        content = load_resource("content_loot_statistics.txt")
        kills, loot_statistics = parse_loot_statistics(content)
        self.assertEqual(36488, kills)
        self.assertEqual(34, len(loot_statistics))

        kills, _ = parse_loot_statistics(content.replace("|kills=36488", "|kills=1,234"))
        self.assertEqual(1234, kills)

        kills, loot_statistics = parse_loot_statistics("Something else")
        self.assertEqual(kills, 0)
        self.assertFalse(loot_statistics)

    def test_client_light_to_rgb(self):
        self.assertEqual(client_color_to_rgb(-1), 0)
        self.assertEqual(client_color_to_rgb(0), 0)
        self.assertEqual(client_color_to_rgb(3), 0x99)
        self.assertEqual(client_color_to_rgb(215), 0xffffff)
        self.assertEqual(client_color_to_rgb(216), 0)

    def test_parse_weapon_proficiency_name(self):
        content = load_resource("content_weapon_proficiency_name.txt")
        mappings = parse_weapon_proficiency_name(content)

        self.assertEqual(2, len(mappings))
        self.assertEqual("Sanguine 1H Axe", mappings["Amber Axe"])
        self.assertEqual("Sanguine 1H Club", mappings["Amber Cudgel"])
        self.assertNotIn("#default", mappings)

    def test_parse_weapon_proficiency_name_without_switch(self):
        mappings = parse_weapon_proficiency_name("== Not a switch ==")
        self.assertEqual({}, mappings)

    def test_parse_weapon_proficiency_tables(self):
        content = load_resource("content_weapon_proficiency_tables.txt")
        tables = parse_weapon_proficiency_tables(content)

        self.assertIn("Sanguine 1H Axe", tables)
        self.assertIn("Sanguine 1H Club", tables)
        self.assertIn(1, tables["Sanguine 1H Axe"])
        self.assertIn(2, tables["Sanguine 1H Axe"])

        perks = tables["Sanguine 1H Axe"][2]
        self.assertEqual(3, len(perks))
        self.assertIsNone(perks[0]["icon"])
        self.assertEqual("Special Icon", perks[1]["icon"])

    def test_parse_weapon_proficiency_tables_effect_fallback(self):
        content = """===Sanguine 1H Axe===
{{Weapon Proficiency Table
|perk_1 =
{{Weapon Proficiency Button |skill_image=Axe Skill Bonus|icon=|effect=Fallback Effect}}
|perk_x =
{{Weapon Proficiency Button |skill_image=Ignored|icon=|text=Ignored}}
}}"""
        tables = parse_weapon_proficiency_tables(content)
        self.assertIn("Sanguine 1H Axe", tables)
        self.assertIn(1, tables["Sanguine 1H Axe"])
        self.assertEqual([1], list(tables["Sanguine 1H Axe"].keys()))
        self.assertEqual("Fallback Effect", tables["Sanguine 1H Axe"][1][0]["effect"])

    def test_parse_weapon_proficiency_tables_level_two_headings(self):
        content = """==Sanguine 1H Axe==
{{Weapon Proficiency Table
|perk_1 =
{{Weapon Proficiency Button |skill_image=Axe Skill Bonus|icon=|text=+1 Axe Fighting}}
}}"""
        tables = parse_weapon_proficiency_tables(content)
        self.assertIn("Sanguine 1H Axe", tables)
        self.assertIn(1, tables["Sanguine 1H Axe"])
        self.assertEqual("+1 Axe Fighting", tables["Sanguine 1H Axe"][1][0]["effect"])

    def test_version_is_tibia_sh_build(self):
        # A release PR sets X.Y.Z+tibiash.N. An upstream sync takes upstream's bare X.Y.Z until the next release.
        self.assertRegex(tibiawikisql.__version__, r"\A[0-9]+\.[0-9]+\.[0-9]+(\+tibiash\.[0-9]+)?\Z")
