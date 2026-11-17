# Prompts

One file per agent that asks the model for prose: `researcher.md`, `red_team.md`, `strategist.md`, `copywriter.md`, `builder.md`.

The other agents (`scorer`, `qa`, `pricer`, `policy_writer`, `analyst`, `support`) are plain code with no prompt, because they compute numbers or fill fixed templates. Every model output is cleaned by `guardrails.clean` before it is saved.
