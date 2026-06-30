#!/usr/bin/env python3
"""
rootfall_exam.py — pure command-matching drill for the 8-zone command list.

Each question gives you what a command DOES. You type the command. It's
auto-graded. No essays, no self-grading.

Run:   python3 rootfall_exam.py            # menu: full drill or review missed
       python3 rootfall_exam.py --review   # jump straight to last run's misses
       python3 rootfall_exam.py --full     # skip the menu, full drill
       python3 rootfall_exam.py --reset     # clear the saved missed list

Missed commands are saved between runs to ~/.rootfall/missed.json (a "mistakes
box"). Getting one right in any run removes it from the box; missing it adds it.
At the end of a run you can immediately retry the ones you just missed.

At the answer prompt, type the command, or a colon-command to navigate:
  :n  next      :p  prev      :g 12  jump to 12     :l  overview
  :s  score     :r  next wrong/blank     :reveal  show answer (marks wrong)
  :h  help      :q  quit + report

The grader ignores flag ORDER ( ss -tulpn == ss -nlptu ), strips a leading
"./" on paths, and treats file/dir/arg slots as wildcards — but flag LETTERS
and casing must be exact ( -R != -r, -I != -i ). If it's ever wrong, you can
override the verdict.
"""

import os
import re
import sys
import json

# --------------------------------------------------------------------- color
NO_COLOR = bool(os.environ.get("NO_COLOR"))
def _c(code, s): return s if NO_COLOR else f"\033[{code}m{s}\033[0m"
def bold(s): return _c("1", s)
def dim(s): return _c("2", s)
def green(s): return _c("32", s)
def red(s): return _c("31", s)
def yellow(s): return _c("33", s)
def cyan(s): return _c("36", s)
def mag(s): return _c("35", s)
def clear(): os.system("cls" if os.name == "nt" else "clear")

# --------------------------------------------------------------------- matcher
def _norm_tok(tok):
    if tok.startswith("./") and len(tok) > 2:
        tok = tok[2:]
    if re.fullmatch(r"-[A-Za-z]{2,}", tok):       # combined flags: sort letters, keep case
        tok = "-" + "".join(sorted(tok[1:]))
    return tok

def normalize(s):
    s = re.sub(r"\s+", " ", s.strip())
    if not s:
        return ""
    return " ".join(_norm_tok(t) for t in s.split(" "))

def _match_template(ans_tokens, spec_str):
    """Template tokens:
        literal      -> must equal normalized answer token (flags get sorted)
        <x>          -> required wildcard (any one token)
        <x?>         -> optional wildcard
        <!x> / <!x?> -> wildcard that must NOT be a flag (not starting with '-')
    """
    spec = spec_str.split(" ")
    i, n = 0, len(ans_tokens)
    for tok in spec:
        if tok.startswith("<") and tok.endswith(">"):
            inner = tok[1:-1]
            nonflag = inner.startswith("!")
            optional = inner.endswith("?")
            avail = i < n and not (nonflag and ans_tokens[i].startswith("-"))
            if optional:
                if avail:
                    i += 1
            else:
                if avail:
                    i += 1
                else:
                    return False
        else:
            if i < n and ans_tokens[i] == _norm_tok(tok):
                i += 1
            else:
                return False
    return i == n

def matches(ans, q):
    toks = normalize(ans).split(" ") if ans.strip() else []
    for t in q.get("templates", []):
        if _match_template(toks, t):
            return True
    rf = q.get("regex_full")
    if rf and re.fullmatch(rf, normalize(ans)):
        return True
    return False

# --------------------------------------------------------------------- questions
# Every entry: what the command DOES (prompt) -> the command (answer + matcher).
Q = [
 # Zone 1 — Navigation
 {"zone":"Zone 1 — Navigation","q":"Long listing: permissions, owner, size, timestamp.",
  "templates":["ls -l <!path?>"],"answer":"ls -l"},
 {"zone":"Zone 1 — Navigation","q":"Show hidden (dot-prefixed) entries.",
  "templates":["ls -a <!path?>"],"answer":"ls -a"},
 {"zone":"Zone 1 — Navigation","q":"Recurse into every subdirectory.",
  "templates":["ls -R <!path?>"],"answer":"ls -R"},

 # Zone 2 — Earthmoving
 {"zone":"Zone 2 — Earthmoving","q":"Create a directory and any missing parents in one stroke.",
  "templates":["mkdir -p <dir?>"],"answer":"mkdir -p <dir>"},
 {"zone":"Zone 2 — Earthmoving","q":"Copy a directory and everything inside, recursively.",
  "templates":["cp -r <src?> <dst?>"],"answer":"cp -r <src> <dst>"},
 {"zone":"Zone 2 — Earthmoving","q":"Remove a tree forcibly, no prompts.",
  "templates":["rm -rf <path?>"],"answer":"rm -rf <path>"},
 {"zone":"Zone 2 — Earthmoving","q":"Move or rename in a single step.",
  "templates":["mv <src?> <dst?>"],"answer":"mv <src> <dst>"},
 {"zone":"Zone 2 — Earthmoving","q":"Create a symbolic link (signpost to another path).",
  "templates":["ln -s <target?> <link?>"],"answer":"ln -s <target> <link>"},
 {"zone":"Zone 2 — Earthmoving","q":"Create an empty file or update its timestamp.",
  "templates":["touch <file?>"],"answer":"touch <file>"},

 # Zone 3 — Sight
 {"zone":"Zone 3 — Sight","q":"Search recursively through every file in a tree.",
  "templates":["grep -r <pat?> <!path?>"],"answer":"grep -r <pattern> <path>"},
 {"zone":"Zone 3 — Sight","q":"Invert: show lines that do NOT match.",
  "templates":["grep -v <pat?> <file?>"],"answer":"grep -v <pattern> <file>"},
 {"zone":"Zone 3 — Sight","q":"Case-insensitive match.",
  "templates":["grep -i <pat?> <file?>"],"answer":"grep -i <pattern> <file>"},
 {"zone":"Zone 3 — Sight","q":"Prefix each match with its line number.",
  "templates":["grep -n <pat?> <file?>"],"answer":"grep -n <pattern> <file>"},
 {"zone":"Zone 3 — Sight","q":"Follow a file, printing new lines as they arrive.",
  "templates":["tail -f <file?>"],"answer":"tail -f <file>"},
 {"zone":"Zone 3 — Sight","q":"Show the last N lines.",
  "templates":["tail -n <num> <file?>","tail -n <num>"],"answer":"tail -n <N> <file>"},
 {"zone":"Zone 3 — Sight","q":"Show the first N lines.",
  "templates":["head -n <num> <file?>","head -n <num>"],"answer":"head -n <N> <file>"},
 {"zone":"Zone 3 — Sight","q":"Count lines.",
  "templates":["wc -l <file?>"],"answer":"wc -l <file>"},

 # Zone 4 — Permission Gates
 {"zone":"Zone 4 — Permission Gates","q":"rwx for owner, r-x for group and others.",
  "templates":["chmod 755 <path?>"],"answer":"chmod 755 <path>"},
 {"zone":"Zone 4 — Permission Gates","q":"rw- for owner, r-- for group and others.",
  "templates":["chmod 644 <path?>"],"answer":"chmod 644 <path>"},
 {"zone":"Zone 4 — Permission Gates","q":"rw- for owner only, locked to everyone else.",
  "templates":["chmod 600 <path?>"],"answer":"chmod 600 <path>"},
 {"zone":"Zone 4 — Permission Gates","q":"Add the execute bit symbolically.",
  "templates":["chmod +x <file?>"],"answer":"chmod +x <file>"},
 {"zone":"Zone 4 — Permission Gates","q":"Apply a permission change recursively through a tree.",
  "templates":["chmod -R <mode?> <path?>"],"answer":"chmod -R <mode> <path>"},
 {"zone":"Zone 4 — Permission Gates","q":"Set both owner and group at once.",
  "templates":["chown <owner> <file?>"],"answer":"chown user:group <file>"},
 {"zone":"Zone 4 — Permission Gates","q":"Show/set the default permission mask for new files.",
  "templates":["umask <mode?>"],"answer":"umask"},

 # Zone 5 — Stream Weavers
 {"zone":"Zone 5 — Stream Weavers","q":"Substitute first occurrence of old with new per line.",
  "regex_full":r"^sed 's/[^/]*/[^/]*/g?'( \S+)?$","answer":"sed 's/old/new/'"},
 {"zone":"Zone 5 — Stream Weavers","q":"Print a chosen whitespace-separated field.",
  "regex_full":r"^awk '\{print \$\d+\}'( \S+)?$","answer":"awk '{print $2}'"},
 {"zone":"Zone 5 — Stream Weavers","q":"Cut a field from delimited text (: delimiter, field 1).",
  "regex_full":r"^cut -d: -f\d+( \S+)?$","answer":"cut -d: -f1"},
 {"zone":"Zone 5 — Stream Weavers","q":"Sort lines lexicographically.",
  "templates":["sort <!file?>"],"answer":"sort"},
 {"zone":"Zone 5 — Stream Weavers","q":"Sort numerically rather than lexically.",
  "templates":["sort -n <!file?>"],"answer":"sort -n"},
 {"zone":"Zone 5 — Stream Weavers","q":"Collapse adjacent duplicates and prefix each with its count.",
  "templates":["uniq -c <!file?>"],"answer":"uniq -c"},
 {"zone":"Zone 5 — Stream Weavers","q":"Translate lower-case to upper-case.",
  "templates":["tr a-z A-Z","tr [:lower:] [:upper:]"],"answer":"tr a-z A-Z"},

 # Zone 6 — The Living Realm
 {"zone":"Zone 6 — The Living Realm","q":"BSD-style listing of every process with CPU and memory.",
  "templates":["ps aux"],"answer":"ps aux"},
 {"zone":"Zone 6 — The Living Realm","q":"Full standard listing with parent PIDs.",
  "templates":["ps -ef"],"answer":"ps -ef"},
 {"zone":"Zone 6 — The Living Realm","q":"Send SIGTERM: polite, catchable stop.",
  "templates":["kill -15 <pid?>"],"answer":"kill -15 <PID>"},
 {"zone":"Zone 6 — The Living Realm","q":"Send SIGKILL: uncatchable force-kill.",
  "templates":["kill -9 <pid?>"],"answer":"kill -9 <PID>"},
 {"zone":"Zone 6 — The Living Realm","q":"Live, sorted view of running processes.",
  "templates":["top"],"answer":"top"},
 {"zone":"Zone 6 — The Living Realm","q":"List the shell's background jobs.",
  "templates":["jobs"],"answer":"jobs"},
 {"zone":"Zone 6 — The Living Realm","q":"Launch a command at scheduling priority 10 (lowered).",
  "templates":["nice -n <num> <cmd?>"],"answer":"nice -n 10 <cmd>"},

 # Zone 7 — The Frontier
 {"zone":"Zone 7 — The Frontier","q":"TCP+UDP listening sockets, numeric, with process (modern).",
  "templates":["ss -tulpn"],"answer":"ss -tulpn"},
 {"zone":"Zone 7 — The Frontier","q":"TCP-only listening sockets, numeric, with process (modern).",
  "templates":["ss -tlnp"],"answer":"ss -tlnp"},
 {"zone":"Zone 7 — The Frontier","q":"TCP+UDP listening sockets, numeric, with process (deprecated tool).",
  "templates":["netstat -tulpn"],"answer":"netstat -tulpn"},
 {"zone":"Zone 7 — The Frontier","q":"TCP-only listening sockets, numeric, with process (deprecated tool).",
  "templates":["netstat -tlnp"],"answer":"netstat -tlnp"},
 {"zone":"Zone 7 — The Frontier","q":"Capture packets on a named interface.",
  "templates":["tcpdump -i <iface?>"],"answer":"tcpdump -i <iface>"},
 {"zone":"Zone 7 — The Frontier","q":"Capture packets without resolving hosts or ports.",
  "templates":["tcpdump -nn <a?> <b?>"],"answer":"tcpdump -nn"},
 {"zone":"Zone 7 — The Frontier","q":"Fetch response headers only.",
  "templates":["curl -I <url?>"],"answer":"curl -I <url>"},
 {"zone":"Zone 7 — The Frontier","q":"Silent: no progress meter or errors.",
  "templates":["curl -s <url?>"],"answer":"curl -s <url>"},
 {"zone":"Zone 7 — The Frontier","q":"Terse DNS answer, just the records.",
  "templates":["dig +short <!name?>","dig <!name> +short"],"answer":"dig +short <name>"},
 {"zone":"Zone 7 — The Frontier","q":"Query the A (IPv4 address) record.",
  "templates":["dig A <!name?>","dig <!name> A"],"answer":"dig A <name>"},
 {"zone":"Zone 7 — The Frontier","q":"List all open network files (sockets).",
  "templates":["lsof -i"],"answer":"lsof -i"},
 {"zone":"Zone 7 — The Frontier","q":"Show which process holds a specific port.",
  "templates":["lsof -i <port>"],"answer":"lsof -i :PORT"},

 # Zone 8 — Deep System
 {"zone":"Zone 8 — Deep System","q":"Free space per mounted filesystem, human-readable.",
  "templates":["df -h"],"answer":"df -h"},
 {"zone":"Zone 8 — Deep System","q":"Summed, human-readable total size of a directory.",
  "templates":["du -sh <dir?>"],"answer":"du -sh <dir>"},
 {"zone":"Zone 8 — Deep System","q":"Human-readable size of each item.",
  "templates":["du -h <dir?>"],"answer":"du -h <dir>"},
 {"zone":"Zone 8 — Deep System","q":"Memory usage, human-readable.",
  "templates":["free -h"],"answer":"free -h"},
 {"zone":"Zone 8 — Deep System","q":"List block devices as a tree.",
  "templates":["lsblk"],"answer":"lsblk"},
 {"zone":"Zone 8 — Deep System","q":"Show currently mounted filesystems.",
  "templates":["mount"],"answer":"mount"},
 {"zone":"Zone 8 — Deep System","q":"Create a gzip-compressed archive (create, gzip, file).",
  "templates":["tar -czf <arch?> <dir?>"],"answer":"tar -czf <archive.tar.gz> <dir>"},
 {"zone":"Zone 8 — Deep System","q":"Extract a gzip-compressed archive.",
  "templates":["tar -xzf <arch?>"],"answer":"tar -xzf <archive.tar.gz>"},
 {"zone":"Zone 8 — Deep System","q":"List contents of a gzip archive without extracting.",
  "templates":["tar -tzf <arch?>"],"answer":"tar -tzf <archive.tar.gz>"},
 {"zone":"Zone 8 — Deep System","q":"Sync trees: archive mode, verbose.",
  "templates":["rsync -av <src?> <dst?>"],"answer":"rsync -av <src> <dst>"},
 {"zone":"Zone 8 — Deep System","q":"Sync trees: archive mode, verbose, compressed in transit.",
  "templates":["rsync -avz <src?> <dst?>"],"answer":"rsync -avz <src> <dst>"},
]

# --------------------------------------------------------------------- persistence
MISS_FILE = os.path.expanduser("~/.rootfall/missed.json")

def load_missed():
    try:
        with open(MISS_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_missed(missed):
    try:
        os.makedirs(os.path.dirname(MISS_FILE), exist_ok=True)
        with open(MISS_FILE, "w") as f:
            json.dump(sorted(missed), f, indent=0)
    except Exception:
        pass  # never let a save failure crash the drill

# --------------------------------------------------------------------- state
state = {}        # q-index -> {"response":str, "correct":bool, "done":bool}
ACTIVE = []       # the q-indices in play this session, in display order

def score_now():
    done = [i for i in ACTIVE if state.get(i, {}).get("done")]
    correct = sum(1 for i in done if state[i]["correct"])
    return correct, len(done), len(ACTIVE)

def status_tag(i):
    st = state.get(i)
    if not st or not st.get("done"):
        return dim("· blank")
    return green("✓") if st["correct"] else red("✗")

def all_done():
    return all(state.get(i, {}).get("done") for i in ACTIVE)

# --------------------------------------------------------------------- screens
def header(pos, mode):
    cor, ans, tot = score_now()
    idx = ACTIVE[pos]
    tag = "review" if mode == "review" else "drill"
    title = f" rootfall · command {tag}   Q {pos+1}/{tot}   {Q[idx]['zone']} "
    w = max(len(title), 58)
    print(mag("═" * w)); print(bold(title)); print(mag("═" * w))
    print(f" score: {green(str(cor))}/{ans} answered  ·  {tot-ans} blank")
    print()

def render(pos, mode):
    clear(); header(pos, mode)
    q = Q[ACTIVE[pos]]
    print(bold("Does: ") + q["q"]); print()
    st = state.get(ACTIVE[pos])
    if st and st.get("done"):
        print(dim("  you typed:   ") + (st["response"] or dim("(revealed)")))
        print(dim("  verdict:     ") + (green("CORRECT") if st["correct"] else red("WRONG")))
        print(dim("  command:     ") + cyan(q["answer"]))
        print()
    print(dim("  type the command, or :h for navigation"))
    print()

def overview(mode):
    clear()
    print(bold(" Overview")); print(mag("─" * 60))
    last = None
    for pos, idx in enumerate(ACTIVE):
        if Q[idx]["zone"] != last:
            print(); print(cyan(Q[idx]["zone"])); last = Q[idx]["zone"]
        print(f"  {pos+1:>2}. {status_tag(idx)}  {Q[idx]['q'][:52]}")
    cor, ans, tot = score_now()
    print(); print(mag("─" * 60))
    print(f" {green(str(cor))} correct / {ans} answered / {tot} total")
    input(dim("\n  Enter to return..."))

def grade(idx, raw):
    q = Q[idx]
    ok = matches(raw, q)
    print((green("\n  ✓ CORRECT") if ok else red("\n  ✗ WRONG")))
    print(dim("  command:   ") + cyan(q["answer"]))
    if not ok:
        ov = input(yellow("\n  Override to correct? [y/N]: ")).strip().lower()
        ok = ov == "y"
    state[idx] = {"response": raw, "correct": ok, "done": True}
    input(dim("\n  Enter to continue..."))

def reveal(idx):
    q = Q[idx]
    print(dim("\n  command: ") + cyan(q["answer"]))
    print(red("  marked wrong (revealed)"))
    state[idx] = {"response": "", "correct": False, "done": True}
    input(dim("\n  Enter to continue..."))

def help_screen():
    clear()
    print(bold(" Navigation")); print(mag("─" * 40))
    for k, v in [("<command>","submit an answer"),(":n","next"),(":p","previous"),
                 (":g N","go to question N"),(":l","overview grid"),(":s","score"),
                 (":r","jump to next blank/wrong"),(":reveal","show the answer"),
                 (":q","quit + report"),(":h","this help")]:
        print(f"  {cyan(k):<22} {v}")
    input(dim("\n  Enter to return..."))

def report(mode):
    clear()
    cor, ans, tot = score_now()
    pct = cor / tot * 100 if tot else 0
    label = "REVIEW REPORT" if mode == "review" else "REPORT"
    print(mag("═" * 60)); print(bold(f" {label}   {cor}/{tot}   ({pct:.0f}%)")); print(mag("═" * 60))
    zones = {}
    for idx in ACTIVE:
        z = Q[idx]["zone"]; zones.setdefault(z, [0, 0]); zones[z][1] += 1
        if state.get(idx, {}).get("correct"): zones[z][0] += 1
    print()
    for z, (gc, gt) in zones.items():
        bar = green("█" * gc) + dim("░" * (gt - gc))
        print(f"  {z:<28} {bar}  {gc}/{gt}")
    missed = [Q[idx] for idx in ACTIVE if state.get(idx, {}).get("done") and not state[idx]["correct"]]
    blanks = [pos + 1 for pos, idx in enumerate(ACTIVE) if not state.get(idx, {}).get("done")]
    if missed:
        print(); print(yellow(" Missed this run:"))
        for q in missed:
            print("   " + red("• ") + cyan(q["answer"]) + dim("   — " + q["q"]))
    if blanks:
        print(); print(dim(" Left blank: " + ", ".join(map(str, blanks))))
    if not missed and not blanks:
        print(); print(green(" Clean sweep."))
    print()

# --------------------------------------------------------------------- session loop
def run_session(mode):
    """Drive the question loop over ACTIVE. Returns when the user quits or
    every active question has been answered."""
    pos, n = 0, len(ACTIVE)
    while True:
        render(pos, mode)
        try:
            raw = input(bold("cmd> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print(); return
        if not raw:
            continue
        if raw.startswith(":"):
            c = raw[1:].strip()
            if c in ("q", "quit"): return
            elif c in ("n", "next", ""): pos = (pos + 1) % n
            elif c in ("p", "prev", "previous"): pos = (pos - 1) % n
            elif c in ("h", "help", "?"): help_screen()
            elif c in ("l", "list", "overview", "s", "score"): overview(mode)
            elif c in ("reveal", "a"):
                reveal(ACTIVE[pos])
                if all_done(): return
                pos = (pos + 1) % n
            elif c in ("r", "review"):
                nxt = next((k for k in range(n)
                            if not state.get(ACTIVE[k], {}).get("done")
                            or not state[ACTIVE[k]]["correct"]), None)
                if nxt is None: input(dim("  nothing blank/wrong. Enter..."))
                else: pos = nxt
            elif c.startswith("g"):
                mm = re.search(r"\d+", c)
                if mm and 0 <= int(mm.group()) - 1 < n: pos = int(mm.group()) - 1
                else: input(red("  usage: :g 12. Enter..."))
            else:
                input(red(f"  unknown ':{c}' (:h for help). Enter..."))
            continue
        grade(ACTIVE[pos], raw)
        if all_done():
            return
        pos = (pos + 1) % n

# --------------------------------------------------------------------- menu / main
def choose_order(full, review):
    while True:
        clear()
        print(bold("\n  rootfall — command-matching drill\n"))
        print(f"  [1] Full drill — {len(full)} commands")
        if review:
            print(f"  [2] Review missed — {len(review)} from last run")
        else:
            print(dim("  [2] Review missed — (none saved yet)"))
        print("  [q] quit\n")
        c = input(bold("  > ")).strip().lower()
        if c in ("1", "full", ""): return list(full), "full"
        if c in ("2", "review") and review: return list(review), "review"
        if c in ("q", "quit"): return None, None

def update_box(missed_box):
    """Right answers leave the box, wrong answers enter it. Persist."""
    for idx in ACTIVE:
        st = state.get(idx)
        if st and st.get("done"):
            if st["correct"]:
                missed_box.discard(Q[idx]["q"])
            else:
                missed_box.add(Q[idx]["q"])
    save_missed(missed_box)

def main():
    args = set(sys.argv[1:])
    missed_box = load_missed()

    if "--reset" in args:
        save_missed(set())
        print("Cleared the saved missed list (~/.rootfall/missed.json).")
        return

    full = list(range(len(Q)))
    prompt_to_idx = {q["q"]: i for i, q in enumerate(Q)}
    review = sorted(prompt_to_idx[p] for p in missed_box if p in prompt_to_idx)

    # pick the starting set
    if "--full" in args:
        order, mode = list(full), "full"
    elif "--review" in args:
        if not review:
            print("No missed commands saved yet — run a full drill first.")
            return
        order, mode = list(review), "review"
    else:
        order, mode = choose_order(full, review)
        if order is None:
            print("Later."); return

    global ACTIVE
    ACTIVE = order

    # play, persist, and offer to immediately retry this run's misses
    while True:
        if mode != "retry":
            clear()
            tag = "Review of last run's misses" if mode == "review" else "Full drill"
            print(bold(f"\n  {tag} — {len(ACTIVE)} commands"))
            print(dim("  what it does -> you type it · auto-graded · :h for nav\n"))
            input(dim("  Enter to begin..."))
        run_session(mode)
        report(mode)
        update_box(missed_box)

        just_missed = [i for i in ACTIVE
                       if state.get(i, {}).get("done") and not state[i]["correct"]]
        if not just_missed:
            print(green("  Nothing left in the box from this run.\n"))
            break
        a = input(yellow(f"  Retry the {len(just_missed)} you just missed now? [y/N]: ")).strip().lower()
        if a != "y":
            print(dim(f"\n  {len(missed_box)} command(s) saved for next time. Run --review to drill them.\n"))
            break
        for i in just_missed:
            state.pop(i, None)   # reset so the retry starts fresh
        ACTIVE = just_missed
        mode = "retry"

if __name__ == "__main__":
    main()