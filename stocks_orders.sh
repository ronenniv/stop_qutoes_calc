#!/usr/bin/env bash
clear

echo "Running main.py"

python3 main.py $@
result=$?

if [ $result -eq 0 ]
then
  echo "Completed successfully"
else
  echo "Completed with errors"
fi