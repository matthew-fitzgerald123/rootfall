"""Lightweight integration tests for the campaign and the fake world.

These guard the data-driven contract: every zone file must load and validate
against the schema, and world.py must scaffold every zone's boss fixtures under a
sandbox directory without error and without touching the real filesystem.
"""

import glob
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from rootfall import campaign, world

CAMPAIGN_DIR = os.path.join(ROOT, "campaign")


class CampaignLoadTests(unittest.TestCase):
    def test_all_zone_files_load_and_validate(self):
        files = sorted(glob.glob(os.path.join(CAMPAIGN_DIR, "zone*.yaml")))
        self.assertEqual(len(files), 9, "expected zones 1 through 9")
        for path in files:
            zone = campaign.load_zone_file(path)  # raises CampaignError if bad
            self.assertTrue(zone.id)
            self.assertTrue(zone.commands)
            self.assertTrue(zone.encounters)

    def test_zones_load_and_order_by_filename(self):
        zones = campaign.load_campaign(CAMPAIGN_DIR)
        ids = [z.id for z in zones]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(ids[0], "zone01_navigation")
        self.assertEqual(ids[-1], "zone09_redhat_realm")

    def test_every_zone_has_villager_recall_and_solve(self):
        for zone in campaign.load_campaign(CAMPAIGN_DIR):
            kinds = set(e["type"] for e in zone.encounters)
            self.assertIn("villager", kinds, zone.id)
            self.assertIn("recall", kinds, zone.id)
            self.assertIn("solve", kinds, zone.id)


class WorldFixtureTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.mkdtemp(prefix="rootfall-world-")
        self.root = os.path.join(self.sandbox, "world")

    def tearDown(self):
        shutil.rmtree(self.sandbox, ignore_errors=True)

    def test_build_world_creates_every_zone_fixture(self):
        world.build_world(self.root)
        for zone_id, paths in world.expected_fixtures(self.root).items():
            for path in paths:
                self.assertTrue(os.path.exists(path), "{}: missing {}".format(zone_id, path))

    def test_build_world_is_idempotent(self):
        world.build_world(self.root)
        world.build_world(self.root)  # must not raise on a second pass
        self.assertTrue(os.path.exists(world.boss_target_path(self.root)))

    def test_gate_lock_starts_restrictive(self):
        world.build_world(self.root)
        gate = os.path.join(self.root, world.GATE_LOCK)
        mode = os.stat(gate).st_mode & 0o777
        self.assertEqual(mode, world.GATE_LOCK_MODE)

    def test_realm_log_has_five_error_lines(self):
        world.build_world(self.root)
        with open(os.path.join(self.root, "var/log/realm.log")) as handle:
            errors = [line for line in handle if line.startswith("ERROR")]
        self.assertEqual(len(errors), 5)

    def test_rogue_process_status_is_present(self):
        world.build_world(self.root)
        with open(os.path.join(self.root, "proc/6606/status")) as handle:
            status = handle.read()
        self.assertIn("wraithd", status)
        self.assertIn("6606", status)

    def test_redhat_text_fixtures_present(self):
        world.build_world(self.root)
        with open(os.path.join(self.root, "var/log/systemctl_status.txt")) as handle:
            self.assertIn("Active: failed", handle.read())
        with open(os.path.join(self.root, "var/log/avc_denial.txt")) as handle:
            self.assertIn("avc:", handle.read())


if __name__ == "__main__":
    unittest.main()
