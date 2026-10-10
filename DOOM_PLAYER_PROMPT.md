# Build a ViZDoom Player Using the LAYA Decision Model

You are an autonomous software engineer working in this repository. Build a usable Doom player that observes ViZDoom and chooses actions using the LAYA decision model, running locally on this machine.

## Goals

- Run a ViZDoom game episode and let the local model control the player.
- Capture game state as an image and provide it, with concise relevant state information, to the local model.
- Convert model decisions into valid ViZDoom button actions, including an action duration measured in game tics.
- Show the game while it runs and report useful status such as episode reward, health, ammo, kills, selected action, and errors.
- Make setup and operation straightforward, with a README and sensible defaults.

## Start by inspecting the environment

Before choosing an implementation, inspect this repository and the local model setup. Identify how the LAYA decision model is represented, what inputs it expects, what decision/action format it returns, and how it is run locally. Find these details in available project documentation, model files, examples, configuration, or installed tooling. Also check the installed ViZDoom version and available scenario files. Do not confuse LAYA (the decision model) with the inference runtime used to run it, and do not invent APIs, imports, endpoints, or method names. If the LAYA model or its local runner cannot be identified, implement a clean adapter boundary and explain precisely what is missing; do not silently substitute a remote model or a different decision model.

Use the existing environment and conventions where possible. Keep dependencies minimal. If there is no project structure yet, create a small, clear Python application with a dependency manifest.

## Player behavior

- Use ViZDoom's supported Python API and bundled scenarios where available.
- Expose a small set of discrete actions appropriate to the selected scenario, such as turn left/right, move forward/back, strafe, attack, and combinations. Only offer buttons supported by the active game configuration.
- Give the LAYA decision model the current observation and request one structured game decision at a time, using the model's actual supported input/output format. Map its decisions to ViZDoom actions and durations; validate every response and fall back to a safe brief action if parsing fails.
- Include the current screenshot and a compact textual state summary in each decision. Bound image size, prompt length, and action duration to keep inference responsive and prevent a single malformed response from stalling the episode.
- Avoid sending a new inference request for every tic. Execute the chosen action for its validated duration, then observe again.
- Provide configurable model identifier, inference settings, decision interval, scenario, and episode length where supported by LAYA and ViZDoom.
- Handle model/runtime errors, game termination, and user interruption gracefully. Never conceal inference failures or claim the model is controlling the game when it is not.

## User experience

Provide a simple command-line entry point. Include options for choosing a scenario, selecting a model when supported, and running a bounded episode. Render the ViZDoom window by default when a display is available; support a headless mode for environments without one. Print concise progress and a final episode summary. Keep configuration explicit and avoid requiring credentials or network access.

## Quality and safety constraints

- Do not delete or overwrite existing user files. If a necessary change would delete anything, stop and ask first. Add or edit files as needed without asking for permission.
- Do not download model weights or access remote inference services unless the user explicitly requests it. Use the local LAYA installation/model configuration.
- Keep secrets out of source control and logs.
- Separate the LAYA inference adapter, action validation, and ViZDoom episode loop enough that each can be understood and exercised independently.
- Add focused tests for action parsing/validation and other logic that can run without a Doom display or loaded model. Do not make tests depend on network access.

## Completion

Implement the working application, not just a design or plan. Run the checks that are practical in the available environment. If a real episode cannot run because a display, ViZDoom installation, LAYA runtime, or local model is unavailable, report the exact blocker and the command the user can run after resolving it. Finish with the files changed, setup/run commands, and any limitations.
