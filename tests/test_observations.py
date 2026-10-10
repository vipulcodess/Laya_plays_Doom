import unittest
from types import SimpleNamespace

from doom_player.observations import visible_enemy_labels


class EnemyLabelTests(unittest.TestCase):
    def test_reports_visible_monster_side_and_ignores_self(self):
        labels = [
            SimpleNamespace(object_category="Monster", object_name="Cacodemon", x=220, width=40),
            SimpleNamespace(object_category="Self", object_name="DoomPlayer", x=100, width=50),
        ]
        result = visible_enemy_labels(labels, screen_width=320)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Cacodemon")
        self.assertEqual(result[0]["direction"], "right")

    def test_missing_screen_width_returns_no_labels(self):
        self.assertEqual(visible_enemy_labels([], screen_width=0), [])


if __name__ == "__main__":
    unittest.main()
