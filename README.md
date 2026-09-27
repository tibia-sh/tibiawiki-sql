<!-- Changed by tibia.sh in 2026. See "About this copy" in README.md. -->
# tibiawiki-sql 

## About this copy

This repository is a copy of [Galarzaa90/tibiawiki-sql](https://github.com/Galarzaa90/tibiawiki-sql) by Allan Galarza,
under the Apache License 2.0. The original work and its credit belong to him. tibia.sh maintains this copy.

The copy adds this data to the database:

* The `npc_location` table. It keeps every position of an NPC, numbered 1 to 7, with its city, subarea, geolabel and
  coordinates.
* The `npc_destination.origin` column. It holds the place where each travel leg starts. When an NPC shuttles between
  two places and no note names a leg's start, that leg starts where the other leg ends.
* The item attributes `restores_hp_min`, `restores_hp_max`, `restores_mana_min` and `restores_mana_max`. They hold the
  ranges a potion restores.
* The `outfit.male_client_id`, `outfit.female_client_id` and `mount.client_id` columns. They hold the client IDs (look
  types) of outfits and mounts.
* The `creature.race_id` column. It holds the client race ID of a creature, `NULL` when the wiki has none or only a
  comment.

The [database schema](docs/schema.md) describes each of them.

Releases are wheels on this repository's [GitHub releases](https://github.com/tibia-sh/tibiawiki-sql/releases), not
on PyPI. Their versions end in `+tibiash.N`, like `9.0.0+tibiash.1`. To install one, download the wheel from a release
and run `pip install` on it. The PyPI package and the install steps below are upstream's.

Releases come from `CHANGELOG.md`. A change that should be released adds an entry, a line starting with `- `, under
`## Unreleased` at the top of `CHANGELOG.md`. On every push to `main`, the Release PR workflow reads that section. When
it has entries, the workflow renames it to the next version, sets `__version__` in `tibiawikisql/__init__.py` to that
version and opens or updates the pull request `chore: release <version>` from the branch `release/next`. The next
version counts `+tibiash.N` up from the highest tagged `N` of the same upstream version, so `9.0.0+tibiash.2` is
followed by `9.0.0+tibiash.3`, and an upstream `9.1.0` by `9.1.0+tibiash.1`. When the section is empty or gone, the
workflow closes that pull request. The tibia-sh App, `tibia-sh-bot`, pushes the branch and opens the pull request, so
its CI runs. Nothing merges it by itself.

The release is drptbl's merge of that pull request. The Release PR workflow's run for the merge tags `v<version>`,
like `v9.0.0+tibiash.1`, on the merge commit, as the App, which the `release tags` ruleset lets create `v*` tags. A
merge by anyone else, a pull request from another branch or author, and any other push to `main` tag nothing. The tag
starts the release workflow.

The release workflow checks that the tag matches the version and that the commit is on `main`. It runs the tests and
checks an installed build of the wheel, both without write access. The publishing job then builds the wheel and the
sdist with only the hashed build dependencies in `build-constraints.txt`, checks the wheel's version, writes
`SHA256SUMS`, attests all three files and publishes them with the changelog section as the release notes. A running
release is left to finish. A newer run for the same tag can still replace one that is waiting to start. Once the
release is published, the workflow sends `generator-release` with the version to tibia-sh/tibiawiki-mcp, whose
generator workflow verifies the wheel's attestation and pins it. Running the workflow by hand on `main` is a dry run: it
skips the tag checks, the release and the dispatch. On any other branch it fails.

When a step fails:

* The Release PR workflow's `tag` job failed: re-run that run. A run dispatched on `main` checks the newest commit of
  `main`, not the merge commit. Until the version is tagged, the next proposal fails, so no version is proposed twice.
  When the error says the version has no tag and no merged pull request was found, GitHub had not listed the release
  merge yet. Re-run the run once the pull request shows as merged, or dispatch the workflow on `main` while the merge
  commit is still its newest commit. A direct push of an untagged version fails the same way. The job creates the tag
  with a token that has contents write only, and GitHub refuses a ref at a commit whose `.github/workflows` tree
  matches no branch tip unless the token has workflow scope. So re-run a failed `tag` job before any workflow change
  lands on `main`. If one already has, a maintainer creates the tag by hand and pushes it over SSH. The tag's push runs
  the release workflow, as a dispatch would only run a dry run.
* The release workflow's `downstream` job failed: the release is published, so don't re-run the release run. Run
  `generator.yml` in tibia-sh/tibiawiki-mcp by hand with the version.

The App's private key is the tibia-sh organization secret `TIBIA_SH_APP_PRIVATE_KEY`. If it leaks, generate a new key
in the App's settings, put it in the secret and delete the leaked key. Then look for tags, releases, branches
and pull requests the App made in tibia-sh's repositories that no workflow run explains, and delete them.

To check a download, run `sha256sum -c SHA256SUMS` and this for each file:

```
gh attestation verify <file> --repo tibia-sh/tibiawiki-sql --signer-workflow tibia-sh/tibiawiki-sql/.github/workflows/release.yml --source-ref refs/tags/v<version> --deny-self-hosted-runners
```

This ties the file you downloaded to a tagged release run of this workflow.

Every Monday, the upstream check workflow compares upstream's `main` with this copy's `main`. When upstream has commits
that `main` lacks, it opens an issue titled `Upstream has new commits` that lists them. Once `main` has them all, it
closes the issue. To merge them, add the remote once with
`git remote add upstream https://github.com/Galarzaa90/tibiawiki-sql.git`. Then run `git fetch upstream`, merge
`upstream/main` into a branch and open a pull request. This repository allows only merge commits, because a squash or a
rebase rewrites upstream's commits, so they would still look new and the issue would never close. When the merge
conflicts on `__version__`, take upstream's version. The next release then gets the next `+tibiash.N` of it. Add an
entry for the merge under `## Unreleased` in `CHANGELOG.md`, so it is released. Keep the change notice in every file
this copy changes. GitHub turns off a scheduled workflow after 60 days without activity in the repository. If that
happens, you can turn it back on from the Actions tab.

Every upstream file this copy changes carries this line at the top, in the file's comment syntax:

```
Changed by tibia.sh in 2026. See "About this copy" in README.md.
```

If you change an upstream file, add the line to it. New files don't need it.

The rest of this README is upstream's.

---

Script that generates a sqlite database for the MMO Tibia.

Inspired in [Mytherin's Tibiaylzer](https://github.com/Mytherin/Tibialyzer) TibiaWiki parsing script.

This script fetches data from TibiaWiki via its API, compared to relying on [database dumps](http://tibia.fandom.com/wiki/Special:Statistics)
that are not updated as frequently. By using the API, the data obtained is always fresh.

This script is not intended to be running constantly, it is meant to be run once, generate a sqlite database and use it 
externally.

If you integrate this into your project or use the generated data, make sure to credit [TibiaWiki](https://tibia.fandom.com) and its contributors.


[![GitHub (pre-)release](https://img.shields.io/github/release/Galarzaa90/tibiawiki-sql/all.svg)](https://github.com/Galarzaa90/tibiawiki-sql/releases)
[![PyPI](https://img.shields.io/pypi/v/tibiawikisql.svg)](https://pypi.python.org/pypi/tibiawikisql/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tibiawikisql.svg)
![PyPI - License](https://img.shields.io/pypi/l/tibiawikisql.svg)
![PyPI - Downloads](https://img.shields.io/pypi/dm/tibiawikisql)

## Requirements
* Python 3.10 or higher
    
## Installing
To install the latest version on PyPi:

```sh
pip install tibiawikisql
```

or

Install the latest version from GitHub

pip install git+https://github.com/Galarzaa90/tibiawiki-sql.git

## Running

```sh
python -m tibiawikisql generate
```

OR

```sh
tibiawikisql
```

The process can be long, taking up to 10 minutes the first time. All images are saved to the `images` folder. On 
subsequent runs, images will be read from disk instead of being fetched from TibiaWiki again.
If a newer version of the image has been uploaded, it will be updated.

When done, a database file called `tibiawiki.db` will be found on the folder.

## Docker
[![Docker Pulls](https://img.shields.io/docker/pulls/galarzaa90/tibiawiki-sql)](https://hub.docker.com/r/galarzaa90/tibiawiki-sql)
[![Docker Image Size (latest semver)](https://img.shields.io/docker/image-size/galarzaa90/tibiawiki-sql?sort=semver)](https://hub.docker.com/r/galarzaa90/tibiawiki-sql/tags)

The database can also be generated without installing the project, it's dependencies, or Python, by using Docker.
Make sure to have Docker installed, then simply run:

```sh
generateWithDocker.sh
```

The script will build a Docker image and run the script inside a container. The `tibiawiki.db` file will end up in
the project's root directory as normal.

## Database contents
* Achievements
* Charms
* Creatures
* Creature drop statistics
* Houses
* Imbuements
* Items
* Mounts
* NPCs
* NPC offers
* Outfits
* Quests
* Spells
* Updates
* Worlds

## Documentation
Check out the [documentation page](https://galarzaa90.github.io/tibiawiki-sql/).


## Contributing
Improvements and bug fixes are welcome, via pull requests  
For questions, suggestions and bug reports, submit an issue.

The best way to contribute to this project is by contributing to [TibiaWiki](https://tibia.fandom.com).

[![image](https://vignette.wikia.nocookie.net/tibia/images/d/d9/Tibiawiki_Small.gif/revision/latest?cb=20150129101832&path-prefix=en)](https://tibia.fandom.com/)
