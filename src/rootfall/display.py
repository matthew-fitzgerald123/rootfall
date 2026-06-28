"""Terminal UI renderer for rootfall.

All drawing goes through Screen. Callers build the game flow; Screen handles
every ANSI escape, layout calculation, and timing pause.

Layout (two-panel):
  ╔══(full width)══════════════════════════════╗
  ║ HEADER LEFT                  HEADER RIGHT  ║
  ╠════════════════════╦═══════════════════════╣
  ║  sprite panel      ║  content panel        ║
  ║  20 cols wide      ║  remaining cols       ║
  ║  (1+18+1)          ║                       ║
  ╚════════════════════╩═══════════════════════╝

The sprite panel is exactly 20 chars wide: one ║, 18 sprite chars, one ║.
The content panel is cols-21 chars wide (border uses 1 more on the right).
"""

import re
import shutil
import sys
import time

from . import art


class Screen:

    # ------------------------------------------------------------------
    # Low-level color / style helpers
    # ------------------------------------------------------------------

    def _c(self, n):
        """ANSI 256 foreground color escape."""
        return "\033[38;5;{}m".format(n)

    def _b(self, n):
        """ANSI 256 background color escape."""
        return "\033[48;5;{}m".format(n)

    def _reset(self):
        return "\033[0m"

    def _bold(self, text):
        return "\033[1m{}\033[22m".format(text)

    def _colored(self, text, fg=None, bold=False):
        parts = []
        if bold:
            parts.append("\033[1m")
        if fg is not None:
            parts.append(self._c(fg))
        parts.append(text)
        parts.append(self._reset())
        return "".join(parts)

    # ------------------------------------------------------------------
    # Terminal geometry and HP bar
    # ------------------------------------------------------------------

    def _cols(self):
        return shutil.get_terminal_size().columns

    def _hp_bar(self, hp, max_hp, width=10):
        """Return a colored HP bar string like 'HP ████░░░░░░ 8/20'."""
        if max_hp <= 0:
            filled = 0
        else:
            filled = int(round(width * max(0, hp) / float(max_hp)))
        filled = min(filled, width)
        empty = width - filled

        bar = (
            self._c(46) + "█" * filled
            + self._c(238) + "░" * empty
            + self._reset()
        )
        return "HP {} {}/{}".format(bar, max(0, hp), max_hp)

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self):
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Word wrap
    # ------------------------------------------------------------------

    def _wrap(self, text, width):
        """Word-wrap text to a list of lines each at most width chars."""
        if width <= 0:
            return [text]
        words = text.split()
        lines = []
        current = []
        length = 0
        for word in words:
            if length == 0:
                current.append(word)
                length = len(word)
            elif length + 1 + len(word) <= width:
                current.append(word)
                length += 1 + len(word)
            else:
                lines.append(" ".join(current))
                current = [word]
                length = len(word)
        if current:
            lines.append(" ".join(current))
        return lines if lines else [""]

    # ------------------------------------------------------------------
    # Sprite line renderer
    # ------------------------------------------------------------------

    def _render_sprite_line(self, sprite, line_index):
        """Return a colored 18-char string for one sprite line."""
        line = sprite["lines"][line_index]
        color = sprite["accents"].get(line_index, sprite["primary"])
        return self._c(color) + line + self._reset()

    # ------------------------------------------------------------------
    # Core two-panel renderer
    # ------------------------------------------------------------------

    def _draw_panel(self, zone_id, sprite_key, header_left, header_right,
                    hp, max_hp, content_lines, await_input=True):
        """Draw the full two-panel frame to stdout.

        sprite_key is either "villager" or "enemy".
        content_lines is a list of plain strings already wrapped.
        If await_input is True, end with a prompt arrow on stdout; the
        caller then reads stdin.
        """
        cols = self._cols()
        zone_color, zone_dim = art.get_zone_colors(zone_id)

        if sprite_key == "villager":
            sprite = art.get_villager(zone_id)
        else:
            sprite = art.get_enemy(zone_id)

        # Panel geometry
        left_inner = 18       # sprite content width
        left_total = 20       # ║ + 18 + ║
        right_inner = max(cols - left_total - 1, 10)  # remaining - right border

        border = self._c(zone_color)
        reset = self._reset()

        def hbar(left_cap, mid, cross_left, right_cap, width=None):
            """Build a horizontal border line.

            Total visible chars: left_cap(1) + inner_left + cross_left(1)
                                 + inner_right + right_cap(1)
                               = inner_left + inner_right + 3
                               = w  =>  inner_right = w - inner_left - 3
            """
            w = width if width is not None else cols
            inner_left = left_inner + 2   # left panel inner including padding chars
            inner_right = max(w - inner_left - 3, 0)
            return (
                border
                + left_cap
                + mid * inner_left
                + cross_left
                + mid * inner_right
                + right_cap
                + reset
            )

        # ── Top border ────────────────────────────────────────────────
        top = border + "╔" + "═" * (cols - 2) + "╗" + reset

        # ── Header line ───────────────────────────────────────────────
        hp_str = self._hp_bar(hp, max_hp)
        # Strip ANSI from hp_str for length counting
        _ansi_re = re.compile(r"\033\[[^m]*m")
        hp_visible = _ansi_re.sub("", hp_str)

        header_left_str = self._colored(" " + header_left, fg=zone_color, bold=True)
        header_right_str = " " + hp_str + "  " + self._colored(header_right, fg=zone_dim)

        left_vis = len(header_left) + 1
        right_vis = len(hp_visible) + 2 + len(header_right) + 2
        padding = cols - 2 - left_vis - right_vis
        if padding < 0:
            padding = 0

        header_line = (
            border + "║" + reset
            + header_left_str
            + " " * padding
            + header_right_str
            + border + "║" + reset
        )

        # ── Separator ─────────────────────────────────────────────────
        sep = hbar("╠", "═", "╬", "╣")

        # ── Content rows ──────────────────────────────────────────────
        # Sprite lines: 13. We fill the left panel height to match content.
        SPRITE_LINES = 13
        right_rows = list(content_lines)

        # We need at least SPRITE_LINES rows total; pad content if shorter.
        while len(right_rows) < SPRITE_LINES:
            right_rows.append("")

        # If content is taller than sprite, we just let it be (sprite rows
        # repeat blank for the extra lines).
        body_rows = max(SPRITE_LINES, len(right_rows))

        # Centre the sprite vertically if body_rows > SPRITE_LINES.
        sprite_top_pad = (body_rows - SPRITE_LINES) // 2

        rows = []
        for i in range(body_rows):
            sprite_idx = i - sprite_top_pad
            if 0 <= sprite_idx < SPRITE_LINES:
                left_cell = self._render_sprite_line(sprite, sprite_idx)
                left_vis_len = left_inner  # sprite lines are exactly 18 chars
            else:
                left_cell = " " * left_inner
                left_vis_len = left_inner

            right_cell = right_rows[i] if i < len(right_rows) else ""
            right_pad = right_inner - len(right_cell)
            if right_pad < 0:
                right_cell = right_cell[:right_inner]
                right_pad = 0

            row = (
                border + "║" + reset
                + left_cell
                + border + "║" + reset
                + " " + right_cell + " " * max(0, right_pad - 1)
                + border + "║" + reset
            )
            rows.append(row)

        # ── Bottom border ─────────────────────────────────────────────
        bottom = hbar("╚", "═", "╩", "╝")

        # ── Render ────────────────────────────────────────────────────
        self.clear()
        out = [top, header_line, sep] + rows + [bottom]
        sys.stdout.write("\n".join(out) + "\n")
        sys.stdout.flush()

        if await_input:
            sys.stdout.write("  > ")
            sys.stdout.flush()

    # ------------------------------------------------------------------
    # Zone transition
    # ------------------------------------------------------------------

    # Thematic banners: 3-5 lines each, ~50 chars wide.
    _ZONE_BANNERS = {
        "zone01_navigation": [
            r"   / tree of paths \    / tree of paths \\   ",
            r"  /--+--+--+--+---\\  /--+--+--+--+---\\  ",
            r" | pwd  cd  ls  find |  tree . . . . . |  ",
            r"  \\________________//                     ",
        ],
        "zone02_earthmoving": [
            r"  ___  ___  ___  ___  ___  ___",
            r" |   ||   ||   ||   ||   ||   |",
            r" | mkdir  rmdir  mv  cp  touch |",
            r" |___|'---|'---|'---|'---|'---|'",
            r"   THE EARTHMOVERS BUILD THE PATH",
        ],
        "zone03_sight": [
            r"  ,--. cat .--. grep .--. wc .--,",
            r" / -- ====  -- ====  -- ==== -- \\",
            r"|  RECORDS SCROLL ENDLESSLY HERE  |",
            r" \\ -- ====  -- ====  -- ==== -- //",
            r"  '--. tail .--. head .--. less .--'",
        ],
        "zone04_permission_gates": [
            r"  [rwx][rwx][rwx]  [---][---][---]",
            r"   |||  |||  |||    |||  |||  |||",
            r"  THE GATES STAND. chmod OPENS THEM.",
            r"   |||  |||  |||    |||  |||  |||",
            r"  [rw-][r--][---]  [rwx][rwx][rwx]",
        ],
        "zone05_stream_weavers": [
            r"  stdin ~~~> | cut | ~~~> | sort | ~~~>",
            r"  ~~~> | uniq | ~~~> | wc | ~~~> stdout",
            r"        STREAMS WEAVE THROUGH THE PIPE",
            r"  cmd1 | cmd2 | cmd3 | cmd4 | cmd5 ...",
        ],
        "zone06_living_realm": [
            r"   ps aux | grep wraithd",
            r"   kill -9 [PID]         kill -15 [PID]",
            r"   THE LIVING REALM BREATHES WITH DAEMONS",
            r"   proc/<pid>/status  .  proc/<pid>/cmdline",
        ],
        "zone07_frontier": [
            r"  ))) ))) ))) SIGNAL BOUNDARY ))) ))) )))",
            r"   ss -tulpn | grep :8080",
            r"  netstat  .  ping  .  traceroute  .  ss",
            r"  ))) ))) ))) THE FRONTIER WATCHES ))) ))",
        ],
        "zone08_deep_system": [
            r"   * . * . * . DEEP SYSTEM . * . * . *",
            r"   tar -czf  .  du -sh  .  rsync -av",
            r"   =-=- THE ARCHIVE AT THE BOTTOM =-=-",
            r"   * . * . * . * . * . * . * . * . * .",
        ],
    }

    def zone_transition(self, zone_id, zone_name, zone_path, zone_theme, cleared):
        """Full-width banner displayed when entering a zone."""
        cols = self._cols()
        zone_color, zone_dim = art.get_zone_colors(zone_id)

        self.clear()
        border = self._c(zone_color)
        reset = self._reset()
        dim = self._c(zone_dim)

        top = border + "╔" + "═" * (cols - 2) + "╗" + reset
        mid = border + "╠" + "═" * (cols - 2) + "╣" + reset
        bot = border + "╚" + "═" * (cols - 2) + "╝" + reset

        def full_row(text, color=None, bold=False):
            c = color if color is not None else zone_color
            inner = cols - 4
            vis = text[:inner]
            pad = inner - len(vis)
            return (
                border + "║" + reset
                + " "
                + self._colored(vis, fg=c, bold=bold)
                + " " * pad
                + " "
                + border + "║" + reset
            )

        cleared_tag = "  [CLEARED]" if cleared else ""
        title = "  ZONE: {}{}".format(zone_name.upper(), cleared_tag)
        path_line = "  {}".format(zone_path)
        theme_line = "  {}".format(zone_theme)

        banners = self._ZONE_BANNERS.get(zone_id, [""])

        rows = [top, full_row(title, bold=True), full_row(path_line, color=zone_dim), mid]
        for banner_line in banners:
            rows.append(full_row(banner_line, color=zone_dim))
        rows += [mid, full_row(theme_line, color=zone_dim), bot]

        sys.stdout.write("\n".join(rows) + "\n")
        sys.stdout.flush()
        input("\n  Press Enter to descend... ")

    # ------------------------------------------------------------------
    # Villager lore screen
    # ------------------------------------------------------------------

    def villager_lore(self, zone_id, encounter):
        """Display villager lore and all runes. Wait for Enter."""
        zone_color, zone_dim = art.get_zone_colors(zone_id)
        sprite = art.get_villager(zone_id)
        inner_width = max(self._cols() - 22, 20)

        lines = []
        lines.append(self._colored(encounter["name"], fg=zone_color, bold=True))
        lines.append("")

        for wrap_line in self._wrap(encounter.get("lore", ""), inner_width - 2):
            lines.append(wrap_line)
        lines.append("")
        lines.append(self._colored("Runes taught:", fg=zone_dim))
        lines.append("")
        for rune in encounter.get("teaches", []):
            cmd = self._colored(rune["command"], fg=zone_color, bold=True)
            desc = rune.get("desc", "")
            rune_line = "  {} -- {}".format(rune["command"], desc)
            for wl in self._wrap(rune_line, inner_width - 2):
                lines.append(wl)
        lines.append("")
        lines.append(self._colored("Press Enter to continue...", fg=zone_dim))

        self._draw_panel(
            zone_id=zone_id,
            sprite_key="villager",
            header_left=encounter["name"],
            header_right="LORE",
            hp=0,
            max_hp=0,
            content_lines=lines,
            await_input=False,
        )
        input()

    # ------------------------------------------------------------------
    # Villager quiz
    # ------------------------------------------------------------------

    def villager_quiz(self, zone_id, encounter, quiz_item, idx, total, wrong_attempts):
        """Draw quiz frame. Does not wait — caller reads answer after."""
        zone_color, zone_dim = art.get_zone_colors(zone_id)
        inner_width = max(self._cols() - 22, 20)

        progress = "Quiz {}/{}".format(idx + 1, total)
        lines = []
        lines.append(self._colored(encounter["name"], fg=zone_color, bold=True))
        lines.append(self._colored(progress, fg=zone_dim))
        lines.append("")

        for wl in self._wrap(quiz_item["prompt"], inner_width - 2):
            lines.append(wl)
        lines.append("")

        if wrong_attempts > 0:
            hint_text = "  (Attempts: {})  Keep trying.".format(wrong_attempts)
            lines.append(self._colored(hint_text, fg=196))
            lines.append("")

        self._draw_panel(
            zone_id=zone_id,
            sprite_key="villager",
            header_left=encounter["name"],
            header_right=progress,
            hp=0,
            max_hp=0,
            content_lines=lines,
            await_input=True,
        )

    # ------------------------------------------------------------------
    # Villager quiz result
    # ------------------------------------------------------------------

    def villager_quiz_result(self, zone_id, encounter, quiz_item, idx, total, correct):
        """Redraw with colored result then sleep 0.8s."""
        zone_color, zone_dim = art.get_zone_colors(zone_id)
        inner_width = max(self._cols() - 22, 20)

        progress = "Quiz {}/{}".format(idx + 1, total)
        lines = []
        lines.append(self._colored(encounter["name"], fg=zone_color, bold=True))
        lines.append(self._colored(progress, fg=zone_dim))
        lines.append("")

        for wl in self._wrap(quiz_item["prompt"], inner_width - 2):
            lines.append(wl)
        lines.append("")

        if correct:
            lines.append(self._colored("  Correct!", fg=46, bold=True))
        else:
            lines.append(self._colored("  Not quite.", fg=196, bold=True))
            answer_line = "  Answer: {}".format(quiz_item["answers"][0])
            lines.append(self._colored(answer_line, fg=zone_dim))

        self._draw_panel(
            zone_id=zone_id,
            sprite_key="villager",
            header_left=encounter["name"],
            header_right=progress,
            hp=0,
            max_hp=0,
            content_lines=lines,
            await_input=False,
        )
        time.sleep(0.8)

    # ------------------------------------------------------------------
    # Battle prompt
    # ------------------------------------------------------------------

    def battle_prompt(self, zone_id, encounter, hp, max_hp):
        """Draw enemy recall prompt. Does not wait — caller reads answer."""
        zone_color, zone_dim = art.get_zone_colors(zone_id)
        inner_width = max(self._cols() - 22, 20)
        limit = int(encounter.get("time_limit", 8))

        lines = []
        lines.append(self._colored("-- RECALL BATTLE --", fg=zone_color, bold=True))
        lines.append(self._colored(art.get_enemy(zone_id)["name"], fg=zone_dim))
        lines.append("")

        for wl in self._wrap(encounter.get("prompt", ""), inner_width - 2):
            lines.append(wl)
        lines.append("")
        lines.append(self._colored(
            "  ({} seconds)".format(limit), fg=zone_dim
        ))
        lines.append("")

        self._draw_panel(
            zone_id=zone_id,
            sprite_key="enemy",
            header_left=art.get_enemy(zone_id)["name"],
            header_right="BATTLE",
            hp=hp,
            max_hp=max_hp,
            content_lines=lines,
            await_input=True,
        )

    # ------------------------------------------------------------------
    # Battle result
    # ------------------------------------------------------------------

    def battle_result(self, zone_id, encounter, hp, max_hp, correct, timed_out, shown_answer):
        """Redraw with colored result then sleep 1.2s."""
        zone_color, zone_dim = art.get_zone_colors(zone_id)
        inner_width = max(self._cols() - 22, 20)
        limit = int(encounter.get("time_limit", 8))

        lines = []
        lines.append(self._colored("-- RECALL BATTLE --", fg=zone_color, bold=True))
        lines.append(self._colored(art.get_enemy(zone_id)["name"], fg=zone_dim))
        lines.append("")

        for wl in self._wrap(encounter.get("prompt", ""), inner_width - 2):
            lines.append(wl)
        lines.append("")

        if correct:
            lines.append(self._colored("  Hit!", fg=46, bold=True))
        elif timed_out:
            lines.append(self._colored("  Too slow!", fg=196, bold=True))
            lines.append(self._colored(
                "  The rune was: {}".format(shown_answer), fg=zone_dim
            ))
        else:
            lines.append(self._colored("  Miss.", fg=196, bold=True))
            lines.append(self._colored(
                "  The rune was: {}".format(shown_answer), fg=zone_dim
            ))

        self._draw_panel(
            zone_id=zone_id,
            sprite_key="enemy",
            header_left=art.get_enemy(zone_id)["name"],
            header_right="BATTLE",
            hp=hp,
            max_hp=max_hp,
            content_lines=lines,
            await_input=False,
        )
        time.sleep(1.2)

    # ------------------------------------------------------------------
    # Solve prompt
    # ------------------------------------------------------------------

    # Usage patterns keyed by encounter name (or partial match).
    # Values are generic usage hints that do not reveal the exact answer.
    _SOLVE_USAGE = {
        "The Gatekeeper": "find <path> -name <filename>",
        "The Builder": "mkdir -p <path>/<subdir>",
        "The Watcher": "grep <pattern> <file>  OR  grep -c <pattern> <file>",
        "Counting Errors": "grep <pattern> <file> | wc -l",
        "The Gate Lock": "chmod <mode> <file>",
        "The Roster": "cut -d<delim> -f<field> <file> | sort | uniq -c",
        "The Rogue": "ps aux | grep <name>  THEN  kill -9 <pid>",
        "The Listener": "grep <pattern> <file>",
        "Sealing the Realm": "tar -czf <archive.tar.gz> <path>  ;  tar -tzf <archive>",
        # Fallback patterns by command keyword in hint
        "find": "find <path> -name <pattern>",
        "chmod": "chmod <mode> <file>",
        "cut": "cut -d<delim> -f<field> <file> | sort | uniq",
        "kill": "kill -<signal> <pid>",
        "tar": "tar -czf <archive> <path>",
        "grep": "grep <pattern> <file>",
        "mkdir": "mkdir -p <path>",
    }

    def _derive_usage(self, encounter):
        """Return a generic usage hint string for a solve encounter."""
        name = encounter.get("name", "")
        # Try direct name match first.
        if name in self._SOLVE_USAGE:
            return self._SOLVE_USAGE[name]
        # Try partial name match.
        for key, pattern in self._SOLVE_USAGE.items():
            if key.lower() in name.lower():
                return pattern
        # Fall back to deriving from hint by replacing real paths/filenames.
        hint = encounter.get("hint", "")
        if hint:
            # Find the base command (first word) and look it up.
            first_word = hint.split()[0] if hint.split() else ""
            if first_word in self._SOLVE_USAGE:
                return self._SOLVE_USAGE[first_word]
            return "{} <args>".format(first_word) if first_word else "<command> <args>"
        return "<command> <args>"

    def solve_prompt(self, zone_id, encounter, hp, max_hp, world_root):
        """Draw solve screen with usage hint. Wait for Enter."""
        zone_color, zone_dim = art.get_zone_colors(zone_id)
        inner_width = max(self._cols() - 22, 20)

        usage = self._derive_usage(encounter)
        lines = []
        lines.append(self._colored("-- SOLVE BATTLE --", fg=zone_color, bold=True))
        lines.append(self._colored(encounter.get("name", "Boss"), fg=zone_dim))
        lines.append("")
        lines.append(self._colored("Objective:", fg=zone_color))

        for wl in self._wrap(encounter.get("objective", ""), inner_width - 2):
            lines.append("  " + wl)
        lines.append("")
        lines.append(self._colored("Usage pattern:", fg=zone_dim))
        lines.append("  " + self._colored(usage, fg=zone_color, bold=True))
        lines.append("")
        lines.append(self._colored(
            "  World root: {}/".format(world_root), fg=zone_dim
        ))
        lines.append(self._colored(
            "  Open another terminal and solve it for real.", fg=zone_dim
        ))
        lines.append("")
        lines.append("  Press Enter when ready...")

        self._draw_panel(
            zone_id=zone_id,
            sprite_key="enemy",
            header_left=encounter.get("name", "Boss"),
            header_right="SOLVE",
            hp=hp,
            max_hp=max_hp,
            content_lines=lines,
            await_input=False,
        )
        input()

    # ------------------------------------------------------------------
    # Solve result
    # ------------------------------------------------------------------

    def solve_result(self, zone_id, encounter, hp, max_hp, correct):
        """Redraw with solve result then sleep 1.0s."""
        zone_color, zone_dim = art.get_zone_colors(zone_id)
        inner_width = max(self._cols() - 22, 20)

        lines = []
        lines.append(self._colored("-- SOLVE BATTLE --", fg=zone_color, bold=True))
        lines.append(self._colored(encounter.get("name", "Boss"), fg=zone_dim))
        lines.append("")

        for wl in self._wrap(encounter.get("objective", ""), inner_width - 2):
            lines.append("  " + wl)
        lines.append("")

        if correct:
            lines.append(self._colored("  The gate swings open.", fg=46, bold=True))
        else:
            lines.append(self._colored("  The gate holds.", fg=196, bold=True))
            lines.append(self._colored(
                "  Regroup and try the command again.", fg=zone_dim
            ))

        self._draw_panel(
            zone_id=zone_id,
            sprite_key="enemy",
            header_left=encounter.get("name", "Boss"),
            header_right="SOLVE",
            hp=hp,
            max_hp=max_hp,
            content_lines=lines,
            await_input=False,
        )
        time.sleep(1.0)

    # ------------------------------------------------------------------
    # Intro screen
    # ------------------------------------------------------------------

    def intro(self, cleared, tracked):
        """Full-width intro screen. Does not wait."""
        cols = self._cols()
        self.clear()

        zone_color = 34
        border = self._c(zone_color)
        reset = self._reset()

        top = border + "╔" + "═" * (cols - 2) + "╗" + reset
        bot = border + "╚" + "═" * (cols - 2) + "╝" + reset
        sep = border + "╠" + "═" * (cols - 2) + "╣" + reset

        def row(text, color=None, bold=False, center=False):
            c = color if color is not None else zone_color
            inner = cols - 4
            if center:
                vis = text[:inner]
                pad_left = (inner - len(vis)) // 2
                pad_right = inner - len(vis) - pad_left
                content = " " * pad_left + vis + " " * pad_right
            else:
                vis = text[:inner]
                content = vis + " " * (inner - len(vis))
            return (
                border + "║" + reset
                + " "
                + self._colored(content, fg=c, bold=bold)
                + " "
                + border + "║" + reset
            )

        art_lines = [
            r"  ____  ____  ____  ____  ____  __   __     __   ",
            r" |  _ \/ __ \/ __ \|_  _|  ___|/  \ |  |   |  |  ",
            r" | |_) | |  | |  | | || | |_  / /\ \| |   | |   ",
            r" |    /| |  | |  | | || |  _|/ /__\ \ |___| |___ ",
            r" |_|\_\ \__/ \____/|__||_|  /_/    \_\_____\____|",
        ]

        rows = [top]
        for al in art_lines:
            rows.append(row(al, color=zone_color, bold=True, center=True))
        rows.append(row("", color=zone_color))
        rows.append(row("  A descent through the filesystem. The map is the tree.",
                        color=22, center=True))
        rows.append(sep)
        rows.append(row("  Starting at /    Zones cleared: {}    Commands tracked: {}".format(
            cleared, tracked), color=zone_color))
        rows.append(bot)

        sys.stdout.write("\n".join(rows) + "\n")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Death screen
    # ------------------------------------------------------------------

    def death(self):
        """Full-width death screen. Does not wait."""
        cols = self._cols()
        self.clear()

        color = 196
        border = self._c(color)
        reset = self._reset()

        top = border + "╔" + "═" * (cols - 2) + "╗" + reset
        bot = border + "╚" + "═" * (cols - 2) + "╝" + reset
        sep = border + "╠" + "═" * (cols - 2) + "╣" + reset

        def row(text, c=None, bold=False, center=False):
            fc = c if c is not None else color
            inner = cols - 4
            if center:
                vis = text[:inner]
                pad_left = (inner - len(vis)) // 2
                pad_right = inner - len(vis) - pad_left
                content = " " * pad_left + vis + " " * pad_right
            else:
                vis = text[:inner]
                content = vis + " " * (inner - len(vis))
            return (
                border + "║" + reset
                + " "
                + self._colored(content, fg=fc, bold=bold)
                + " "
                + border + "║" + reset
            )

        skull_lines = [
            r"        ___",
            r"       /   \      YOU HAVE FALLEN",
            r"      | x x |",
            r"      |  ^  |     HP reached zero.",
            r"       \_W_/      You wake at the root, /.",
            r"      /|   |\     Run state wiped.",
            r"     / |   | \    Your memory is intact.",
        ]

        rows = [top]
        for sl in skull_lines:
            rows.append(row(sl, c=color, bold=True, center=True))
        rows.append(sep)
        rows.append(row("  The descent collapses. Begin again.", c=88, center=True))
        rows.append(bot)

        sys.stdout.write("\n".join(rows) + "\n")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Victory screen
    # ------------------------------------------------------------------

    def victory(self, zones, hp):
        """Full-width victory screen. Does not wait."""
        cols = self._cols()
        self.clear()

        color = 220
        border = self._c(color)
        reset = self._reset()

        top = border + "╔" + "═" * (cols - 2) + "╗" + reset
        bot = border + "╚" + "═" * (cols - 2) + "╝" + reset
        sep = border + "╠" + "═" * (cols - 2) + "╣" + reset

        def row(text, c=None, bold=False, center=False):
            fc = c if c is not None else color
            inner = cols - 4
            if center:
                vis = text[:inner]
                pad_left = (inner - len(vis)) // 2
                pad_right = inner - len(vis) - pad_left
                content = " " * pad_left + vis + " " * pad_right
            else:
                vis = text[:inner]
                content = vis + " " * (inner - len(vis))
            return (
                border + "║" + reset
                + " "
                + self._colored(content, fg=fc, bold=bold)
                + " "
                + border + "║" + reset
            )

        victory_art = [
            r"    *   .       .    *    .       .   *",
            r"  .   *    YOU HAVE REACHED THE DEEP   .",
            r"    .    *   .    *   .    *   .    *   ",
            r"  *   .   SYSTEM ARCHON DEFEATED   .   *",
            r"    .    *   .    *   .    *   .    *   ",
        ]

        rows = [top]
        for va in victory_art:
            rows.append(row(va, c=color, bold=True, center=True))
        rows.append(sep)
        rows.append(row(
            "  Cleared all {} zones.  HP remaining: {}.".format(len(zones), max(0, hp)),
            c=226, center=True
        ))
        rows.append(row(
            "  Mastered commands stay buried. Run again: only gaps remain.",
            c=136, center=True
        ))
        rows.append(bot)

        sys.stdout.write("\n".join(rows) + "\n")
        sys.stdout.flush()
