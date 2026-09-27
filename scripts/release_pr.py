"""Propose and tag this copy's releases from ``CHANGELOG.md``.

Run by `.github/workflows/release-pr.yml` with the runner's ``python3 -I``, so it uses only the standard library. It
reads and writes ``CHANGELOG.md`` and ``tibiawikisql/__init__.py`` in the working directory, and takes the tags as the
output of ``git show-ref --tags --dereference`` in a file.

``propose`` writes the next release: it renames the first ``## Unreleased`` section of the changelog to the next
``+tibiash.N`` version, sets ``__version__`` to it, writes the pull request body and prints the version. It exits
``NO_ENTRIES_EXIT`` with nothing written when the section is missing or empty.

``tag-decision`` prints ``decision=<skip|noop|fail|tag>``, ``version=<__version__>`` and ``reason=<why it fails>``
for a push to main, given the ``pulls/{number}`` response of the pull request that the pushed commit merged, or
``null``, and the files the pushed commit changes relative to its first parent, one per line.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

GENERATOR_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\+tibiash\.[0-9]+")
UPSTREAM_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
VERSION_LINE = re.compile(r'__version__ = "([^"]*)"')
SHOW_REF_LINE = re.compile(r"([0-9a-f]{40}|[0-9a-f]{64}) refs/tags/(\S+?)(\^\{\})?")
COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
APP_LOGIN = re.compile(r"[a-z0-9-]+\[bot\]")
UNRELEASED = "## Unreleased"
RELEASE_APPROVER = "drptbl"
RELEASE_BRANCH = "release/next"
NO_ENTRIES_EXIT = 3
CHANGELOG = Path("CHANGELOG.md")
INIT = Path("tibiawikisql/__init__.py")
# The files propose writes, and the only ones a release merge may change.
RELEASE_FILES = frozenset({CHANGELOG.as_posix(), INIT.as_posix()})


class NoUnreleasedEntriesError(ValueError):
    """The changelog has no ``## Unreleased`` section, or the section has no ``- `` entry."""

    def __init__(self) -> None:
        """Name the reason in the message."""
        super().__init__("no unreleased entries")


def parse_tags(show_ref: str) -> dict[str, str]:
    """Map each tag to the commit it points at.

    Args:
        show_ref: The output of ``git show-ref --tags --dereference``. An annotated tag's ``^{}`` line names its commit.

    Returns:
        The commit SHA of each tag, by the tag's name without ``refs/tags/``.

    Raises:
        ValueError: A line is not a tag line of that output.
    """
    tags: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for line in show_ref.splitlines():
        match = SHOW_REF_LINE.fullmatch(line)
        if not match:
            msg = f"not a line of git show-ref --tags --dereference: {line!r}"
            raise ValueError(msg)
        sha, name, dereferenced = match.groups()
        (peeled if dereferenced else tags)[name] = sha
    return {**tags, **peeled}


def next_version(current: str, tags: list[str]) -> str:
    """Work out the version of the next release.

    Args:
        current: The ``__version__`` on main, ``x.y.z`` from upstream or ``x.y.z+tibiash.N`` from this copy.
        tags: The names of the repository's tags.

    Returns:
        ``<x.y.z>+tibiash.<N>``, where N is one more than the highest N tagged for ``x.y.z``, or 1 when none is.

    Raises:
        ValueError: ``current`` has another shape, or it is a ``+tibiash.N`` version that is not tagged yet, so the next
            proposal would repeat it.
    """
    if GENERATOR_VERSION.fullmatch(current):
        if f"v{current}" not in tags:
            msg = f"__version__ {current} has no tag v{current}: tag that release before proposing the next one"
            raise ValueError(msg)
    elif not UPSTREAM_VERSION.fullmatch(current):
        msg = f"__version__ {current!r} is neither x.y.z nor x.y.z+tibiash.N"
        raise ValueError(msg)
    base = current.split("+", 1)[0]
    tagged = re.compile(rf"v{re.escape(base)}\+tibiash\.([0-9]+)")
    numbers = [int(match.group(1)) for tag in tags if (match := tagged.fullmatch(tag))]
    return f"{base}+tibiash.{max(numbers, default=0) + 1}"


def _unreleased_section(lines: list[str]) -> tuple[int, list[str]]:
    """Find the first ``## Unreleased`` section.

    Args:
        lines: The changelog's lines, with their line endings.

    Returns:
        The heading's index and the section's lines, up to the next ``## `` heading.

    Raises:
        NoUnreleasedEntriesError: There is no such heading, or no line of the section starts with ``- ``.
    """
    start = next((i for i, line in enumerate(lines) if line.rstrip() == UNRELEASED), None)
    if start is None:
        raise NoUnreleasedEntriesError
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    section = lines[start + 1:end]
    if not any(line.startswith("- ") for line in section):
        raise NoUnreleasedEntriesError
    return start, section


def release_changelog(text: str, version: str) -> tuple[str, str]:
    """Rename the first ``## Unreleased`` heading to ``## <version>``.

    Args:
        text: The changelog.
        version: The release's version.

    Returns:
        The changelog with the heading renamed, and the section's entries without the blank lines around them.

    Raises:
        NoUnreleasedEntriesError: A ``ValueError``, ``no unreleased entries``: there is no ``## Unreleased`` heading,
            or its section has no ``- `` entry.
    """
    lines = text.splitlines(keepends=True)
    start, section = _unreleased_section(lines)
    heading = lines[start]
    lines[start] = f"## {version}" + heading[len(heading.rstrip("\r\n")):]
    return "".join(lines), "".join(section).strip()


def _version_line(init_text: str) -> tuple[list[str], int, str]:
    """Find the one ``__version__`` line, in the form the workflows' ``sed`` reads.

    Args:
        init_text: The text of ``tibiawikisql/__init__.py``.

    Returns:
        The file's lines with their line endings, the version line's index and the version.

    Raises:
        ValueError: There is not exactly one line starting with ``__version__``, or it is not ``__version__ = "<v>"``.
    """
    lines = init_text.splitlines(keepends=True)
    indexes = [i for i, line in enumerate(lines) if line.startswith("__version__")]
    if len(indexes) != 1:
        msg = f"tibiawikisql/__init__.py must have exactly one __version__ line, it has {len(indexes)}"
        raise ValueError(msg)
    index = indexes[0]
    match = VERSION_LINE.fullmatch(lines[index].rstrip("\r\n"))
    if not match:
        msg = f'the __version__ line must read __version__ = "<version>", got {lines[index]!r}'
        raise ValueError(msg)
    return lines, index, match.group(1)


def read_version(init_text: str) -> str:
    """Read ``__version__``.

    Args:
        init_text: The text of ``tibiawikisql/__init__.py``.

    Returns:
        The version.

    Raises:
        ValueError: As :func:`_version_line`.
    """
    return _version_line(init_text)[2]


def set_version(init_text: str, version: str) -> str:
    """Set ``__version__``.

    Args:
        init_text: The text of ``tibiawikisql/__init__.py``.
        version: The release's version, ``x.y.z+tibiash.N``.

    Returns:
        The text with the version line replaced.

    Raises:
        ValueError: The version is not ``x.y.z+tibiash.N``, or as :func:`_version_line`.
    """
    if not GENERATOR_VERSION.fullmatch(version):
        msg = f"a release version is x.y.z+tibiash.N, got {version!r}"
        raise ValueError(msg)
    lines, index, _ = _version_line(init_text)
    line = lines[index]
    lines[index] = f'__version__ = "{version}"' + line[len(line.rstrip("\r\n")):]
    return "".join(lines)


def _release_merge(merged_pr: dict | None, head: str, app_login: str) -> bool:
    """Tell whether a pull request is the App's release pull request, merged at ``head`` by the App or the approver.

    The App merges it when its auto-merge fires, since GitHub records whoever turned auto-merge on as the merger. The
    release approver, a user, can still merge it by hand.

    Args:
        merged_pr: The ``pulls/{number}`` response, or ``None``.
        head: The pushed commit.
        app_login: The App's login, ``<slug>[bot]``.

    Returns:
        Whether the merge releases.
    """
    if merged_pr is None:
        return False
    merged_by = merged_pr.get("merged_by") or {}
    return (
        merged_pr.get("merge_commit_sha") == head
        and bool(merged_pr.get("merged_at"))
        and (merged_pr.get("head") or {}).get("ref") == RELEASE_BRANCH
        and (merged_pr.get("user") or {}).get("login") == app_login
        and (
            (merged_by.get("type") == "Bot" and merged_by.get("login") == app_login)
            or (merged_by.get("type") == "User" and merged_by.get("login") == RELEASE_APPROVER)
        )
    )


def _release_files_problem(changed_files: list[str]) -> str:
    """Tell what is wrong with the files a release merge changes.

    Args:
        changed_files: The files the merge commit changes relative to its first parent.

    Returns:
        Why the merge must not be tagged, in one line: it changes no files, or files outside ``RELEASE_FILES``, which
        it names. Empty when it changes only files of ``RELEASE_FILES``.
    """
    if not changed_files:
        return "the release merge changes no files."
    extra = sorted(set(changed_files) - RELEASE_FILES)
    if extra:
        allowed = " and ".join(sorted(RELEASE_FILES))
        return f"a release merge may change only {allowed}, and this one also changes {', '.join(extra)}."
    return ""


def decide_tag(
    version: str,
    tags: dict[str, str],
    head: str,
    merged_pr: dict | None,
    app_login: str,
    *,
    changed_files: list[str],
) -> tuple[str, str]:
    """Choose what to do with the tag ``v<version>`` after a push to main.

    Args:
        version: ``__version__`` at the pushed commit.
        tags: The commit of each tag, from :func:`parse_tags`.
        head: The pushed commit.
        merged_pr: The ``pulls/{number}`` response of the pull request whose merge commit is ``head``, or ``None``. The
            list of a commit's pull requests has no ``merged_by``, so an entry of it never qualifies.
        app_login: The App's login, ``<slug>[bot]``.
        changed_files: The files ``head`` changes relative to its first parent.

    Returns:
        The decision and, for ``fail``, the reason in one line, else an empty reason. With no merged pull request,
        ``fail`` when the version is ``x.y.z+tibiash.N`` and has no tag: a release merge that GitHub did not list yet,
        or a direct push, which would otherwise leave the release untagged unseen. Otherwise ``skip`` unless
        ``merged_pr`` is the App's ``release/next`` pull request, merged at ``head`` by the App or by the release
        approver, a user; else ``fail`` when ``changed_files`` is empty or names a file outside ``RELEASE_FILES``, so
        no release carries code that did not come through an ordinary pull request; else ``fail`` when the version is
        not ``x.y.z+tibiash.N`` or its tag points at another commit; else ``noop`` when the tag points at ``head``;
        else ``tag``.
    """
    tagged = tags.get(f"v{version}")
    if merged_pr is None and GENERATOR_VERSION.fullmatch(version) and tagged is None:
        return "fail", (
            f"v{version} has no tag and no merged pull request was found. For a release merge, re-run this run once "
            "the pull request shows as merged."
        )
    if not _release_merge(merged_pr, head, app_login):
        return "skip", ""
    problem = _release_files_problem(changed_files)
    if problem:
        return "fail", problem
    if not GENERATOR_VERSION.fullmatch(version):
        return "fail", f"the version {version!r} is not x.y.z+tibiash.N."
    if tagged not in {None, head}:
        return "fail", f"v{version} already points at {tagged}."
    return ("noop" if tagged == head else "tag"), ""


def release_body(version: str, entries: str) -> str:
    """Write the release pull request's body.

    Args:
        version: The release's version.
        entries: The released changelog entries.

    Returns:
        The body as Markdown.
    """
    return (
        f"Releases `{version}`. When {RELEASE_APPROVER} merges this pull request, the merge commit is tagged "
        f"`v{version}`, and the tag publishes the release. A merge by anyone else tags nothing.\n\n{entries}\n"
    )


def _read(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as file:
        return file.read()


def _write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text)


def _propose(tags_file: Path, body_file: Path) -> int:
    changelog = _read(CHANGELOG)
    try:
        _unreleased_section(changelog.splitlines(keepends=True))
    except NoUnreleasedEntriesError:
        return NO_ENTRIES_EXIT
    init = _read(INIT)
    version = next_version(read_version(init), list(parse_tags(_read(tags_file))))
    released, entries = release_changelog(changelog, version)
    versioned = set_version(init, version)
    _write(body_file, release_body(version, entries))
    _write(CHANGELOG, released)
    _write(INIT, versioned)
    sys.stdout.write(f"{version}\n")
    return 0


def _tag_decision(tags_file: Path, pr_file: Path, head: str, app_login: str, changed_file: Path) -> int:
    if not COMMIT_SHA.fullmatch(head):
        msg = f"--head must be a full commit SHA, got {head!r}"
        raise ValueError(msg)
    if not APP_LOGIN.fullmatch(app_login):
        msg = f"--app-login must be <slug>[bot], got {app_login!r}"
        raise ValueError(msg)
    merged_pr = json.loads(_read(pr_file))
    if merged_pr is not None and not isinstance(merged_pr, dict):
        msg = f"{pr_file} must hold a pull request object or null"
        raise ValueError(msg)
    version = read_version(_read(INIT))
    changed_files = _read(changed_file).splitlines()
    decision, reason = decide_tag(
        version, parse_tags(_read(tags_file)), head, merged_pr, app_login, changed_files=changed_files,
    )
    sys.stdout.write(f"decision={decision}\nversion={version}\nreason={reason}\n")
    return 0


def main(argv: list[str]) -> int:
    """Run a command.

    Args:
        argv: The command-line arguments.

    Returns:
        The exit status: 0, or ``NO_ENTRIES_EXIT`` when ``propose`` finds no unreleased entries.

    Raises:
        SystemExit: The arguments are wrong, or the inputs are, with the reason.
    """
    parser = argparse.ArgumentParser(prog="release_pr.py", description=__doc__.split("\n\n", 1)[0])
    commands = parser.add_subparsers(dest="command", required=True)
    propose = commands.add_parser("propose", help="write the next release and print its version")
    propose.add_argument("--tags", required=True, type=Path, help="git show-ref --tags --dereference output")
    propose.add_argument("--body", required=True, type=Path, help="where to write the pull request body")
    tag = commands.add_parser("tag-decision", help="print what to do with the release tag")
    tag.add_argument("--tags", required=True, type=Path, help="git show-ref --tags --dereference output")
    tag.add_argument("--pr", required=True, type=Path, help="the merged pull request's JSON, or null")
    tag.add_argument("--head", required=True, help="the pushed commit")
    tag.add_argument("--app-login", required=True, help="the App's login, <slug>[bot]")
    tag.add_argument("--changed-files", required=True, type=Path,
                     help="the files the pushed commit changes relative to its first parent, one per line")
    args = parser.parse_args(argv)
    try:
        if args.command == "propose":
            return _propose(args.tags, args.body)
        return _tag_decision(args.tags, args.pr, args.head, args.app_login, args.changed_files)
    except ValueError as error:
        msg = f"release_pr.py {args.command}: {error}"
        raise SystemExit(msg) from error


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
