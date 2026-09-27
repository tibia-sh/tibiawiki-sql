import io
import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import ClassVar

from scripts.release_pr import (
    NO_ENTRIES_EXIT,
    RELEASE_APPROVER,
    RELEASE_BRANCH,
    decide_tag,
    main,
    next_version,
    parse_tags,
    release_changelog,
    set_version,
)

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
APP = "tibia-sh-bot[bot]"
HEAD = "a" * 40
OLD = "b" * 40
CHANGELOG = """<!-- Changed by tibia.sh in 2026. See "About this copy" in README.md. -->
# Changelog

## Unreleased

- Fix a thing.
- Add another thing
  over two lines.

## 9.0.0+tibiash.2

- An older entry.
"""
INIT = '''"""Package."""

__license__ = "Apache 2.0"
__version__ = "9.0.0+tibiash.2"
'''


def merged_pr(**changes: object) -> dict:
    """A ``pulls/{number}`` response for the App's release PR, merged by the approver at ``HEAD``."""
    pr = {
        "number": 12,
        "merge_commit_sha": HEAD,
        "merged_at": "2026-09-27T10:00:00Z",
        "head": {"ref": RELEASE_BRANCH, "sha": "c" * 40},
        "user": {"login": APP, "type": "Bot"},
        "merged_by": {"login": RELEASE_APPROVER, "type": "User"},
    }
    pr.update(changes)
    return pr


def job(workflow: str, name: str) -> str:
    """The text of one job of a workflow, from its ``  <name>:`` line to the next job."""
    lines = (WORKFLOWS / workflow).read_text(encoding="utf-8").splitlines()
    start = lines.index(f"  {name}:")
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"  \S", lines[i])), len(lines))
    return "\n".join(lines[start:end]) + "\n"


class TestNextVersion(unittest.TestCase):
    def test_counts_up_from_the_tagged_version(self):
        tags = ["v9.0.0+tibiash.1", "v9.0.0+tibiash.2"]
        self.assertEqual("9.0.0+tibiash.3", next_version("9.0.0+tibiash.2", tags))

    def test_new_upstream_version_starts_at_one(self):
        self.assertEqual("9.1.0+tibiash.1", next_version("9.1.0", ["v9.0.0+tibiash.2"]))

    def test_orders_numerically(self):
        tags = ["v9.0.0+tibiash.10", "v9.0.0+tibiash.9"]
        self.assertEqual("9.0.0+tibiash.11", next_version("9.0.0+tibiash.10", tags))

    def test_ignores_other_bases_and_lookalikes(self):
        tags = ["v9.0.0", "v9.1.0+tibiash.7", "v9.0.0+tibiash.4x", "9.0.0+tibiash.5", "v9.0.0+tibiash.2"]
        self.assertEqual("9.0.0+tibiash.3", next_version("9.0.0+tibiash.2", tags))

    def test_untagged_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, re.escape("9.0.0+tibiash.3")):
            next_version("9.0.0+tibiash.3", ["v9.0.0+tibiash.1", "v9.0.0+tibiash.2"])

    def test_unknown_version_shape_is_rejected(self):
        for current in ["9.0", "9.0.0rc1", "9.0.0+local", "9.0.0+tibiash.2\n", ""]:
            with self.subTest(current=current), self.assertRaises(ValueError):
                next_version(current, [f"v{current}"])


class TestReleaseChangelog(unittest.TestCase):
    def test_renames_the_heading_and_returns_the_entries(self):
        text, entries = release_changelog(CHANGELOG, "9.0.0+tibiash.3")
        self.assertEqual(CHANGELOG.replace("## Unreleased\n", "## 9.0.0+tibiash.3\n"), text)
        self.assertEqual("- Fix a thing.\n- Add another thing\n  over two lines.", entries)

    def test_renames_only_the_first_heading(self):
        changelog = CHANGELOG + "\n## Unreleased\n\n- Stray.\n"
        text, entries = release_changelog(changelog, "9.0.0+tibiash.3")
        self.assertEqual(1, text.count("## Unreleased\n"))
        self.assertEqual(1, text.count("## 9.0.0+tibiash.3\n"))
        self.assertLess(text.index("## 9.0.0+tibiash.3"), text.index("## Unreleased"))
        self.assertNotIn("Stray", entries)

    def test_empty_section_is_rejected(self):
        changelog = CHANGELOG.replace("- Fix a thing.\n- Add another thing\n  over two lines.\n", "Nothing yet.\n")
        with self.assertRaisesRegex(ValueError, "^no unreleased entries$"):
            release_changelog(changelog, "9.0.0+tibiash.3")

    def test_missing_heading_is_rejected(self):
        changelog = CHANGELOG.replace("## Unreleased\n", "")
        with self.assertRaisesRegex(ValueError, "^no unreleased entries$"):
            release_changelog(changelog, "9.0.0+tibiash.3")

    def test_entry_of_a_later_section_does_not_count(self):
        changelog = "# Changelog\n\n## Unreleased\n\n## 9.0.0\n\n- Old.\n"
        with self.assertRaisesRegex(ValueError, "^no unreleased entries$"):
            release_changelog(changelog, "9.0.0+tibiash.3")

    def test_keeps_crlf_line_endings(self):
        text, _ = release_changelog(CHANGELOG.replace("\n", "\r\n"), "9.0.0+tibiash.3")
        self.assertEqual(CHANGELOG.replace("## Unreleased\n", "## 9.0.0+tibiash.3\n").replace("\n", "\r\n"), text)


class TestSetVersion(unittest.TestCase):
    def test_replaces_the_version_line(self):
        self.assertEqual(INIT.replace("9.0.0+tibiash.2", "9.0.0+tibiash.3"), set_version(INIT, "9.0.0+tibiash.3"))

    def test_missing_line_is_rejected(self):
        with self.assertRaises(ValueError):
            set_version(INIT.replace('__version__ = "9.0.0+tibiash.2"\n', ""), "9.0.0+tibiash.3")

    def test_two_lines_are_rejected(self):
        with self.assertRaises(ValueError):
            set_version(INIT + '__version__ = "9.0.0"\n', "9.0.0+tibiash.3")

    def test_version_outside_the_generator_pattern_is_rejected(self):
        for version in ["9.1.0", '9.0.0+tibiash.3"', "9.0.0+tibiash.3\n"]:
            with self.subTest(version=version), self.assertRaises(ValueError):
                set_version(INIT, version)

    def test_line_the_workflows_cannot_read_is_rejected(self):
        with self.assertRaises(ValueError):
            set_version(INIT.replace('"9.0.0+tibiash.2"', "'9.0.0+tibiash.2'"), "9.0.0+tibiash.3")


class TestParseTags(unittest.TestCase):
    def test_peels_annotated_tags(self):
        show_ref = (
            f"{OLD} refs/tags/v9.0.0\n"
            f"{'d' * 40} refs/tags/v9.0.0+tibiash.2\n"
            f"{HEAD} refs/tags/v9.0.0+tibiash.2^{{}}\n"
        )
        self.assertEqual({"v9.0.0": OLD, "v9.0.0+tibiash.2": HEAD}, parse_tags(show_ref))

    def test_empty_output_has_no_tags(self):
        self.assertEqual({}, parse_tags(""))

    def test_malformed_line_is_rejected(self):
        for line in [f"{HEAD} refs/heads/main", "xyz refs/tags/v1", f"{HEAD}  refs/tags/v1", f"{HEAD} refs/tags/"]:
            with self.subTest(line=line), self.assertRaises(ValueError):
                parse_tags(line + "\n")


class TestDecideTag(unittest.TestCase):
    VERSION = "9.0.0+tibiash.3"
    TAGS: ClassVar[dict[str, str]] = {"v9.0.0+tibiash.2": OLD}

    def decide(self, pr: dict | None, tags: dict[str, str] | None = None, version: str = VERSION) -> str:
        return decide_tag(version, self.TAGS if tags is None else tags, HEAD, pr, APP)

    def test_tags_the_approved_release_merge(self):
        self.assertEqual("tag", self.decide(merged_pr()))

    def test_skips_an_ordinary_push_after_a_tagged_release(self):
        self.assertEqual("skip", self.decide(None, {"v9.0.0+tibiash.3": OLD}))

    def test_skips_a_direct_push(self):
        self.assertEqual("skip", self.decide(None))

    def test_skips_an_upstream_version(self):
        self.assertEqual("skip", self.decide(None, version="9.1.0"))

    def test_skips_a_merge_by_the_app(self):
        self.assertEqual("skip", self.decide(merged_pr(merged_by={"login": APP, "type": "Bot"})))

    def test_skips_a_merge_by_another_user(self):
        self.assertEqual("skip", self.decide(merged_pr(merged_by={"login": "someone", "type": "User"})))

    def test_skips_a_merge_by_a_bot_named_like_the_approver(self):
        self.assertEqual("skip", self.decide(merged_pr(merged_by={"login": RELEASE_APPROVER, "type": "Bot"})))

    def test_skips_the_commit_pulls_list_entry_without_merged_by(self):
        entry = merged_pr()
        del entry["merged_by"]
        self.assertEqual("skip", self.decide(entry))

    def test_skips_a_null_merged_by(self):
        self.assertEqual("skip", self.decide(merged_pr(merged_by=None)))

    def test_skips_another_merge_commit(self):
        self.assertEqual("skip", self.decide(merged_pr(merge_commit_sha=OLD)))

    def test_skips_an_unmerged_pr(self):
        self.assertEqual("skip", self.decide(merged_pr(merged_at=None)))

    def test_skips_another_branch(self):
        self.assertEqual("skip", self.decide(merged_pr(head={"ref": "release/other", "sha": "c" * 40})))

    def test_skips_a_pr_by_someone_else(self):
        self.assertEqual("skip", self.decide(merged_pr(user={"login": RELEASE_APPROVER, "type": "User"})))

    def test_noop_when_already_tagged_here(self):
        self.assertEqual("noop", self.decide(merged_pr(), {**self.TAGS, "v9.0.0+tibiash.3": HEAD}))

    def test_fails_when_the_tag_is_elsewhere(self):
        self.assertEqual("fail", self.decide(merged_pr(), {**self.TAGS, "v9.0.0+tibiash.3": OLD}))

    def test_fails_on_a_version_outside_the_generator_pattern(self):
        for version in ["9.1.0", "9.0.0+tibiash.3\n", "9.0.0+tibiash.x"]:
            with self.subTest(version=version):
                self.assertEqual("fail", self.decide(merged_pr(), version=version))


class CliTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "tibiawikisql").mkdir()
        self.write("CHANGELOG.md", CHANGELOG)
        self.write("tibiawikisql/__init__.py", INIT)
        self.write("tags.txt", f"{'d' * 40} refs/tags/v9.0.0+tibiash.2\n{OLD} refs/tags/v9.0.0+tibiash.2^{{}}\n")
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)

    def write(self, name: str, text: str) -> None:
        with open(self.root / name, "w", encoding="utf-8", newline="") as file:
            file.write(text)

    def read(self, name: str) -> str:
        with open(self.root / name, encoding="utf-8", newline="") as file:
            return file.read()

    def run_main(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(list(argv))
        return code, out.getvalue()


class TestProposeCli(CliTestCase):
    def propose(self) -> tuple[int, str]:
        return self.run_main("propose", "--tags", "tags.txt", "--body", "body.md")

    def test_writes_the_release(self):
        self.assertEqual((0, "9.0.0+tibiash.3\n"), self.propose())
        self.assertEqual(CHANGELOG.replace("## Unreleased\n", "## 9.0.0+tibiash.3\n"), self.read("CHANGELOG.md"))
        self.assertEqual(INIT.replace("9.0.0+tibiash.2", "9.0.0+tibiash.3"), self.read("tibiawikisql/__init__.py"))
        body = self.read("body.md")
        self.assertIn("`v9.0.0+tibiash.3`", body)
        self.assertIn(RELEASE_APPROVER, body)
        self.assertTrue(body.endswith("- Fix a thing.\n- Add another thing\n  over two lines.\n"))

    def test_no_entries_exits_3_before_asking_for_a_version(self):
        # The release merge's own run: the section is renamed and the version is not tagged yet.
        changelog = CHANGELOG.replace("## Unreleased\n", "## 9.0.0+tibiash.3\n")
        init = INIT.replace("9.0.0+tibiash.2", "9.0.0+tibiash.3")
        self.write("CHANGELOG.md", changelog)
        self.write("tibiawikisql/__init__.py", init)
        self.assertEqual((NO_ENTRIES_EXIT, ""), self.propose())
        self.assertEqual(3, NO_ENTRIES_EXIT)
        self.assertEqual(changelog, self.read("CHANGELOG.md"))
        self.assertEqual(init, self.read("tibiawikisql/__init__.py"))
        self.assertFalse((self.root / "body.md").exists())

    def test_untagged_version_with_entries_fails_without_writing(self):
        self.write("tibiawikisql/__init__.py", INIT.replace("9.0.0+tibiash.2", "9.0.0+tibiash.3"))
        with self.assertRaisesRegex(SystemExit, re.escape("9.0.0+tibiash.3")):
            self.propose()
        self.assertEqual(CHANGELOG, self.read("CHANGELOG.md"))
        self.assertFalse((self.root / "body.md").exists())


class TestTagDecisionCli(CliTestCase):
    def tag_decision(self, pr: object) -> tuple[int, str]:
        self.write("pr.json", json.dumps(pr))
        self.write("tibiawikisql/__init__.py", INIT.replace("9.0.0+tibiash.2", "9.0.0+tibiash.3"))
        return self.run_main("tag-decision", "--tags", "tags.txt", "--pr", "pr.json", "--head", HEAD,
                             "--app-login", APP)

    def test_prints_the_decision_and_the_version(self):
        self.assertEqual((0, "decision=tag\nversion=9.0.0+tibiash.3\n"), self.tag_decision(merged_pr()))

    def test_null_pr_is_a_skip(self):
        self.assertEqual((0, "decision=skip\nversion=9.0.0+tibiash.3\n"), self.tag_decision(None))

    def test_head_must_be_a_full_sha(self):
        self.write("pr.json", "null")
        with self.assertRaises(SystemExit):
            self.run_main("tag-decision", "--tags", "tags.txt", "--pr", "pr.json", "--head", "abc1234",
                          "--app-login", APP)

    def test_app_login_must_be_a_bot_login(self):
        self.write("pr.json", "null")
        for login in ["[bot]", "tibia-sh-bot", "drptbl"]:
            with self.subTest(login=login), self.assertRaises(SystemExit):
                self.run_main("tag-decision", "--tags", "tags.txt", "--pr", "pr.json", "--head", HEAD,
                              "--app-login", login)

    def test_pr_must_be_an_object_or_null(self):
        with self.assertRaises(SystemExit):
            self.tag_decision([merged_pr()])


class WorkflowTestCase(unittest.TestCase):
    """Security-critical workflow text, checked line for line, with the standard library alone."""

    WORKFLOW = ""

    def text(self) -> str:
        return (WORKFLOWS / self.WORKFLOW).read_text(encoding="utf-8")

    def assert_in_job(self, name: str, snippet: str) -> None:
        self.assertIn(snippet, job(self.WORKFLOW, name))


class TestReleasePrWorkflow(WorkflowTestCase):
    WORKFLOW = "release-pr.yml"
    CHECKOUT = """\
      - name: Check out
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          fetch-tags: true
          persist-credentials: false
"""

    def test_runs_on_main_one_run_at_a_time(self):
        self.assertIn("""\
name: Release PR
""", self.text())
        self.assertIn("""\
on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions: {}
""", self.text())
        self.assertIn("""\
concurrency:
  group: release-pr
  cancel-in-progress: false
  queue: max
""", self.text())

    def test_runs_no_dependency_code(self):
        lines = [line.strip() for line in self.text().splitlines()]
        uses = sorted({line for line in lines if line.startswith(("uses:", "- uses:"))})
        self.assertEqual([
            "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1",
            "uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0",
        ], uses)
        code = "\n".join(line for line in self.text().splitlines() if not line.lstrip().startswith("#"))
        for word in ["pip ", "uv ", "setup-", "cache", "npm", "unittest", ".venv", "artifact"]:
            with self.subTest(word=word):
                self.assertNotIn(word, code)
        runs = re.findall(r"python3?\b[^\n]*", code)
        self.assertTrue(runs)
        for run in runs:
            with self.subTest(run=run):
                self.assertTrue(run.startswith("python3 -I scripts/release_pr.py "))

    def test_propose_job_runs_in_the_release_environment(self):
        self.assert_in_job("propose", """\
  propose:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    environment: release-trigger
    permissions:
      contents: read # the checkout and its tags
      pull-requests: read # the open release pull request
    steps:
""" + self.CHECKOUT)

    def test_propose_ends_green_with_no_entries(self):
        self.assert_in_job("propose", """\
      - name: Write the release
        id: propose
        run: |
          tags="$RUNNER_TEMP/tags.txt"
          git show-ref --tags --dereference > "$tags"
          if version="$(python3 -I scripts/release_pr.py propose --tags "$tags" --body "$RUNNER_TEMP/body.md")"; then
            if [[ ! $version =~ ^[0-9]+\\.[0-9]+\\.[0-9]+\\+tibiash\\.[0-9]+$ ]]; then
              echo "::error::release_pr.py propose printed a version that is not x.y.z+tibiash.N."
              exit 1
            fi
            echo "Proposing $version."
            echo "version=$version" >> "$GITHUB_OUTPUT"
          else
            status=$?
            if [ "$status" -ne 3 ]; then
              exit "$status"
            fi
            echo "CHANGELOG.md has no unreleased entries, so there is nothing to release."
          fi
""")

    def test_finds_the_app_pull_request_with_github_token(self):
        self.assert_in_job("propose", """\
        env:
          GH_TOKEN: ${{ github.token }}
          GH_REPO: ${{ github.repository }}
          APP_LOGIN: ${{ vars.TIBIA_SH_APP_SLUG }}[bot]
        run: |
          if [[ ! $APP_LOGIN =~ ^[a-z0-9-]+\\[bot\\]$ ]]; then
            echo "::error::The App's login, from vars.TIBIA_SH_APP_SLUG, is not <slug>[bot]."
            exit 1
          fi
          query="head=$GITHUB_REPOSITORY_OWNER:release/next&base=main&state=open"
          number="$(timeout --kill-after=10 120 gh api "repos/{owner}/{repo}/pulls?$query" \\
            --jq 'map(select(.user.login == env.APP_LOGIN)) | .[0].number // empty')"
          if [[ ! $number =~ ^[0-9]*$ ]]; then
            echo "::error::The open release pull request has no plain number."
            exit 1
          fi
          echo "number=$number" >> "$GITHUB_OUTPUT"
""")

    def test_closes_with_a_pull_requests_token(self):
        self.assert_in_job("propose", """\
      - id: close_token
        if: ${{ steps.propose.outputs.version == '' && steps.pr.outputs.number != '' }}
        uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0
        with:
          client-id: ${{ vars.TIBIA_SH_APP_CLIENT_ID }}
          private-key: ${{ secrets.TIBIA_SH_APP_PRIVATE_KEY }}
          owner: tibia-sh
          repositories: tibiawiki-sql
          permission-pull-requests: write
      - name: Close the release pull request
        if: ${{ steps.propose.outputs.version == '' && steps.pr.outputs.number != '' }}
        env:
          GH_TOKEN: ${{ steps.close_token.outputs.token }}
          GH_REPO: ${{ github.repository }}
          PR: ${{ steps.pr.outputs.number }}
        run: |
          timeout --kill-after=10 120 gh pr close "$PR" \\
            --comment "CHANGELOG.md on main has no unreleased entries, so there is nothing to release."
""")

    def test_commits_only_the_script_output_before_the_token(self):
        self.assert_in_job("propose", """\
      - name: Commit the release
        if: ${{ steps.propose.outputs.version != '' }}
        env:
          VERSION: ${{ steps.propose.outputs.version }}
          GIT_AUTHOR_NAME: github-actions[bot]
          GIT_AUTHOR_EMAIL: 41898282+github-actions[bot]@users.noreply.github.com
          GIT_COMMITTER_NAME: github-actions[bot]
          GIT_COMMITTER_EMAIL: 41898282+github-actions[bot]@users.noreply.github.com
        run: |
          if [[ "$(git status --porcelain)" != $' M CHANGELOG.md\\n M tibiawikisql/__init__.py' ]]; then
            echo "::error::propose must change CHANGELOG.md and tibiawikisql/__init__.py, and nothing else."
            exit 1
          fi
          git add CHANGELOG.md tibiawikisql/__init__.py
          git commit --quiet -m "chore: release $VERSION"
""")
        propose = job(self.WORKFLOW, "propose")
        self.assertLess(propose.index("- name: Commit the release"), propose.index("- id: push_token"))

    def test_pushes_and_opens_the_pull_request_with_the_app_token(self):
        self.assert_in_job("propose", """\
      - id: push_token
        if: ${{ steps.propose.outputs.version != '' }}
        uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0
        with:
          client-id: ${{ vars.TIBIA_SH_APP_CLIENT_ID }}
          private-key: ${{ secrets.TIBIA_SH_APP_PRIVATE_KEY }}
          owner: tibia-sh
          repositories: tibiawiki-sql
          permission-contents: write
          permission-pull-requests: write
""")
        self.assert_in_job("propose", """\
      - name: Push release/next and open or update its pull request
        if: ${{ steps.propose.outputs.version != '' }}
        env:
          GH_TOKEN: ${{ steps.push_token.outputs.token }}
          GH_REPO: ${{ github.repository }}
          VERSION: ${{ steps.propose.outputs.version }}
          PR: ${{ steps.pr.outputs.number }}
        run: |
          title="chore: release $VERSION"
          # shellcheck disable=SC2016 # git's shell expands $GH_TOKEN when it runs the helper
          timeout --kill-after=10 120 git -c credential.helper= \\
            -c 'credential.helper=!f() { echo username=x-access-token; echo "password=$GH_TOKEN"; }; f' \\
            push --force origin HEAD:refs/heads/release/next
          if [[ -n $PR ]]; then
            timeout --kill-after=10 120 gh api --method PATCH "repos/{owner}/{repo}/pulls/$PR" --silent \\
              -f title="$title" -F body=@"$RUNNER_TEMP/body.md"
          else
            timeout --kill-after=10 120 gh api "repos/{owner}/{repo}/pulls" --silent \\
              -f head=release/next -f base=main -f title="$title" -F body=@"$RUNNER_TEMP/body.md"
          fi
""")

    def test_app_tokens_reach_only_the_writing_steps(self):
        text = self.text()
        self.assertEqual(
            sorted(re.findall(r"GH_TOKEN: \$\{\{ steps\.(\w+)\.outputs\.token \}\}", text)),
            sorted(re.findall(r"- id: (\w+_token)\n", text)),
        )
        self.assertNotIn("merge --auto", text)

    def test_tag_job_runs_in_the_release_environment(self):
        self.assert_in_job("tag", """\
  tag:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    environment: release-trigger
    permissions:
      contents: read # the checkout and its tags
      pull-requests: read # the pull request the pushed commit merged
    steps:
""" + self.CHECKOUT)

    def test_reads_merged_by_from_the_pull_request_itself(self):
        self.assert_in_job("tag", """\
      - name: Read the merged pull request
        env:
          GH_TOKEN: ${{ github.token }}
          GH_REPO: ${{ github.repository }}
        run: |
          numbers="$(timeout --kill-after=10 120 gh api "repos/{owner}/{repo}/commits/$GITHUB_SHA/pulls" \\
            --jq '[.[] | select(.merge_commit_sha == env.GITHUB_SHA and .merged_at) | "\\(.number)"] | join(" ")')"
          if [[ -z $numbers ]]; then
            echo null > "$RUNNER_TEMP/pr.json"
          elif [[ $numbers =~ ^[0-9]+$ ]]; then
            timeout --kill-after=10 120 gh api "repos/{owner}/{repo}/pulls/$numbers" > "$RUNNER_TEMP/pr.json"
          else
            echo "::error::More than one merged pull request has $GITHUB_SHA as its merge commit."
            exit 1
          fi
""")

    def test_decides_with_the_script_and_fails_red(self):
        self.assert_in_job("tag", """\
      - name: Decide
        id: decide
        env:
          APP_LOGIN: ${{ vars.TIBIA_SH_APP_SLUG }}[bot]
        run: |
          tags="$RUNNER_TEMP/tags.txt"
          git show-ref --tags --dereference > "$tags"
          result="$(python3 -I scripts/release_pr.py tag-decision --tags "$tags" --pr "$RUNNER_TEMP/pr.json" \\
            --head "$GITHUB_SHA" --app-login "$APP_LOGIN")"
          decision="$(sed -n 's/^decision=//p' <<< "$result")"
          version="$(sed -n 's/^version=//p' <<< "$result")"
          case $decision in
            tag) echo "Tagging v$version at $GITHUB_SHA." ;;
            noop) echo "v$version already points at $GITHUB_SHA." ;;
            skip) echo "$GITHUB_SHA is not drptbl's merge of the App's release pull request, so nothing is tagged." ;;
            fail)
              echo "::error::v$version cannot be tagged at $GITHUB_SHA." \\
                "The version is not x.y.z+tibiash.N, or the tag points at another commit."
              exit 1
              ;;
            *)
              echo "::error::release_pr.py tag-decision printed an unknown decision."
              exit 1
              ;;
          esac
          echo "decision=$decision" >> "$GITHUB_OUTPUT"
          echo "version=$version" >> "$GITHUB_OUTPUT"
""")

    def test_creates_the_tag_with_a_contents_token(self):
        self.assert_in_job("tag", """\
      - id: tag_token
        if: ${{ steps.decide.outputs.decision == 'tag' }}
        uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0
        with:
          client-id: ${{ vars.TIBIA_SH_APP_CLIENT_ID }}
          private-key: ${{ secrets.TIBIA_SH_APP_PRIVATE_KEY }}
          owner: tibia-sh
          repositories: tibiawiki-sql
          permission-contents: write
      - name: Create the tag
        if: ${{ steps.decide.outputs.decision == 'tag' }}
        env:
          GH_TOKEN: ${{ steps.tag_token.outputs.token }}
          GH_REPO: ${{ github.repository }}
          VERSION: ${{ steps.decide.outputs.version }}
        run: |
          if [[ ! $VERSION =~ ^[0-9]+\\.[0-9]+\\.[0-9]+\\+tibiash\\.[0-9]+$ || ! $GITHUB_SHA =~ ^[0-9a-f]{40}$ ]]; then
            echo "::error::The version is not x.y.z+tibiash.N, or the pushed commit is not a full SHA."
            exit 1
          fi
          timeout --kill-after=10 120 gh api "repos/{owner}/{repo}/git/refs" --silent \\
            -f ref="refs/tags/v$VERSION" -f sha="$GITHUB_SHA"
          echo "Tagged v$VERSION at $GITHUB_SHA."
""")


class TestReleaseWorkflow(WorkflowTestCase):
    WORKFLOW = "release.yml"

    def test_publish_step_reports_published_after_the_upload(self):
        self.assert_in_job("release", """\
    outputs:
      published: ${{ steps.publish.outputs.published }} # 'true' once the release and its assets are uploaded
""")
        self.assert_in_job("release", """\
      - name: Create the release
        id: publish
        if: github.event_name == 'push'
        env:
          GH_TOKEN: ${{ github.token }}
          GH_REPO: ${{ github.repository }}
          WHEEL: ${{ steps.build.outputs.wheel }}
          SDIST: ${{ steps.build.outputs.sdist }}
        run: |
          gh release create "$GITHUB_REF_NAME" "$WHEEL" "$SDIST" dist/SHA256SUMS \\
            --verify-tag --notes-file "$RUNNER_TEMP/notes.md"
          echo "published=true" >> "$GITHUB_OUTPUT"
""")
        release = job(self.WORKFLOW, "release")
        self.assertLess(release.index("uses: actions/attest-build-provenance@"), release.index("id: publish"))
        self.assertEqual(1, self.text().count("published=true"))

    def test_downstream_runs_only_after_a_tag_push_published(self):
        # A dry run is a workflow_dispatch on main, which publishes nothing, so it has no downstream job.
        self.assert_in_job("downstream", """\
  downstream:
    needs: [check, release]
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v') &&
      needs.release.outputs.published == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 8
    environment: release-trigger
    permissions: {}
    env:
      VERSION: ${{ needs.check.outputs.version }}
    steps:
""")

    def test_downstream_dispatches_with_a_contents_token(self):
        self.assert_in_job("downstream", """\
      - id: token
        uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0
        with:
          client-id: ${{ vars.TIBIA_SH_APP_CLIENT_ID }}
          private-key: ${{ secrets.TIBIA_SH_APP_PRIVATE_KEY }}
          owner: tibia-sh
          repositories: tibiawiki-mcp
          permission-contents: write
""")
        self.assert_in_job("downstream", """\
      - name: Tell tibiawiki-mcp about the release
        env:
          GH_TOKEN: ${{ steps.token.outputs.token }}
        run: |
          if [[ ! $VERSION =~ ^[0-9]+\\.[0-9]+\\.[0-9]+\\+tibiash\\.[0-9]+$ || $GITHUB_REF_NAME != "v$VERSION" ]]; then
            echo "::error::The released version is not x.y.z+tibiash.N, or it is not the tag's."
            exit 1
          fi
          # shellcheck disable=SC2016 # $version is jq's, not the shell's
          payload='{event_type: "generator-release", client_payload: {version: $version}}'
          body="$(jq -n --arg version "$VERSION" "$payload")"
          for attempt in 1 2 3; do
            if [ "$attempt" -gt 1 ]; then
              sleep 30
            fi
            if timeout --kill-after=10 120 gh api repos/tibia-sh/tibiawiki-mcp/dispatches --input - <<< "$body"; then
              echo "Told tibia-sh/tibiawiki-mcp about $VERSION in attempt $attempt."
              exit 0
            fi
          done
          echo "::error::Could not tell tibia-sh/tibiawiki-mcp about $VERSION in 3 attempts, 30 seconds apart." \\
            "Run generator.yml there by hand with the version, as README.md describes."
          exit 1
""")
        downstream = job(self.WORKFLOW, "downstream")
        self.assertNotIn("checkout", downstream)
        self.assertEqual(1, downstream.count("uses:"))
