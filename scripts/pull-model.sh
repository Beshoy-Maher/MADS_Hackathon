#!/bin/sh
# Download the local model into Ollama (runs once inside the model-pull container).
# Tries LLM_MODEL first, then smaller/older Qwen3 tags.
for m in "$LLM_MODEL" qwen3:4b-instruct qwen3:4b qwen3:1.7b; do
  [ -z "$m" ] && continue
  echo "Pulling $m ..."
  if ollama pull "$m"; then
    echo "Model $m is ready."
    exit 0
  fi
done
echo "Could not download a model. The app still runs with its labelled deterministic fallback."
exit 1
