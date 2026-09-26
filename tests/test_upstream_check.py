import re
import unittest

from scripts.upstream_check import (
    LIST_ISSUES,
    MAX_LINE,
    MAX_LINES,
    TITLE,
    build_body,
    decide,
    describe_base,
    find_issue,
    gh_commands,
    parse_commits,
)

COMMITS = ["abc1234 Fix creature parsing", "def5678 Add mounts"]
FENCE = re.compile(r"^ {0,3}(~{3,}|`{3,})")
BASE = "`main` at `abc1234`"
BOT = {"is_bot": True, "login": "app/github-actions"}


def fenced(body: str) -> tuple[list[int], list[str]]:
    lines = body.splitlines()
    fences = [i for i, line in enumerate(lines) if FENCE.match(line)]
    return fences, lines


class TestDecide(unittest.TestCase):
    def test_commits_without_issue_creates(self):
        self.assertEqual("create", decide(COMMITS, None))

    def test_commits_with_open_issue_updates(self):
        self.assertEqual("update", decide(COMMITS, "OPEN"))

    def test_commits_with_closed_issue_reopens(self):
        self.assertEqual("reopen", decide(COMMITS, "CLOSED"))

    def test_no_commits_with_open_issue_closes(self):
        self.assertEqual("close", decide([], "OPEN"))

    def test_no_commits_without_issue_does_nothing(self):
        self.assertEqual("none", decide([], None))

    def test_no_commits_with_closed_issue_does_nothing(self):
        self.assertEqual("none", decide([], "CLOSED"))

    def test_unknown_issue_state_is_rejected(self):
        with self.assertRaises(ValueError):
            decide(COMMITS, "MERGED")


class TestBuildBody(unittest.TestCase):
    def test_lists_every_commit_inside_one_fence(self):
        body = build_body(COMMITS, BASE)
        fences, lines = fenced(body)
        self.assertEqual(2, len(fences))
        self.assertEqual("~~~", lines[fences[0]])
        self.assertEqual("~~~", lines[fences[1]])
        self.assertEqual(COMMITS, lines[fences[0] + 1:fences[1]])

    def test_hostile_subject_stays_inert(self):
        subject = "abc1234 Close #12 ~~~ ping @user ~~~~ `` ```"
        body = build_body([subject, "def5678 ~~~"], BASE)
        fences, lines = fenced(body)
        self.assertEqual(2, len(fences))
        self.assertEqual(2, body.count("~~~"))
        inside = lines[fences[0] + 1:fences[1]]
        self.assertEqual(2, len(inside))
        self.assertIn("#12", inside[0])
        self.assertIn("@user", inside[0])
        outside = "\n".join(lines[:fences[0]] + lines[fences[1] + 1:])
        self.assertNotIn("#12", outside)
        self.assertNotIn("@user", outside)

    def test_subject_split_by_carriage_return_cannot_close_the_fence(self):
        body = build_body(["abc1234 first\r~~~\r#12 @user"], BASE)
        fences, lines = fenced(body)
        self.assertEqual(2, len(fences))
        self.assertEqual(1, fences[1] - fences[0] - 1)
        self.assertNotIn("\r", lines[fences[0] + 1])
        self.assertEqual(2, body.count("~~~"))

    def test_names_the_base(self):
        self.assertIn("Compared with `main` at `abc1234`.", build_body(COMMITS, BASE))

    def test_huge_subject_is_cut(self):
        body = build_body(["abc1234 " + "x" * 100_000], BASE)
        self.assertLess(len(body), 65_536)
        fences, lines = fenced(body)
        line = lines[fences[0] + 1]
        self.assertEqual(MAX_LINE, len(line))
        self.assertTrue(line.startswith("abc1234 xxx"))
        self.assertTrue(line.endswith("\u2026"))

    def test_line_at_the_limit_is_kept_whole(self):
        commit = "abc1234 " + "x" * (MAX_LINE - 8)
        fences, lines = fenced(build_body([commit], BASE))
        self.assertEqual([commit], lines[fences[0] + 1:fences[1]])

    def test_cut_never_rejoins_tildes(self):
        commit = "abc1234 " + "~" * 1000
        body = build_body([commit], BASE)
        self.assertEqual(2, body.count("~~~"))
        fences, lines = fenced(body)
        self.assertEqual(MAX_LINE, len(lines[fences[0] + 1]))

    def test_control_characters_are_dropped(self):
        body = build_body(["abc1234 a\x00b\x1b[31mc\x7fd\x85e\rf\tg"], BASE)
        fences, lines = fenced(body)
        self.assertEqual(["abc1234 ab[31mcdef\tg"], lines[fences[0] + 1:fences[1]])
        self.assertNotIn("\x00", body)

    def test_long_list_is_capped(self):
        commits = [f"{i:07x} Commit {i}" for i in range(1000)]
        body = build_body(commits, BASE)
        fences, lines = fenced(body)
        self.assertEqual(MAX_LINES, fences[1] - fences[0] - 1)
        self.assertEqual(commits[:MAX_LINES], lines[fences[0] + 1:fences[1]])
        self.assertIn("... and 700 more commits", lines[fences[1] + 1:])
        self.assertIn("has 1000 commit(s)", body)

    def test_worst_case_body_fits_an_issue(self):
        commits = ["abc1234 " + "~" * 100_000] * 1000
        self.assertLess(len(build_body(commits, BASE)), 65_536)

    def test_one_more_commit_is_singular(self):
        commits = [f"{i:07x} Commit {i}" for i in range(MAX_LINES + 1)]
        self.assertIn("... and 1 more commit\n", build_body(commits, BASE))


class TestDescribeBase(unittest.TestCase):
    def test_default_is_main(self):
        self.assertEqual("`main` at `abc1234`", describe_base("", "abc1234"))

    def test_manual_base_ref(self):
        self.assertEqual("`base_ref e46b2d3~3` at `4d8d6a6`", describe_base("e46b2d3~3", "4d8d6a6"))

    def test_sha_must_be_hex(self):
        for sha in ("", "abc123", "abc1234`", "ABC1234", "abc1234 x"):
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                describe_base("", sha)

    def test_base_ref_cannot_leave_its_code_span(self):
        for ref in ("a`b", "a b", "a\nb"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                describe_base(ref, "abc1234")


class TestParseCommits(unittest.TestCase):
    def test_skips_blank_lines(self):
        self.assertEqual(COMMITS, parse_commits("abc1234 Fix creature parsing\n\ndef5678 Add mounts\n"))

    def test_empty_file_has_no_commits(self):
        self.assertEqual([], parse_commits(""))


class TestFindIssue(unittest.TestCase):
    def test_list_command_filters_by_the_actions_bot(self):
        self.assertEqual(
            ["issue", "list", "--state", "all", "--author", "github-actions[bot]",
             "--json", "number,title,state,author"],
            LIST_ISSUES,
        )

    def test_matches_exact_title_only(self):
        issues = [
            {"number": 1, "title": TITLE + "!", "state": "OPEN", "author": BOT},
            {"number": 2, "title": TITLE.lower(), "state": "OPEN", "author": BOT},
            {"number": 3, "title": TITLE, "state": "CLOSED", "author": BOT},
        ]
        self.assertEqual(issues[2], find_issue(issues))

    def test_no_match_is_none(self):
        self.assertIsNone(find_issue([{"number": 1, "title": "Other", "state": "OPEN", "author": BOT}]))

    def test_two_matches_are_rejected(self):
        issues = [
            {"number": 1, "title": TITLE, "state": "OPEN", "author": BOT},
            {"number": 2, "title": TITLE, "state": "CLOSED", "author": BOT},
        ]
        with self.assertRaises(ValueError):
            find_issue(issues)

    def test_title_match_by_another_author_is_rejected(self):
        for author in (
            {"is_bot": False, "login": "app/github-actions"},
            {"is_bot": True, "login": "app/dependabot"},
            {"is_bot": True, "login": "github-actions"},
            {"is_bot": False, "login": "someone"},
        ):
            with self.subTest(author=author), self.assertRaises(ValueError):
                find_issue([{"number": 1, "title": TITLE, "state": "OPEN", "author": author}])


class TestGhCommands(unittest.TestCase):
    def test_create(self):
        self.assertEqual(
            [["issue", "create", "--title", TITLE, "--body-file", "body.md"]],
            gh_commands("create", None, "body.md"),
        )

    def test_update(self):
        self.assertEqual([["issue", "edit", "7", "--body-file", "body.md"]], gh_commands("update", 7, "body.md"))

    def test_reopen_updates_first(self):
        self.assertEqual(
            [["issue", "edit", "7", "--body-file", "body.md"], ["issue", "reopen", "7"]],
            gh_commands("reopen", 7, "body.md"),
        )

    def test_close(self):
        self.assertEqual([["issue", "close", "7"]], gh_commands("close", 7, "body.md"))

    def test_none(self):
        self.assertEqual([], gh_commands("none", None, "body.md"))

    def test_action_on_an_issue_needs_its_number(self):
        with self.assertRaises(ValueError):
            gh_commands("update", None, "body.md")


if __name__ == "__main__":
    unittest.main()
