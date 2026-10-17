#!/bin/sh
set -eu
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
printf '%s
' 'Push guard enabled. Use a feature branch and open a PR. Never push main.'
