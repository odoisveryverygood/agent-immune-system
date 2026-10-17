#!/bin/sh
# Send only lane-owned source to Docker, never the repository or host secrets.
set -eu
if [ "$#" -ne 1 ]; then
  echo 'Usage: sh sandbox/build-image.sh DOCKER_CONTEXT' >&2
  exit 2
fi
task_context=$(mktemp -d)
trap 'rm -rf "$task_context"' EXIT HUP INT TERM
mkdir -p "$task_context/backend/target" "$task_context/sandbox"
cp backend/target/*.py "$task_context/backend/target/"
cp sandbox/Dockerfile sandbox/worker.py sandbox/probe.py "$task_context/sandbox/"
docker --context "$1" build -f "$task_context/sandbox/Dockerfile" -t agent-immune-target:p2 "$task_context"
