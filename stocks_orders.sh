#!/usr/bin/env bash
clear

echo "Running main.py"

python3 main.py $@

# shellcheck disable=SC2181
[ $? -eq 0 ] && echo "Completed successfully" || echo "Completed with errors"