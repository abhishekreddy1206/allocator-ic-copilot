#!/bin/sh
set -eu
curl --fail --silent --show-error -X POST http://localhost:8000/api/demo
