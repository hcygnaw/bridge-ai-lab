# Bridge AI Lab

A clean, solution-free experiment package for episode 9 of
[meow-ai-arena](https://github.com/chen-006/meow-ai-arena).

## What is included

- `bridge/workspace/`: the original contestant package, including all seven
  levels, public scenarios, rules, simulator frontend and replay viewer.
- `bridge/engine/bridge_sim.cpp` and `bridge/build_engine.py`: the original
  physics engine source and cross-platform build script.
- `bridge/prompt.md`: the original opening message, with the contestant's
  working directory replaced by a placeholder.
- `.github/workflows/copilot-setup-steps.yml`: environment preparation for
  GitHub Copilot cloud agent.

These upstream files and `LICENSE` were copied without modification from
commit `3e8b17208f9edccf19c7280106f4d3eec35c5ee4`.
This is a new repository, not a fork or a copy of upstream Git history.
It contains no contestant designs, reference solutions, competition results,
recorded replays or solution-based scoring scripts.

## Prepare the environment

Requirements: Python 3.9+ and g++ with C++17 support. No third-party Python
packages are needed.

From the repository root:

```text
cd bridge
python build_engine.py
cd workspace
python bridge.py --help
```

The build produces a native executable named `bridge_sim.exe` on both Windows
and Linux. The filename does not imply that Wine is needed on Linux.
Compilation on another platform does not guarantee byte-for-byte identity
with the original Windows executable.

## Start a cloud experiment

Enable Copilot cloud agent for this repository, then start a task from the
repository's Agents page or assign an issue to Copilot. The setup workflow
prepares Python and compiles the engine before the agent begins.
Creating this repository does not itself enable or start Copilot.

Use the fenced opening message in `bridge/prompt.md` as the task prompt.
Replace `{选手目录}` with the absolute path to this checkout's
`bridge/workspace` directory. That is the contestant's working directory,
not the repository root.

For an independent attempt, follow `AGENTS.md`: do not retrieve upstream
answers, other contestants' work or online leaderboard entries. All seven
levels are available from the start, sharing one 90-minute contest budget.
Do not treat seven separate 90-minute tasks as a reproduction of the contest.
The copied prompt's "seven other contestants" wording is an upstream typo;
the original event had nine contestants.

The submission consists of `level1.json` through `level6.json`,
`final_bridge.json`, `saboteur.json`, and the notes requested by the original
prompt, under `bridge/workspace/submission/`. Do not upload anything to the
public leaderboard unless the user explicitly requests it.

## Evaluation boundaries

Use `bridge.py check` and `bridge.py run` for levels 1 through 6, and
`bridge.py duel` for local final-round experiments. Preserve the best passing
design while iterating, and report actual simulator output rather than
unverified claims.

Reference costs and other contestants' designs are intentionally absent.
Comparisons against the original competition must happen after the submission
has been frozen, in a separate evaluator environment.

The unmodified final-round rules and local `duel` command require the
saboteur to arrive intact by its deadline for an attack to count. The published
competition used a different scoring convention based on the standard
convoy's outcome. Choose and record the evaluation convention before a run;
do not change the simulator during the attempt.

A prompt is not a hard timer or network sandbox. For a strict 90-minute
experiment, record the start after setup, enforce the deadline externally,
and collect a snapshot of the submission at the deadline. The setup job's
timeout is only for environment preparation, not the agent's contest timer.

## License and attribution

The contestant package and engine are by the meow-ai-arena contributors and
are distributed under the original MIT license, preserved in `LICENSE`.
This repository only adds experiment packaging and cloud setup instructions.
