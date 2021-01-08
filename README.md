Extract stock price and calculate stop quote price

# Install
1) copy <b>stock_orders.sh</b> and <b>main.py</b> to your folder

2) run in your folder:<br>
  chmod 755 stocks_orders.sh
# Usage
usage: main.py [-h] -c COST FILE -o ORDER FILE [-csv {yes,no}] [-v {on,off}]

<u>arguments:</u>

    -h, --help            show help message and exit</p>

    -c COST FILE [COST FILE ...], --cost_file COST FILE [COST FILE ...]
                        file name/s with unit cost

    -o ORDER FILE [ORDER FILE ...], --order_file ORDER FILE [ORDER FILE ...]
                        file name/s with order status

    -csv {yes,no}         send output to csv file <date,time>.summary.csv

    -v {on,off}, --verbose {on,off}
                        verbose
