# Independent bridge-building experiments

- Read the rules in `bridge/workspace` and the opening message in
  `bridge/prompt.md`. Use `bridge/workspace` as the contestant working directory.
- Treat the copied engine, build script, simulator, rules, levels and viewer
  as read-only. Report environment problems instead of changing the physics
  or relaxing validation.
- Do not fetch or inspect upstream solutions, contestant designs, recorded
  replays, rankings or reference answers. Do not query external websites,
  repositories or search tools for solutions. Do not use subagents.
- Put final designs in `bridge/workspace/submission`. Auxiliary scripts may
  be created inside `bridge/workspace`. Preserve simulator archives locally;
  they are ignored by Git.
- Run the real simulator on every public scenario before claiming a level
  passes. Keep a best-known passing design instead of overwriting it with an
  unverified candidate.
- Do not submit to the public leaderboard or fetch adversarial designs
  unless the user explicitly authorizes that separate, post-submission step.
- Do not commit the compiled engine, Python caches or automatic archives.
  Final design JSON, useful optimization scripts and requested notes are
  deliverables and should be retained.
- Honor the requested time budget. Do not claim a strict 90-minute experiment
  unless an external deadline and submission snapshot were actually enforced.
