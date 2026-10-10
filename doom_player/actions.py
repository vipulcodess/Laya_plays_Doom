"""Validation and construction of actions against the active ViZDoom buttons."""

from dataclasses import dataclass
import json
from typing import Any, Dict, Iterable, List, Mapping, Sequence


@dataclass(frozen=True)
class Decision:
    buttons: List[str]
    duration_tics: int
    label: str


class DecisionError(ValueError):
    pass


def action_catalog(available_buttons: Iterable[str]) -> Dict[str, List[str]]:
    """Return useful named actions, including only buttons supported by this config."""
    available = set(available_buttons)
    candidates = {
        "wait": [],
        "forward": ["MOVE_FORWARD"],
        "backward": ["MOVE_BACKWARD"],
        "turn_left": ["TURN_LEFT"],
        "turn_right": ["TURN_RIGHT"],
        "strafe_left": ["MOVE_LEFT"],
        "strafe_right": ["MOVE_RIGHT"],
        "strafe_left_attack": ["MOVE_LEFT", "ATTACK"],
        "strafe_right_attack": ["MOVE_RIGHT", "ATTACK"],
        "attack": ["ATTACK"],
        "forward_attack": ["MOVE_FORWARD", "ATTACK"],
        "turn_left_attack": ["TURN_LEFT", "ATTACK"],
        "turn_right_attack": ["TURN_RIGHT", "ATTACK"],
        "backward_attack": ["MOVE_BACKWARD", "ATTACK"],
    }
    return {name: buttons for name, buttons in candidates.items()
            if all(button in available for button in buttons)}


def parse_decision(raw: Any, available_buttons: Iterable[str], max_tics: int,
                   fallback_tics: int = 4) -> Decision:
    """Parse JSON or a mapping; reject unsupported buttons and unsafe durations."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise DecisionError("response is not valid JSON") from exc
    if not isinstance(raw, Mapping):
        raise DecisionError("decision must be a JSON object")
    known = set(available_buttons)
    if "action" in raw:
        catalog = action_catalog(known)
        action_name = raw["action"]
        if not isinstance(action_name, str) or action_name not in catalog:
            raise DecisionError("action must name an action in the supplied catalog")
        buttons = catalog[action_name]
        label = action_name
    else:
        values = raw.get("buttons")
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise DecisionError("buttons must be a list of button names")
        if len(set(values)) != len(values):
            raise DecisionError("buttons must not contain duplicates")
        unsupported = set(values) - known
        if unsupported:
            raise DecisionError("unsupported button(s): " + ", ".join(sorted(unsupported)))
        buttons = values
        label = "+".join(values) if values else "wait"
    duration = raw.get("duration_tics")
    if isinstance(duration, bool) or not isinstance(duration, int):
        raise DecisionError("duration_tics must be an integer")
    if duration < 1 or duration > max_tics:
        raise DecisionError("duration_tics must be between 1 and {}".format(max_tics))
    return Decision(buttons=list(buttons), duration_tics=duration, label=label)


def safe_fallback(available_buttons: Sequence[str], max_tics: int,
                  fallback_tics: int = 4) -> Decision:
    """Brief no-button action that cannot issue an invalid button for this config."""
    duration = max(1, min(max_tics, fallback_tics))
    return Decision(buttons=[], duration_tics=duration, label="safe_wait")
