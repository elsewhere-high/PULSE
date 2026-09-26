#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
COVERAGE_DIR=${PULSE_COVERAGE_DIR:-"$PROJECT_ROOT/results/chengdu_census2020/coverage_v1"}
LLM_DIR=${PULSE_LLM_DIR:-"$PROJECT_ROOT/results/chengdu_census2020/llm_v1"}
: "${CONDA_PREFIX:?Activate a Conda environment before running this script}"
: "${PULSE_LLAMA_BIN:?Set PULSE_LLAMA_BIN to the llama-server executable}"
: "${PULSE_LLM_MODEL:?Set PULSE_LLM_MODEL to a local GGUF model file}"
LLAMA_BIN=$PULSE_LLAMA_BIN
LLAMA_DIR=$(dirname "$LLAMA_BIN")
MODEL=$PULSE_LLM_MODEL
LLM_RUNNER="$PROJECT_ROOT/scripts/run_chengdu_census2020_llm.py"
export PULSE_COVERAGE_DIR="$COVERAGE_DIR" PULSE_LLM_DIR="$LLM_DIR"

# The portable llama.cpp bundle ships its shared objects beside the binary.
export LD_LIBRARY_PATH="$LLAMA_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

mkdir -p "$LLM_DIR"

# The GPU coverage matrix owns the device first.  Its final table is written
# only after all 12 summaries have passed the hard gates.
while [ ! -s "$COVERAGE_DIR/matrix_results.csv" ]; do
  sleep 30
done

"$LLAMA_BIN" \
  -m "$MODEL" \
  -ngl 99 \
  -c 32768 \
  -np 32 \
  --cont-batching \
  --host 127.0.0.1 \
  --port 8080 \
  > "$LLM_DIR/llama-server.log" 2>&1 &
LLAMA_PID=$!

cleanup() {
  kill "$LLAMA_PID" 2>/dev/null || true
  wait "$LLAMA_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$LLAMA_PID" 2>/dev/null; then
    echo "llama-server exited before becoming healthy" >&2
    exit 1
  fi
  sleep 5
done
curl -fsS http://127.0.0.1:8080/health >/dev/null

"$CONDA_PREFIX/bin/python" "$LLM_RUNNER"
