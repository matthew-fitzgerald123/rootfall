"""Unit tests for the recall answer matcher.

The matcher must accept genuinely-equivalent answers (flag order, flag bundling,
whitespace) without becoming loose enough to pass incorrect ones (a missing
flag, a wrong signal number, a different flag case).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from rootfall import battle


class EquivalenceAccepted(unittest.TestCase):
    def test_flag_order_independent(self):
        self.assertTrue(battle.matches("ss -tlpnu", ["ss -tulpn"]))

    def test_bundled_equals_separated(self):
        self.assertTrue(battle.matches("ss -t -u -l -p -n", ["ss -tulpn"]))

    def test_separated_and_reordered(self):
        self.assertTrue(battle.matches("ss -n -u -t -l -p", ["ss -tulpn"]))

    def test_whitespace_tolerated(self):
        self.assertTrue(battle.matches("ss     -tulpn", ["ss -tulpn"]))
        self.assertTrue(battle.matches("   grep -n ERROR realm.log  ", ["grep -n ERROR realm.log"]))

    def test_multiple_accepted_answers(self):
        accepted = ["find . -name config.yaml", "find -name config.yaml"]
        self.assertTrue(battle.matches("find -name config.yaml", accepted))
        self.assertTrue(battle.matches("find . -name config.yaml", accepted))

    def test_value_flag_order_for_tcpdump(self):
        # Both orders are listed in the campaign; the matcher should agree.
        self.assertTrue(battle.matches("tcpdump -i eth0 -nn", ["tcpdump -nn -i eth0"]))


class WrongAnswersRejected(unittest.TestCase):
    def test_missing_flag_fails(self):
        # -tuln is missing the p (process) flag, so it is not -tulpn.
        self.assertFalse(battle.matches("ss -tuln", ["ss -tulpn"]))

    def test_wrong_signal_fails(self):
        self.assertFalse(battle.matches("kill -15 6606", ["kill -9 6606"]))
        self.assertFalse(battle.matches("kill -9 6606", ["kill -15 6606"]))

    def test_flag_case_is_significant(self):
        # ls -r is reverse order, not recursive; it must not pass for -R.
        self.assertFalse(battle.matches("ls -r", ["ls -R"]))
        self.assertTrue(battle.matches("ls -R", ["ls -R"]))

    def test_different_argument_fails(self):
        self.assertFalse(battle.matches("tcpdump -i wlan0", ["tcpdump -i eth0"]))

    def test_extra_flag_fails(self):
        self.assertFalse(battle.matches("ss -tulpne", ["ss -tulpn"]))

    def test_none_answer_fails(self):
        self.assertFalse(battle.matches(None, ["pwd"]))


class CanonicalFormProperties(unittest.TestCase):
    def test_long_flags_not_treated_as_bundles(self):
        # --recursive must not be exploded into r,e,c,u,... letters.
        self.assertFalse(battle.matches("grep --recursive x", ["grep -r x"]))

    def test_bundled_short_flags_match_canonical(self):
        self.assertEqual(battle._canonical("ss -tulpn"), battle._canonical("ss -t -u -l -p -n"))


if __name__ == "__main__":
    unittest.main()
