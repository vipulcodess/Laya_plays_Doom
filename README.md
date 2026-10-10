# ViZDoom player using LAYA

This CLI runs a bounded ViZDoom episode and uses the local [Convai LAYA](https://huggingface.co/convaiinnovations/laya) checkpoint for one structured decision at a time. The built-in adapter calls the documented `laya.load()` and `agent.predict(state, questions)` SDK methods. Inference runs locally; model weights are fetched from Hugging Face the first time the checkpoint is loaded.

## Important model limitation

The linked LAYA checkpoint is a **text/JSON typed-decision model, not a vision model**. ViZDoom renders the game window; the app enables ViZDoom's structured object/label metadata and sends LAYA visible monster names and their left/center/right screen positions alongside `episode_tic`, `health`, `ammo`, `kills`, and supported actions. It still cannot interpret pixels, walls, or unlabelled visual detail. When a visible monster is to one side and the scenario has a matching control, the adapter only offers actions toward that side. The base checkpoint is not Doom-tuned and may still make poor gameplay decisions. No alternate/remote inference model is used.

## Setup

LAYA requires Python 3.10 or newer. On this machine, Python 3.9 is the system interpreter; install a supported Python and create an isolated environment (Homebrew example):

```sh
brew install python@3.12
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The first run downloads the English `convaiinnovations/laya` checkpoint (about 808 MB per its model card) into the Hugging Face cache. After that, inference uses the cached local weights. ViZDoom's bundled scenarios are installed with the Python package; list them with:

```sh
doom-player --list-scenarios
```

## Run

```sh
doom-player
```

By default, the app loads `convaiinnovations/laya`, runs `defend_the_line.cfg`, and shows the game window when a display is available. This scenario starts with several enemies visible and exposes turning plus attack controls. For headless mode or a bounded episode:

```sh
doom-player --headless --scenario defend_the_line.cfg --episodes 1 --max-tics 2100
```

Options include `--scenario basic.cfg` to return to the single-target starter level, `--model-id` for another LAYA checkpoint, `--max-action-tics` to cap duration (default 12), `--fallback-tics` for safe waits after errors, and `--decision-timeout` to bound each decision request. `--max-tics 1365` is about 39 seconds of game time at 35 tics per second; `2100` is about 60 seconds. These are upper bounds: dying or a scenario ending can finish an episode earlier. The app overrides a scenario's built-in timeout with `--max-tics`. The adapter asks LAYA to select from scenario-supported action combinations and a short duration choice in one typed-decision call. When a visible monster is on the left or right, it filters choices toward that direction; when locomotion controls are present, it excludes idle and stationary-only actions. Malformed responses and inference failures are printed and replaced with a brief no-button wait; a timed-out adapter is disabled for the rest of the run.

An alternate `--adapter module:factory` can be supplied for development, but the default is the built-in LAYA SDK adapter. Its factory receives `model_id` and must return an object with `decide(observation)`.

## Checks and current machine status

Run the logic tests without a game display or loaded model:

```sh
python -m unittest discover -s tests -v
```

At initial inspection, ViZDoom and LAYA were not installed and this machine had only Python 3.9.6. The install commands above add the required Python packages; the first normal `doom-player` run downloads LAYA's weights. The application's unit tests do not download weights or require ViZDoom.
