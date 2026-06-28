"""Scaffolds a self-contained fake Filesystem Hierarchy Standard world.

The dungeon map IS the filesystem. To make that safe and portable, the game
builds its own world/ directory and never touches the player's real root. That
also lets /proc work on macOS, where it does not otherwise exist: the files
under world/proc are fabricated.

Themed locations referenced in the lore:
  /etc      City of Configs    (villagers, configs, locked gates)
  /var/log  Hall of Records    (logs to read and grep)
  /proc     Living Realm       (fake process and socket files)
  /dev      Forge
  /bin      The Armory
  /usr/bin  The Armory annex

Each zone's solve boss gets the fixtures it needs here, built under world/ only
and never on the real filesystem:
  Zone 1  a key buried deep under etc for a find -name
  Zone 2  nothing: the player builds the cell block themselves
  Zone 3  var/log/realm.log with mixed INFO/WARN/ERROR lines
  Zone 4  etc/gate.lock shipped at a restrictive mode to chmod open
  Zone 5  etc/roster.db, colon-delimited, for a cut|sort|uniq pipe
  Zone 6  fake proc/<pid>/status files including the rogue wraithd
  Zone 7  var/net/ss.txt, a captured socket table to grep for port 8080
  Zone 8  srv/realm, a small tree to archive with tar and weigh with du
"""

import os

# The Zone 1 boss target: a key buried several directories deep under etc.
BOSS_TARGET_DIR = "etc/keepers/inner/vault"
BOSS_TARGET_FILE = "gatekeeper.key"

# Zone 4 ships the gate locked. The player chmods it open to 644.
GATE_LOCK = "etc/gate.lock"
GATE_LOCK_MODE = 0o600

_DIRS = [
    "etc",
    "etc/init.d",
    "etc/network",
    "etc/keepers",
    "etc/keepers/inner",
    "etc/keepers/inner/vault",
    "var",
    "var/log",
    "var/log/old",
    "var/net",
    "proc",
    "proc/1",
    "proc/4242",
    "proc/6606",
    "dev",
    "bin",
    "usr",
    "usr/bin",
    # The navigation tree the player roams in Zone 1.
    "srv",
    "srv/maps",
    "srv/maps/north",
    "srv/maps/north/ridge",
    "srv/maps/south",
    # The realm tree the player archives and weighs in Zone 8.
    "srv/realm",
    "srv/realm/logs",
    "srv/realm/data",
]

# A seeded log with mixed levels for Zone 3. It carries exactly five ERROR lines
# so the boss "grep ERROR | wc -l" has a clean, checkable answer of 5.
_REALM_LOG = (
    "INFO  boot sequence started\n"
    "INFO  mounting /var\n"
    "WARN  disk usage at 71 percent\n"
    "INFO  warden online\n"
    "ERROR failed to seal gate 7\n"
    "INFO  recall queue primed\n"
    "WARN  clock drift detected\n"
    "ERROR lost contact with the forge\n"
    "INFO  villager spawned\n"
    "ERROR permission denied on gate.lock\n"
    "WARN  retrying network bind\n"
    "ERROR socket bind failed on 8080\n"
    "INFO  descent ready\n"
    "ERROR rogue process detected: wraithd\n"
    "INFO  shutdown deferred\n"
)

# Colon-delimited roster for Zone 5: name:role:zone. The role field repeats so
# that cut -d: -f2 | sort | uniq -c produces a meaningful tally.
_ROSTER_DB = (
    "warden:guard:etc\n"
    "weaver:mage:stream\n"
    "gatekeeper:guard:etc\n"
    "recordkeeper:scribe:varlog\n"
    "forgemaster:smith:dev\n"
    "wraithd:rogue:proc\n"
    "borderwarden:guard:frontier\n"
    "loom-mistress:mage:stream\n"
)

# A captured ss -tulpn style socket table for Zone 7. The line for 8080 ties back
# to the rogue wraithd and its PID from Zone 6.
_SS_OUTPUT = (
    "Netid State  Recv-Q Send-Q Local-Address:Port Peer-Address:Port Process\n"
    "tcp   LISTEN 0      128    0.0.0.0:22         0.0.0.0:*         users:((\"sshd\",pid=712,fd=3))\n"
    "tcp   LISTEN 0      128    0.0.0.0:8080       0.0.0.0:*         users:((\"wraithd\",pid=6606,fd=7))\n"
    "tcp   LISTEN 0      128    127.0.0.1:5432     0.0.0.0:*         users:((\"postgres\",pid=901,fd=5))\n"
    "udp   UNCONN 0      0      0.0.0.0:68         0.0.0.0:*         users:((\"dhclient\",pid=455,fd=6))\n"
)

_FILES = {
    "etc/hostname": "rootfall\n",
    "etc/motd": "Welcome to the City of Configs.\n",
    "etc/network/interfaces.conf": "iface eth0 inet dhcp\n",
    GATE_LOCK: "sealed by the Permission Gates\n",
    "etc/roster.db": _ROSTER_DB,
    "var/log/messages": "boot: descent initialized\nwarden: gate sealed\n",
    "var/log/old/messages.1": "archived records of older runs\n",
    "var/log/realm.log": _REALM_LOG,
    "var/net/ss.txt": _SS_OUTPUT,
    "bin/ls": "(armory) base command: ls\n",
    "bin/find": "(armory) base command: find\n",
    "usr/bin/tree": "(armory annex) base command: tree\n",
    "srv/maps/north/ridge/config.yaml": "region: north\n",
    "srv/maps/south/config.yaml": "region: south\n",
    # The realm tree for Zone 8. Sizes vary so du -sh * | sort -h is meaningful.
    "srv/realm/logs/old.log": "archived realm log\n" * 16,
    "srv/realm/logs/today.log": "todays realm log\n" * 4,
    "srv/realm/data/records.db": "realm record row\n" * 64,
    "srv/realm/data/index.idx": "idx\n" * 8,
}

# Fabricated process files so /proc lore lands even on macOS.
_PROC_FILES = {
    "proc/cpuinfo": "processor : 0\nmodel name : rootfall virtual core\n",
    "proc/meminfo": "MemTotal: 1024 kB\nMemFree: 512 kB\n",
    "proc/1/status": "Name:\tinit\nState:\tR (running)\nPid:\t1\nPPid:\t0\n",
    "proc/1/cmdline": "/sbin/init\n",
    # A benign process for Zone 6 to practice a polite SIGTERM against.
    "proc/4242/status": "Name:\tforged\nState:\tS (sleeping)\nPid:\t4242\nPPid:\t1\n",
    "proc/4242/cmdline": "/usr/sbin/forged\n",
    # The rogue. The boss reads this to confirm the kill target.
    "proc/6606/status": "Name:\twraithd\nState:\tR (running)\nPid:\t6606\nPPid:\t1\nThreads:\t13\n",
    "proc/6606/cmdline": "/tmp/wraithd --listen 8080\n",
}


def build_world(root="world"):
    """Create (or top up) the fake world. Idempotent and safe to call on boot."""
    for relative in _DIRS:
        os.makedirs(os.path.join(root, relative), exist_ok=True)

    contents = {}
    contents.update(_FILES)
    contents.update(_PROC_FILES)
    contents[os.path.join(BOSS_TARGET_DIR, BOSS_TARGET_FILE)] = (
        "You found the gatekeeper. The descent continues.\n"
    )

    for relative, body in contents.items():
        path = os.path.join(root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w") as handle:
                handle.write(body)

    # The Zone 4 gate is reset to its restrictive starting mode every build so
    # the puzzle is fresh on each descent regardless of how the player left it.
    gate = os.path.join(root, GATE_LOCK)
    os.chmod(gate, GATE_LOCK_MODE)

    return root


def boss_target_path(root="world"):
    """Where the Zone 1 boss key actually lives, for reference and tests."""
    return os.path.join(root, BOSS_TARGET_DIR, BOSS_TARGET_FILE)


def expected_fixtures(root="world"):
    """Boss-critical fixture paths, keyed by zone id, for reference and tests.

    Zone 2 is absent on purpose: its boss is built by the player, so the world
    seeds nothing for it.
    """
    return {
        "zone01_navigation": [boss_target_path(root)],
        "zone03_sight": [os.path.join(root, "var/log/realm.log")],
        "zone04_permission_gates": [os.path.join(root, GATE_LOCK)],
        "zone05_stream_weavers": [os.path.join(root, "etc/roster.db")],
        "zone06_living_realm": [
            os.path.join(root, "proc/6606/status"),
            os.path.join(root, "proc/4242/status"),
        ],
        "zone07_frontier": [os.path.join(root, "var/net/ss.txt")],
        "zone08_deep_system": [
            os.path.join(root, "srv/realm/data/records.db"),
            os.path.join(root, "srv/realm/logs/old.log"),
        ],
    }
