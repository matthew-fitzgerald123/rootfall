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

import re
import select
import sys
import time

# Outcome dicts use these keys: "correct" (bool) and "damage" (int).

# A bare bundle of short flags: a single dash followed only by ASCII letters,
# such as -l, -tulpn, or -nn. Tokens with digits (-9, -15), long flags
# (--recursive), flags carrying a value (-d:), or anything else are NOT bundles
# and stay as ordinary tokens.
_SHORT_FLAG = re.compile(r"-[A-Za-z]+")
_QUOTES = "\"'"


def _tokenize(text):
    """Split into shell-like tokens, keeping quoted spans whole.

    Whitespace separates tokens, except whitespace inside a quoted span, which
    stays part of that single token. This is what guarantees token boundaries:
    a one-argument "foo bar" comes back as one token, never two. Quote
    characters are kept on the token here; stripping happens in _strip_quotes.
    An unterminated quote is treated literally, so the opening quote just rides
    along on the token and nothing is merged or split unexpectedly.
    """
    tokens = []
    current = []
    quote = None
    for ch in text:
        if quote is None:
            if ch.isspace():
                if current:
                    tokens.append("".join(current))
                    current = []
            else:
                if ch in _QUOTES:
                    quote = ch
                current.append(ch)
        else:
            current.append(ch)
            if ch == quote:
                quote = None
    if current:
        tokens.append("".join(current))
    return tokens


def _strip_quotes(token):
    """Strip one matched surrounding quote pair, but only when it is safe.

    Stripped only when the same quote character wraps both ends and the inner
    span has no whitespace, so "config.yaml" becomes config.yaml. A quoted span
    that contains whitespace keeps its quotes, so "foo bar" stays a single
    distinct token and never looks like the two tokens foo bar. Mismatched or
    internal quotes are left untouched.
    """
    if len(token) >= 2 and token[0] in _QUOTES and token[-1] == token[0]:
        inner = token[1:-1]
        if token[0] not in inner and not any(ch.isspace() for ch in inner):
            return inner
    return token


def _canonical(text):
    """Reduce a command answer to a form that ignores only safe differences.

    Ignored (safe): surrounding and repeated whitespace; the order of short
    flags; whether short flags are bundled (-tulpn) or separated (-t -u -l); and
    surrounding matched quotes around a whitespace-free argument.

    NOT ignored (would change meaning): the exact multiset of flag letters, so
    -tulpn differs from -tuln; the case of flag letters, so ls -R differs from
    ls -r; token boundaries, so a quoted "foo bar" never equals two arguments;
    and every non-flag token, including -9 versus -15, long flags, -d:, and
    filenames, so kill -9 differs from kill -15. Non-flag words are lowercased
    for command-name forgiveness, matching the original behavior.
    """
    flags = []
    words = []
    for raw in _tokenize(text):
        token = _strip_quotes(raw)
        if _SHORT_FLAG.fullmatch(token):
            flags.extend(token[1:])  # the letters only, case preserved
        else:
            words.append(token.lower())
    return tuple(words), tuple(sorted(flags))


def matches(answer, accepted):
    """True if answer is equivalent to any accepted option.

    Equivalence is deliberately narrow: flag order, flag bundling, and
    whitespace only. A missing flag, a wrong flag, a different flag case, or a
    different argument all fail. See _canonical for the exact contract.
    """
    if answer is None:
        return False
    target = _canonical(answer)
    return any(target == _canonical(option) for option in accepted)


# ---------------------------------------------------------------------------
# Stdin drain (prevents desync after a timeout)
# ---------------------------------------------------------------------------

# Set to True when timed_input times out so the next call drains any
# buffered keystrokes the player typed after the timeout fired.
_pending_drain = False


def _drain_stdin(timeout=0.0):
    """Discard any data waiting in stdin.

    After a timeout the player may still press Enter, buffering a line that
    the next prompt would otherwise consume as its own answer. timeout gives a
    brief window to catch input that arrives just after this call starts.
    """
    try:
        while True:
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if not ready:
                break
            line = sys.stdin.readline()
            if not line:  # EOF on the read end
                break
    except (OSError, ValueError):
        pass


def _read_timed(time_limit):
    """Read one line from stdin with a hard timeout. Returns (answer, elapsed, timed_out).

    Does NOT print anything -- all rendering is the caller's responsibility.
    Handles the pending-drain logic to prevent answer desync after a timeout.
    """
    global _pending_drain
    if _pending_drain:
        _drain_stdin(timeout=0.2)
        _pending_drain = False

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

    _pending_drain = True
    return None, time.time() - start, True


def timed_input(prompt, time_limit):
    """Read a line, printing prompt and timeout message (plain-text path).

    Returns (answer, elapsed, timed_out). On timeout or end of input the answer
    is None. Uses select so a real terminal gets a hard cutoff; if select is not
    available (an unusual stdin) it falls back to an untimed read.
    """
    sys.stdout.write(prompt + "\n> ")
    sys.stdout.flush()
    answer, elapsed, timed_out = _read_timed(time_limit)
    if timed_out:
        sys.stdout.write("\n... time!\n")
        sys.stdout.flush()
    return answer, elapsed, timed_out


# --- RECALL ----------------------------------------------------------------

def recall_battle(scheduler, encounter, miss_damage=3,
                  screen=None, zone_id=None, hp=0, max_hp=20):
    """Timed retrieval drill graded by the countdown."""
    accepted = encounter["answers"]
    key = encounter.get("key") or accepted[0]
    limit = int(encounter.get("time_limit", 8))

    scheduler.ensure(key, encounter["prompt"], accepted[0])

    if screen:
        screen.battle_prompt(zone_id, encounter, hp, max_hp)
        answer, elapsed, timed_out = _read_timed(limit)
    else:
        print()
        print("  -- RECALL --")
        banner = "  {} ({} seconds)".format(encounter["prompt"], limit)
        answer, elapsed, timed_out = timed_input(banner, limit)

    correct = (not timed_out) and matches(answer, accepted)
    scheduler.record(key, correct, elapsed, limit)

    if screen:
        screen.battle_result(zone_id, encounter, hp, max_hp,
                             correct, timed_out, accepted[0])
    else:
        if correct:
            print("  Hit. {:.1f}s.".format(elapsed))
        elif timed_out:
            print("  Too slow. The rune was: {}".format(accepted[0]))
        else:
            print("  Miss. The rune was: {}".format(accepted[0]))

    return {"correct": correct, "damage": 0 if correct else miss_damage}


# --- SOLVE -----------------------------------------------------------------

def solve_battle(scheduler, encounter, world_root="world", miss_damage=5,
                 screen=None, zone_id=None, hp=0, max_hp=20, gated=True):
    """Honor-system battle solved in the player's own terminal.

    When gated=False (zones 1-6) the player is trusted unconditionally and no
    confirmation prompt is shown. When gated=True (zone 7+) they must
    self-report whether the command worked.
    """
    key = encounter.get("key") or "find -name"
    objective = encounter["objective"]

    if screen:
        screen.solve_prompt(zone_id, encounter, hp, max_hp, world_root)
    else:
        print()
        print("  -- SOLVE --")
        print("  " + objective)
        hint = encounter.get("hint", "")
        if hint:
            first_cmd = hint.split()[0] if hint.split() else ""
            print("  Usage: {} <args>".format(first_cmd) if first_cmd else "")
        print("  The fake world is under '{}/'. Your real filesystem is untouched.".format(world_root))
        print("  Open another terminal, solve it for real, then come back.")
        _prompt("  Press Enter when you have run it... ")

    if gated:
        reported = _yes_no("  Did the command work?")
    else:
        reported = True

    scheduler.ensure(key, objective, encounter.get("hint", ""))
    scheduler.record(key, reported, 0.0, 0)

    if screen:
        screen.solve_result(zone_id, encounter, hp, max_hp, reported)
    else:
        if reported:
            print("  The gate swings open.")
        else:
            print("  The gate holds. Regroup and try again.")

    return {"correct": reported, "damage": 0 if reported else miss_damage}


# --- VILLAGER --------------------------------------------------------------

def villager_battle(scheduler, encounter, compressed=False, miss_damage=1,
                    screen=None, zone_id=None):
    """Teaching NPC that quiz gates before letting the player pass."""
    if compressed:
        if not _yes_no("  You have met this villager before. Hear the lore again?",
                       default=False):
            for rune in encounter.get("teaches", []):
                scheduler.ensure(rune["command"], rune.get("desc", ""), rune["command"])
            if screen:
                screen.clear()
            print("  You nod and walk past.")
            return {"correct": True, "damage": 0}

    if screen:
        screen.villager_lore(zone_id, encounter)
    else:
        print()
        print("  -- VILLAGER: {} --".format(encounter["name"]))
        print("  " + encounter["lore"])
        print()
        for rune in encounter.get("teaches", []):
            print("    rune {:<12} {}".format(rune["command"], rune.get("desc", "")))
        print()

    quizzes = encounter.get("quizzes", [])
    total_wrong = 0

    for idx, quiz_item in enumerate(quizzes):
        wrong_attempts = 0
        while True:
            if screen:
                screen.villager_quiz(zone_id, encounter, quiz_item,
                                     idx, len(quizzes), wrong_attempts)
                answer = _prompt("")
            else:
                answer = _prompt("  {}\n  > ".format(quiz_item["prompt"]))

            if matches(answer, quiz_item["answers"]):
                if screen:
                    screen.villager_quiz_result(zone_id, encounter, quiz_item,
                                                idx, len(quizzes), correct=True)
                else:
                    print("  Correct. The road opens.")
                break

            wrong_attempts += 1
            total_wrong += 1
            if screen:
                screen.villager_quiz_result(zone_id, encounter, quiz_item,
                                            idx, len(quizzes), correct=False)
            else:
                print("  Not quite. The villager waits.")

    for rune in encounter.get("teaches", []):
        scheduler.seed(rune["command"], rune.get("desc", ""), rune["command"])

    return {"correct": True, "damage": min(total_wrong, 3) * miss_damage}


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
