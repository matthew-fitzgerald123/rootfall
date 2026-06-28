"""Scaffolds a self-contained fake Filesystem Hierarchy Standard world.

The dungeon map IS the filesystem. To make that safe and portable, the game
builds its own world/ directory and never touches the player's real root. That
also lets /proc work on macOS, where it does not otherwise exist: the files
under world/proc are fabricated.

Themed locations referenced in the lore:
  /etc      City of Configs   (villagers live here)
  /var/log  Hall of Records
  /proc     Living Realm       (fake process files)
  /dev      Forge
  /bin      The Armory
  /usr/bin  The Armory annex

For this slice the world also grows a small navigation tree with a hidden target
file so the Zone 1 boss can force a real find against it.
"""

import os

# The Zone 1 boss target: a key buried several directories deep under etc.
BOSS_TARGET_DIR = "etc/keepers/inner/vault"
BOSS_TARGET_FILE = "gatekeeper.key"

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
    "proc",
    "proc/1",
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
]

_FILES = {
    "etc/hostname": "rootfall\n",
    "etc/motd": "Welcome to the City of Configs.\n",
    "etc/network/interfaces.conf": "iface eth0 inet dhcp\n",
    "var/log/messages": "boot: descent initialized\nwarden: gate sealed\n",
    "var/log/old/messages.1": "archived records of older runs\n",
    "bin/ls": "(armory) base command: ls\n",
    "bin/find": "(armory) base command: find\n",
    "usr/bin/tree": "(armory annex) base command: tree\n",
    "srv/maps/north/ridge/config.yaml": "region: north\n",
    "srv/maps/south/config.yaml": "region: south\n",
}

# Fabricated process files so /proc lore lands even on macOS.
_PROC_FILES = {
    "proc/cpuinfo": "processor : 0\nmodel name : rootfall virtual core\n",
    "proc/meminfo": "MemTotal: 1024 kB\nMemFree: 512 kB\n",
    "proc/1/status": "Name:\tinit\nState:\tR (running)\nPid:\t1\n",
    "proc/1/cmdline": "/sbin/init\n",
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

    return root


def boss_target_path(root="world"):
    """Where the Zone 1 boss key actually lives, for reference and tests."""
    return os.path.join(root, BOSS_TARGET_DIR, BOSS_TARGET_FILE)
