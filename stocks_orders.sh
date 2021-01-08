#!/usr/bin/env bash
clear

echo "Running main.py"

if [ $# -eq 0 ]
then
  cost_file=`ls -t ~/Downloads/ExportData*.csv | tail -1`
  order_file=`ls -t ~/Downloads/ExportData*.csv | head -1`
  echo "$cost_file"
  python3 main.py -c $cost_file -o $order_file -csv yes
else
  python3 main.py $@
fi

result=$?

if [ $result -eq 0 ]
then
  echo "Completed successfully"
else
  echo "Completed with errors"
fi