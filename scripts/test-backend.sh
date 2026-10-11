#!/bin/sh
# A fresh test database per invocation, independent of application containers.
set -eu
cd "$(dirname "$0")/.."
test_project="allocator-tests-$$"
cleanup() {
    docker compose -f compose.test.yaml -p "$test_project" down --volumes --remove-orphans
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
docker compose -f compose.test.yaml -p "$test_project" run --build --rm tests
