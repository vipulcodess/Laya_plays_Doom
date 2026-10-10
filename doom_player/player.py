"""Bounded ViZDoom episode runner."""

import argparse
import os
import queue
import sys
import threading
from typing import Any, Dict, List, Optional

from .actions import action_catalog, parse_decision, safe_fallback
from .adapter import load_provider
from .observations import visible_enemy_labels


def _game_value(game: Any, enum: Any, name: str) -> Optional[float]:
    variable = getattr(enum, name, None)
    if variable is None:
        return None
    try:
        value = game.get_game_variable(variable)
        return float(value)
    except Exception:
        return None


def _scenario_path(vizdoom: Any, scenario: str) -> str:
    if os.path.isfile(scenario):
        return os.path.abspath(scenario)
    return os.path.join(vizdoom.scenarios_path, scenario)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Play a ViZDoom episode using local LAYA typed decisions.")
    parser.add_argument("--scenario", default="defend_the_line.cfg", help="Scenario config path or bundled config filename (default has multiple enemies)")
    parser.add_argument("--adapter", default="doom_player.laya_adapter:create_adapter", help="Adapter factory (defaults to the built-in LAYA adapter)")
    parser.add_argument("--model-id", default="convaiinnovations/laya", help="Local LAYA checkpoint ID; weights download on first use")
    parser.add_argument("--headless", action="store_true", help="Do not show the ViZDoom window")
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--max-tics", type=int, default=2100, help="Maximum tics per episode")
    parser.add_argument("--max-action-tics", type=int, default=12, help="Clamp decision durations to this many tics")
    parser.add_argument("--fallback-tics", type=int, default=4, help="Safe no-button duration after adapter errors")
    parser.add_argument("--decision-timeout", type=float, default=60.0, help="Maximum seconds to wait for one adapter decision")
    parser.add_argument("--list-scenarios", action="store_true", help="List bundled scenario config files")
    return parser


def _observation(state: Any, game: Any, vizdoom: Any, buttons: List[str],
                 max_action_tics: int) -> Dict[str, Any]:
    enum = vizdoom.GameVariable
    summary = {
        "episode_tic": int(state.tic),
        "health": _game_value(game, enum, "HEALTH"),
        "ammo": _game_value(game, enum, "AMMO2"),
        "kills": _game_value(game, enum, "KILLCOUNT"),
        "visible_enemies": visible_enemy_labels(state.labels, game.get_screen_width()),
    }
    return {
        "state": summary,
        "available_buttons": buttons,
        "actions": action_catalog(buttons),
        "response_schema": {
            "type": "object",
            "required": ["action", "duration_tics"],
            "action": {"enum": sorted(action_catalog(buttons))},
            "duration_tics": {"type": "integer", "minimum": 1, "maximum": max_action_tics},
        },
    }


def _decide_with_timeout(provider: Any, observation: Dict[str, Any], timeout: float) -> Any:
    """Bound a hung adapter call; the daemon worker cannot keep the CLI alive."""
    result = queue.Queue(maxsize=1)

    def invoke() -> None:
        try:
            result.put((True, provider.decide(observation)))
        except BaseException as exc:
            result.put((False, exc))

    worker = threading.Thread(target=invoke, name="decision-adapter", daemon=True)
    worker.start()
    try:
        ok, value = result.get(timeout=timeout)
    except queue.Empty as exc:
        raise TimeoutError("decision adapter exceeded {:.1f}s".format(timeout)) from exc
    if not ok:
        raise value
    return value


def run(args: argparse.Namespace) -> int:
    try:
        import vizdoom as vzd
    except ImportError:
        print("ERROR: ViZDoom is not installed. Install dependencies with: python -m pip install -e .", file=sys.stderr)
        return 2
    if args.list_scenarios:
        print("\n".join(sorted(n for n in os.listdir(vzd.scenarios_path) if n.endswith(".cfg"))))
        return 0
    if args.episodes < 1 or args.max_tics < 1 or args.max_action_tics < 1 or args.decision_timeout <= 0:
        print("ERROR: episode count and tic limits must be positive", file=sys.stderr)
        return 2
    try:
        provider = load_provider(args.adapter, args.model_id)
    except Exception as exc:
        print("ERROR: could not load decision adapter: {}".format(exc), file=sys.stderr)
        return 2

    total_reward = 0.0
    adapter_timed_out = False
    try:
        for episode in range(1, args.episodes + 1):
            game = vzd.DoomGame()
            config = _scenario_path(vzd, args.scenario)
            if not os.path.isfile(config):
                raise FileNotFoundError("scenario config not found: {}".format(config))
            game.load_config(config)
            # The scenario's own timeout may be shorter than --max-tics. Apply
            # the CLI bound as the engine timeout so it exits cleanly there.
            game.set_episode_timeout(args.max_tics)
            game.set_labels_buffer_enabled(True)
            game.set_objects_info_enabled(True)
            game.set_window_visible(not args.headless and bool(os.environ.get("DISPLAY") or sys.platform == "darwin"))
            game.init()
            buttons = [button.name for button in game.get_available_buttons()]
            print("Episode {}/{} started; scenario={} buttons={} enemy_labels=on timeout={}".format(
                episode, args.episodes, os.path.basename(config), ",".join(buttons), args.max_tics))
            game.new_episode()
            reward = 0.0
            selected = "starting"
            last_enemies = "none"
            last_status = 0
            try:
                while not game.is_episode_finished():
                    state = game.get_state()
                    if state is None:
                        break
                    try:
                        observation = _observation(state, game, vzd, buttons,
                                                   args.max_action_tics)
                        enemies = observation["state"]["visible_enemies"]
                        last_enemies = ",".join(
                            "{}:{}".format(enemy["name"], enemy["direction"])
                            for enemy in enemies
                        ) or "none"
                        if adapter_timed_out:
                            raise RuntimeError("adapter disabled after a timed-out decision")
                        response = _decide_with_timeout(provider, observation, args.decision_timeout)
                        decision = parse_decision(response, buttons, args.max_action_tics, args.fallback_tics)
                    except Exception as exc:
                        print("ERROR: inference/decision failed at tic {}: {}; using safe wait".format(state.tic, exc), file=sys.stderr)
                        if isinstance(exc, TimeoutError):
                            adapter_timed_out = True
                        decision = safe_fallback(buttons, args.max_action_tics, args.fallback_tics)
                    selected = decision.label
                    action = [1 if name in decision.buttons else 0 for name in buttons]
                    remaining = args.max_tics - int(state.tic)
                    if remaining <= 0:
                        break
                    reward += float(game.make_action(action, min(decision.duration_tics, remaining)))
                    if state.tic - last_status >= 70 or game.is_episode_finished():
                        health = _game_value(game, vzd.GameVariable, "HEALTH")
                        ammo = _game_value(game, vzd.GameVariable, "AMMO2")
                        kills = _game_value(game, vzd.GameVariable, "KILLCOUNT")
                        print("tic={} reward={:.1f} health={} ammo={} kills={} enemies={} action={}".format(
                            state.tic, reward, health, ammo, kills, last_enemies, selected))
                        last_status = state.tic
                total_reward += reward
                print("Episode {}/{} finished: reward={:.1f} health={} ammo={} kills={} enemies={} last_action={}".format(
                    episode, args.episodes, reward,
                    _game_value(game, vzd.GameVariable, "HEALTH"),
                    _game_value(game, vzd.GameVariable, "AMMO2"),
                    _game_value(game, vzd.GameVariable, "KILLCOUNT"), last_enemies, selected))
            finally:
                game.close()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Completed episode reward total: {:.1f}".format(total_reward))
        return 130
    except Exception as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 1
    print("All episodes complete: total_reward={:.1f}".format(total_reward))
    return 0


def main() -> None:
    raise SystemExit(run(build_parser().parse_args()))


if __name__ == "__main__":
    main()
