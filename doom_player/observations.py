"""Compact textual sensor data derived from ViZDoom's structured labels."""

from typing import Any, Dict, Iterable, List


def visible_enemy_labels(labels: Iterable[Any], screen_width: int) -> List[Dict[str, Any]]:
    """Summarize visible monster label boxes without interpreting pixels."""
    if screen_width <= 0:
        return []
    enemies = []
    for label in labels or ():
        category = getattr(label, "object_category", "")
        if str(category).casefold() != "monster":
            continue
        x = float(getattr(label, "x", 0))
        width = max(0.0, float(getattr(label, "width", 0)))
        center_x = x + width / 2.0
        normalized_x = center_x / float(screen_width)
        if normalized_x < 0.44:
            direction = "left"
        elif normalized_x > 0.56:
            direction = "right"
        else:
            direction = "center"
        enemies.append({
            "name": str(getattr(label, "object_name", "monster")),
            "direction": direction,
            "screen_x": round(normalized_x * 2.0 - 1.0, 2),
            "box_width": round(width / float(screen_width), 2),
        })
    # Larger screen boxes usually belong to nearer visible targets.
    enemies.sort(key=lambda enemy: enemy["box_width"], reverse=True)
    return enemies[:8]
