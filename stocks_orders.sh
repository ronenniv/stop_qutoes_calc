#!/usr/bin/env bash

if [ $# -eq 0 ]
then
  echo "No arguments. Searching for existing csv files in ~/Downloads."
  cost_file=`ls -t ~/Downloads/ExportData*.csv | tail -1`
  if [ "$cost_file" = "" ]
  then
    echo "Error: No file found with pattern ExportData*.csv."
    exit 1
  fi
  order_file=`ls -t ~/Downloads/ExportData*.csv | head -1`
  if [ "$cost_file" = "$order_file" ]
  then
    echo "Error: only one csv file found. Missing files."
    exit 1
  fi
  echo "execute -c $cost_file -o $order_file"
  python3 main.py -c $cost_file -o $order_file -csv yes
else
  python3 main.py $@
fi

result=$?

if [ $result -eq 0 ]
then
  echo "Completed successfully!!!"
  exit 0
else
  echo "Completed with errors!!!"
  exit 1
fi