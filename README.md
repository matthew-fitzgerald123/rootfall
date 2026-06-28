# rootfall

A roguelike for mastering Linux commands and flags, built for SRE and platform
interview prep. The filesystem hierarchy is the dungeon map.

## Overview

rootfall turns command drilling into a descent. You start at the root, `/`, and
work down through themed zones, each one teaching a domain of commands. The
Filesystem Hierarchy Standard is the map: `/etc` is the City of Configs, `/var/log`
the Hall of Records, `/proc` the Living Realm, `/dev` the Forge, and the binaries
under `/bin` and `/usr/bin` are the Armory.

The point is retrieval under pressure, not graphics. When you die, you go back to
the root and lose the run. The one thing that survives is a spaced-repetition
memory of which commands you are still slow or wrong on, so every restart targets
your weak spots instead of replaying what you have already mastered.

## How to play

Requirements: Python 3.9 or newer and PyYAML.

```
pip install PyYAML
```

Optional but recommended. You likely develop on macOS but target Linux, and the
solve battles assume GNU coreutils behavior. Install the GNU versions and use the
g-prefixed binaries (`gfind`, `gsed`, `ggrep`) when you want your local tools to
match a Linux box:

```
brew install coreutils gnu-sed grep findutils
```

Launch from the repo root:

```
python rootfall.py
```

Three battle types:

- Solve battles are on the honor system. The game states a Linux-correct
  objective, you solve it for real in your own terminal against the self-contained
  `world/` directory, then you self-report. Nothing is verified. This is a personal
  prep tool, so honesty is the contract. A self-report still feeds your memory.
- Recall battles are timed and played inside the game. A short prompt appears with
  a countdown. You type the answer and the timer is the grader.
- Villager battles teach. An NPC gives you the command, then quiz gates you before
  letting you pass, so recognition does not pass for recall.

The death rule: there is one HP bar across the whole descent. Misses chip it. At
zero HP the run is over and you return to the root. Death deletes run state only.
Your spaced-repetition memory and your record of cleared zones are never touched.

## The World

The game scaffolds its own self-contained `world/` directory that models the
Filesystem Hierarchy Standard, and it never touches your real root. That keeps
your system safe and lets `/proc` exist on macOS, where the process files are
fabricated. Both `world/` and your `saves/` are gitignored.

Zones, in descent order:

1. Navigation
2. The City of Configs
3. The Hall of Records
4. The Living Realm
5. The Forge
6. The Armory
7. The Frontier
8. Deep System

Only Zone 1, Navigation, is implemented so far. It teaches `pwd`, `cd`, `ls`,
`find`, and `tree`, along with the `ls` and `find` flag runes, and ends with a
solve-battle boss that forces a real `find -name`.

## Architecture

Two save layers, kept strictly apart:

- Run state is ephemeral: current zone, position, HP, and the runes and flags
  gathered this run. A death deletes it.
- Meta state is permanent: the SM-2 scheduling queue with per-command ease,
  interval, repetition, and error history, plus the set of zones ever cleared. A
  death never touches it.

The scheduler is a from-scratch SM-2. The twist is that you never self-grade a
recall. The countdown timer does it: fast and correct stretches the interval,
slow holds steady, and wrong or timed out drops the quality below the passing
line, which resets the item and pulls it back to the front of the queue. Nothing
is ever permanently learned; even long-interval items eventually resurface.

Once a zone is cleared it runs in compressed mode on later descents. Villager
tutorials become skippable and recall battles are SRS driven, so mastered
commands rarely surface and the early descent gets faster as you improve. Nothing
is skipped outright, it is only compressed.

## Roadmap

- Foundation: repo, two-layer save model, fake FHS world, campaign loader.
- Zone 1 vertical slice: Navigation playable end to end with all three battle
  types and a solve-battle boss.
- SRS core: SM-2 scheduler with timer-as-grader and unit tests.
- Content expansion: author zones 2 through The Frontier as pure YAML, including
  pipes as combo chains.
- Hardening: richer grading, deeper world detail, and Deep System as the finale.
