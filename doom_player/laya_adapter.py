"""Adapter for Convai's text-only LAYA typed-decision model."""

import os
from typing import Any, Dict

from .actions import action_catalog


ACTION_GUIDANCE = {
    "wait": "Stay still briefly; use when caution or observation is preferable.",
    "forward": "Move into the level without firing.",
    "backward": "Retreat without firing.",
    "turn_left": "Rotate left to search or reorient.",
    "turn_right": "Rotate right to search or reorient.",
    "strafe_left": "Move sideways left to evade or reposition.",
    "strafe_right": "Move sideways right to evade or reposition.",
    "strafe_left_attack": "Strafe left while firing to reposition and engage.",
    "strafe_right_attack": "Strafe right while firing to reposition and engage.",
    "attack": "Fire while standing still; useful when a target is already aligned.",
    "forward_attack": "Advance while firing; use to explore and engage.",
    "turn_left_attack": "Turn left while firing to search and engage.",
    "turn_right_attack": "Turn right while firing to search and engage.",
    "backward_attack": "Retreat while firing to create distance from danger.",
}


class LayaDecisionAdapter:
    """Use LAYA's typed choice questions over numeric/text state, never image bytes."""

    def __init__(self, model: Any):
        self.model = model

    def decide(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        actions = action_catalog(observation["available_buttons"])
        visible_enemies = observation["state"].get("visible_enemies", [])
        movement_buttons = {
            "MOVE_FORWARD", "MOVE_BACKWARD", "MOVE_LEFT", "MOVE_RIGHT",
            "TURN_LEFT", "TURN_RIGHT",
        }
        if set(observation["available_buttons"]) & movement_buttons:
            # Never offer a no-op or stationary attack while locomotion is
            # available: LAYA otherwise repeatedly picked "wait" in Doom.
            actions = {
                name: buttons for name, buttons in actions.items()
                if set(buttons) & movement_buttons
            }
        target_direction = visible_enemies[0]["direction"] if visible_enemies else "center"
        if target_direction in ("left", "right"):
            preferred_button = "TURN_{}".format(target_direction.upper())
            if preferred_button not in observation["available_buttons"]:
                preferred_button = "MOVE_{}".format(target_direction.upper())
            toward_target = {
                name: buttons for name, buttons in actions.items()
                if preferred_button in buttons
            }
            if toward_target:
                actions = toward_target
        if not actions:
            raise ValueError("active scenario exposes no supported player actions")

        action_criteria = {
            name: ACTION_GUIDANCE.get(name, "Use this supported control combination.")
            for name in actions
        }
        if target_direction in ("left", "right"):
            action_criteria = {
                name: "Move {} toward the visible monster on screen {}; this brings the target toward the crosshair.{}".format(
                    target_direction, target_direction,
                    " Fire while moving." if "attack" in name else "")
                for name in actions
            }
        max_tics = int(observation["response_schema"]["duration_tics"]["maximum"])
        duration_values = sorted(set(value for value in (4, 8, 12) if value <= max_tics))
        if not duration_values:
            duration_values = [max_tics]
        duration_criteria = {
            "tics_{}".format(value): "Execute for exactly {} game tics; shorter choices allow earlier reassessment.".format(value)
            for value in duration_values
        }

        # LAYA consumes text/JSON state and typed questions. Its documented API
        # has no image input, so send only compact state and omit screenshot data.
        state = {
            "game": "ViZDoom",
            "observation": observation["state"],
            "controls": action_criteria,
            "note": "This decision model receives game statistics, not the rendered screen."
        }
        questions = {
            "action": {
                "type": "choice",
                "instructions": "Choose the best next Doom control combination from the supplied game statistics and ViZDoom's visible-monster labels. If a visible monster is on one side, move toward it to bring it toward the crosshair. The model does not receive pixels. When movement controls are available, every option moves or turns the player; do not stay idle.",
                "criteria": action_criteria,
            },
            "duration": {
                "type": "choice",
                "instructions": "Choose how long to execute the selected control combination before the next observation.",
                "criteria": duration_criteria,
            },
        }
        result = self.model.predict(state, questions)
        answers = result["answers"]
        action_name = answers["action"]["choice"]
        duration_key = answers["duration"]["choice"]
        if action_name not in actions:
            raise ValueError("LAYA returned an action absent from the current scenario")
        if duration_key not in duration_criteria:
            raise ValueError("LAYA returned an invalid duration choice")
        return {"action": action_name, "duration_tics": int(duration_key.split("_", 1)[1])}


def create_adapter(model_id: str = "convaiinnovations/laya") -> LayaDecisionAdapter:
    """Load the local LAYA SDK checkpoint, downloading weights on first use."""
    checkpoint = model_id or "convaiinnovations/laya"
    # The Xet downloader stalled on this host during checkpoint retrieval;
    # allow callers to override this setting while keeping first-run loading reliable.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "300")
    try:
        import laya
    except ImportError as exc:
        raise RuntimeError("install LAYA with `python -m pip install 'laya>=0.3.20'`") from exc
    model = laya.load(checkpoint)
    return LayaDecisionAdapter(model)
