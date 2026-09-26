<!-- Changed by tibia.sh in 2026. See "About this copy" in README.md. -->
# tibiawiki-sql 

## About this copy

This repository is a copy of [Galarzaa90/tibiawiki-sql](https://github.com/Galarzaa90/tibiawiki-sql) by Allan Galarza,
under the Apache License 2.0. The original work and its credit belong to him. tibia.sh maintains this copy.

The copy adds this data to the database:

* The `npc_location` table. It keeps every position of an NPC, numbered 1 to 7, with its city, subarea, geolabel and
  coordinates.
* The `npc_destination.origin` column. It holds the place where each travel leg starts.
* The item attributes `restores_hp_min`, `restores_hp_max`, `restores_mana_min` and `restores_mana_max`. They hold the
  ranges a potion restores.
* The `outfit.male_client_id`, `outfit.female_client_id` and `mount.client_id` columns. They hold the client IDs (look
  types) of outfits and mounts.

The [database schema](docs/schema.md) describes each of them.

Releases are wheels on this repository's [GitHub releases](https://github.com/tibia-sh/tibiawiki-sql/releases), not
on PyPI. Their versions end in `+tibiash.N`, like `9.0.0+tibiash.1`. To install one, download the wheel from a release
and run `pip install` on it. The PyPI package and the install steps below are upstream's.

To release a version, set `__version__` in `tibiawikisql/__init__.py`, add a `## <version>` section to `CHANGELOG.md`
and merge both to `main`. Then push the tag `v<version>`, like `v9.0.0+tibiash.1`, on that commit. The release
workflow checks that the tag matches the version and that the commit is on `main`. It runs the tests and checks an
installed build of the wheel, both without write access. The publishing job then builds the wheel and the sdist with
only the hashed build dependencies in `build-constraints.txt`, checks the wheel's version, writes `SHA256SUMS`, attests
all three files and publishes them with the changelog section as the release notes. A running release is left to
finish. A newer run for the same tag can still replace one that is waiting to start. Running the workflow by hand on
`main` is a dry run: it skips the tag checks and the release. On any other branch it fails.

To check a download, run `sha256sum -c SHA256SUMS` and this for each file:

```
gh attestation verify <file> --repo tibia-sh/tibiawiki-sql --signer-workflow tibia-sh/tibiawiki-sql/.github/workflows/release.yml --source-ref refs/tags/v<version> --deny-self-hosted-runners
```

This ties the file you downloaded to a tagged release run of this workflow.

Every Monday, the upstream check workflow compares upstream's `main` with this copy's `main`. When upstream has commits
that `main` lacks, it opens an issue titled `Upstream has new commits` that lists them. Once `main` has them all, it
closes the issue. To merge them, add the remote once with
`git remote add upstream https://github.com/Galarzaa90/tibiawiki-sql.git`. Then run `git fetch upstream`, merge
`upstream/main` into a branch and open a pull request. Keep the change notice in every file this copy changes. GitHub
turns off a scheduled workflow after 60 days without activity in the repository. If that happens, you can turn it back
on from the Actions tab.

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
