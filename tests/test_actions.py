import unittest

from doom_player.actions import DecisionError, action_catalog, parse_decision, safe_fallback


BUTTONS = ["MOVE_FORWARD", "TURN_LEFT", "ATTACK"]


class ActionTests(unittest.TestCase):
    def test_catalog_excludes_unsupported_controls(self):
        catalog = action_catalog(BUTTONS)
        self.assertEqual(catalog["forward_attack"], ["MOVE_FORWARD", "ATTACK"])
        self.assertNotIn("turn_right", catalog)

    def test_parses_named_action_and_duration(self):
        decision = parse_decision('{"action":"forward_attack","duration_tics":8}', BUTTONS, 12)
        self.assertEqual(decision.buttons, ["MOVE_FORWARD", "ATTACK"])
        self.assertEqual(decision.duration_tics, 8)

    def test_rejects_unknown_buttons_and_unbounded_duration(self):
        for payload in (
            {"buttons": ["USE"], "duration_tics": 3},
            {"action": "forward", "duration_tics": 13},
            {"action": "forward", "duration_tics": True},
        ):
            with self.subTest(payload=payload), self.assertRaises(DecisionError):
                parse_decision(payload, BUTTONS, 12)

    def test_fallback_is_safe_and_bounded(self):
        decision = safe_fallback(BUTTONS, 3, 10)
        self.assertEqual(decision.buttons, [])
        self.assertEqual(decision.duration_tics, 3)


if __name__ == "__main__":
    unittest.main()
