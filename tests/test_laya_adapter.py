import unittest

from doom_player.laya_adapter import LayaDecisionAdapter


class FakeLaya:
    def __init__(self, action="strafe_left_attack"):
        self.state = None
        self.questions = None
        self.action = action

    def predict(self, state, questions):
        self.state = state
        self.questions = questions
        return {"answers": {
            "action": {"choice": self.action},
            "duration": {"choice": "tics_8"},
        }}


class LayaAdapterTests(unittest.TestCase):
    def test_uses_documented_typed_choices_and_text_state_only(self):
        model = FakeLaya()
        adapter = LayaDecisionAdapter(model)
        observation = {
            "state": {"episode_tic": 18, "health": 87, "ammo": 12, "kills": 1},
            "available_buttons": ["MOVE_LEFT", "MOVE_RIGHT", "ATTACK"],
            "response_schema": {"duration_tics": {"maximum": 12}},
            "image": {"encoding": "base64", "data": "not sent to text model"},
        }
        decision = adapter.decide(observation)

        self.assertEqual(decision, {"action": "strafe_left_attack", "duration_tics": 8})
        self.assertEqual(set(model.questions), {"action", "duration"})
        self.assertNotIn("image", model.state)
        self.assertIn("strafe_left_attack", model.questions["action"]["criteria"])
        self.assertNotIn("wait", model.questions["action"]["criteria"])
        self.assertNotIn("attack", model.questions["action"]["criteria"])
        self.assertNotIn("turn_right", model.questions["action"]["criteria"])
        self.assertEqual(model.questions["duration"]["criteria"].keys(), {"tics_4", "tics_8", "tics_12"})

    def test_visible_enemy_on_right_limits_direction_to_right(self):
        model = FakeLaya(action="strafe_right_attack")
        adapter = LayaDecisionAdapter(model)
        observation = {
            "state": {"episode_tic": 40, "health": 87, "ammo": 12, "kills": 1,
                      "visible_enemies": [{"name": "Cacodemon", "direction": "right", "screen_x": 0.42}]},
            "available_buttons": ["MOVE_LEFT", "MOVE_RIGHT", "ATTACK"],
            "response_schema": {"duration_tics": {"maximum": 12}},
        }
        decision = adapter.decide(observation)

        self.assertEqual(decision["action"], "strafe_right_attack")
        offered = model.questions["action"]["criteria"]
        self.assertIn("strafe_right_attack", offered)
        self.assertNotIn("strafe_left_attack", offered)


if __name__ == "__main__":
    unittest.main()
