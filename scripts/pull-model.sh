#!/bin/sh
# Download the local models into Ollama (runs once inside the model-pull container).
# Order: the small fast model first (the dashboard works as soon as it is there), then the judge,
# the writer and the critic. A model that cannot be pulled is skipped: its steps use the small model.
ok=""
for m in "$LLM_FAST_MODEL" qwen3:4b-instruct qwen3:4b qwen3:1.7b; do
  [ -z "$m" ] && continue
  echo "Pulling $m ..."
  if ollama pull "$m"; then echo "Model $m is ready."; ok="$m"; break; fi
done
for m in "$LLM_JUDGE_MODEL" "$LLM_MODEL" "$LLM_CRITIC_MODEL"; do
  [ -z "$m" ] && continue
  [ "$m" = "$ok" ] && continue
  echo "Pulling $m ..."
  if ollama pull "$m"; then echo "Model $m is ready."; ok="$ok $m"; else echo "Could not pull $m; its steps use the small model."; fi
done
if [ -z "$ok" ]; then
  echo "Could not download a model. The app still runs with its labelled deterministic fallback."
  exit 1
fi
exit 0
