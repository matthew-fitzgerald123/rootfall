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

Zones, in descent order, by what each one drills:

1. Navigation: `pwd`, `cd`, `ls`, `find`, `tree`
2. Earthmoving: `mkdir`, `touch`, `cp`, `mv`, `rm`, `ln`
3. Sight: `cat`, `less`, `head`, `tail`, `grep`, `wc` (set in the Hall of Records, `/var/log`)
4. The Permission Gates: `chmod`, `chown`, `sudo`, `umask`
5. The Stream Weavers: `sed`, `awk`, `cut`, `sort`, `uniq`, `tr` (pipes unlock here as combo chains)
6. The Living Realm: `ps`, `top`, `kill`, `jobs`, `nice` (set in `/proc`)
7. The Frontier: `ss`, `netstat`, `tcpdump`, `curl`, `dig`, `lsof`
8. Deep System: `df`, `du`, `free`, `lsblk`, `mount`, `tar`, `rsync`

All eight zones are implemented and playable. Each one has a teaching villager
that quiz-gates before letting you pass, timed recall battles drawn from the SM-2
queue, and an honor-system solve boss. Pipes unlock at Zone 5, and the bosses in
zones 5 through 8 require pipe chains. The Frontier, Zone 7, is the boss zone,
built around networking triage.

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

Done:

- Foundation: repo, two-layer save model, fake FHS world, campaign loader.
- Zone 1 vertical slice: Navigation playable end to end with all three battle
  types and a solve-battle boss.
- SRS core: SM-2 scheduler with timer-as-grader and unit tests.
- Content expansion: all eight zones authored as pure YAML, with pipes as combo
  chains in zones 5 through 8.
- Hardening: an answer-key audit, and a recall matcher that accepts
  equivalent-correct answers (flag-order independence, bundled versus separated
  short flags, quote tolerance) while keeping semantically different commands
  distinct.

Still ahead:

- Timer calibration against real play sessions.
- Output-reading and diagnostic-chain drills.
- A possible RHEL-specific zone (systemd, SELinux, dnf, firewalld).
