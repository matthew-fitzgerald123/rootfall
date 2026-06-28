"""The three battle types.

SOLVE   - honor system. The game states a Linux-correct objective. The player
          solves it in their own terminal against the fake world directory, then
          self-reports. No verification, by design: this is a personal prep tool.
RECALL  - timed retrieval. A short prompt with a visible countdown. The player
          types the answer into the game and the timer is the grader. This is
          the primary drill, and items come from the SM-2 queue, not in order.
VILLAGER - teaching. An NPC delivers lore and the command or flag, then quiz
          gates the player before letting them pass, so recognition cannot
          masquerade as recall.

Every battle feeds the spaced-repetition scheduler that lives in meta state.
"""

import select
import sys
import time

# Outcome dicts use these keys: "correct" (bool) and "damage" (int).


def _normalize(text):
    """Lowercase and collapse whitespace so flag spacing does not matter."""
    return " ".join(text.strip().lower().split())


def matches(answer, accepted):
    if answer is None:
        return False
    target = _normalize(answer)
    return any(target == _normalize(option) for option in accepted)


def timed_input(prompt, time_limit):
    """Read a line, but give up after time_limit seconds.

    Returns (answer, elapsed, timed_out). On timeout or end of input the answer
    is None. Uses select so a real terminal gets a hard cutoff; if select is not
    available (an unusual stdin) it falls back to an untimed read.
    """
    sys.stdout.write(prompt + "\n> ")
    sys.stdout.flush()
    start = time.time()
    try:
        ready, _, _ = select.select([sys.stdin], [], [], time_limit)
    except (OSError, ValueError):
        line = sys.stdin.readline()
        elapsed = time.time() - start
        return (None, elapsed, False) if line == "" else (line.strip(), elapsed, False)

    if ready:
        line = sys.stdin.readline()
        elapsed = time.time() - start
        if line == "":
            return None, elapsed, True
        return line.strip(), elapsed, False

    sys.stdout.write("\n... time!\n")
    return None, time.time() - start, True


# --- RECALL ----------------------------------------------------------------

def recall_battle(scheduler, encounter, miss_damage=3):
    """Timed retrieval drill graded by the countdown."""
    accepted = encounter["answers"]
    key = encounter.get("key") or accepted[0]
    limit = int(encounter.get("time_limit", 8))

    scheduler.ensure(key, encounter["prompt"], accepted[0])

    print()
    print("  -- RECALL --")
    banner = "  {} ({} seconds)".format(encounter["prompt"], limit)
    answer, elapsed, timed_out = timed_input(banner, limit)
    correct = (not timed_out) and matches(answer, accepted)

    scheduler.record(key, correct, elapsed, limit)

    if correct:
        print("  Hit. {:.1f}s.".format(elapsed))
    elif timed_out:
        print("  Too slow. The rune was: {}".format(accepted[0]))
    else:
        print("  Miss. The rune was: {}".format(accepted[0]))

    return {"correct": correct, "damage": 0 if correct else miss_damage}


# --- SOLVE -----------------------------------------------------------------

def solve_battle(scheduler, encounter, world_root="world", miss_damage=5):
    """Honor-system battle solved in the player's own terminal."""
    key = encounter.get("key") or "find -name"
    objective = encounter["objective"]

    print()
    print("  -- SOLVE --")
    print("  " + objective)
    if encounter.get("hint"):
        print("  Hint: " + encounter["hint"])
    print("  The fake world is under '{}/'. Your real filesystem is untouched.".format(world_root))
    print("  Open another terminal, solve it for real, then come back.")

    _prompt("  Press Enter when you have run it... ")
    reported = _yes_no("  Did the command find the target?")

    scheduler.ensure(key, objective, encounter.get("hint", ""))
    scheduler.record(key, reported, 0.0, 0)

    if reported:
        print("  The gate swings open.")
    else:
        print("  The gate holds. Regroup and try the find again.")

    return {"correct": reported, "damage": 0 if reported else miss_damage}


# --- VILLAGER --------------------------------------------------------------

def villager_battle(scheduler, encounter, compressed=False, miss_damage=1):
    """Teaching NPC that quiz gates before letting the player pass."""
    print()
    print("  -- VILLAGER: {} --".format(encounter["name"]))

    if compressed:
        if not _yes_no("  You have met this villager before. Hear the lore again?", default=False):
            # Compressed mode: tutorial is skippable once the zone is cleared.
            for rune in encounter.get("teaches", []):
                scheduler.ensure(rune["command"], rune.get("desc", ""), rune["command"])
            print("  You nod and walk past.")
            return {"correct": True, "damage": 0}

    print("  " + encounter["lore"])
    print()
    for rune in encounter.get("teaches", []):
        print("    rune {:<12} {}".format(rune["command"], rune.get("desc", "")))
    print()

    quiz = encounter["quiz"]
    attempts = 0
    while True:
        answer = _prompt("  {}\n  > ".format(quiz["prompt"]))
        if matches(answer, quiz["answers"]):
            print("  Correct. The road opens.")
            break
        attempts += 1
        print("  Not quite. The villager waits.")

    # A passed quiz seeds every taught command into the SRS queue.
    for rune in encounter.get("teaches", []):
        scheduler.seed(rune["command"], rune.get("desc", ""), rune["command"])

    return {"correct": True, "damage": min(attempts, 3) * miss_damage}


# --- small IO helpers ------------------------------------------------------

def _prompt(text):
    try:
        return input(text)
    except EOFError:
        return ""


def _yes_no(question, default=True):
    suffix = " [Y/n] " if default else " [y/N] "
    answer = _prompt(question + suffix).strip().lower()
    if not answer:
        return default
    return answer.startswith("y")
