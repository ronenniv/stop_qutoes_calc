import argparse
import os
import re
import sys
from datetime import datetime

# args constants
COST_FILE = 'cost_file'
ORDER_FILE = 'order_file'
OUTPUT_FLAG = 'output'
VERBOSE_FLAG = 'verbose'
OUTPUT_ARG_YES = 'yes'
OUTPUT_ARG_NO = 'no'
VERBOSE_ARG_ON = 'on'
VERBOSE_ARG_OFF = 'off'

# stock details
STOCK_GAIN = 'GAIN%'
STOCK_LAST_PRICE = 'LAST_PRICE$'
STOCK_95STOP_QUOTE = '95%STOP_QUOTE$'
STOCK_EXIST_STOP = 'EXIST_STOP$'
STOCK_NEW_STOP = 'NEW_STOP$'
PERCENT_FOR_STOP_QUOTE = 0.95

verbose_flag_indicator = VERBOSE_ARG_OFF  # default is verbose off


def verbose_print(text: str):
    """
    print verbose text if verbose_flag_indicator is on

    :param text: text to print
    """
    if verbose_flag_indicator == VERBOSE_ARG_ON:
        print(text)


def get_input_file_argparse() -> dict:
    """
    get input file/s from command line arguments

    :return: the input file name/s, verbose flag
    """
    parser = argparse.ArgumentParser(description='Extract stock price and calculate stop quote price')
    parser.add_argument('-c', '--cost_file', metavar='COST FILE', required=True, help='file name/s with unit cost',
                        nargs='+')
    parser.add_argument('-o', '--order_file', metavar='ORDER FILE', required=True, help='file name/s with order status',
                        nargs='+')
    parser.add_argument('-csv', choices=[OUTPUT_ARG_YES, OUTPUT_ARG_NO], nargs=1,
                        required=False, default='no', help='send output to csv file <date,time>.summary.csv')
    parser.add_argument('-v', '--verbose', choices=[VERBOSE_ARG_ON, VERBOSE_ARG_OFF], nargs=1,
                        required=False, default=VERBOSE_ARG_OFF, help='verbose')
    args = parser.parse_args()
    files_dict = dict()
    files_dict[COST_FILE] = args.cost_file
    files_dict[ORDER_FILE] = args.order_file
    files_dict[OUTPUT_FLAG] = args.csv
    # when default, argparse return params as str, and if it get arg in command line, it return it as list
    if isinstance(args.verbose, list):
        files_dict[VERBOSE_FLAG] = args.verbose[0]
    else:
        files_dict[VERBOSE_FLAG] = args.verbose
    global verbose_flag_indicator
    verbose_flag_indicator = files_dict[VERBOSE_FLAG]
    verbose_print('Verbose is ON')

    if isinstance(args.csv, list):
        files_dict[OUTPUT_FLAG] = args.csv[0]
    else:
        files_dict[OUTPUT_FLAG] = args.csv

    verbose_print(f'Arguments to be used:\n{files_dict}')
    return files_dict


def verify_input_file(input_file: list):
    """
    check if the input file exist and its size larger than 0

    :param input_file: list
    """
    for file in input_file:
        if not os.path.isfile(file):
            print(f'Error: file {file} not found.')
            sys.exit(1)
        else:
            if os.path.getsize(file) == 0:
                print(f'Error: file {file} size is zero.')
                sys.exit(1)


def extract_stocks(input_file: str) -> dict:
    """
    extract stock symbol and unit cost from holding csv file

    :param input_file: str
    :return: dict with symbol as key, and unit cost as value
    """
    verbose_print(f'Processing {input_file=} for holdings.')

    with open(input_file, 'r') as f:
        # group(1) = Symbol
        # group(2) = Unrealized gain
        # group(3) = Price
        r_unit_cost = re.compile(
            '"([A-Z]{1,4})\s?!?".."[+-]?\$\d+\.?\d\d [+-]?\d+\.?\d\d%".."[+-]?\$[0-9,]+\.?\d* ([+-]?\d+\.?\d*)%".."[A-Z].*".."\d*.?\d*".."\$[0-9,]+\.?\d*".."\$([0-9,]+\.?\d*)"')
        r_stock = re.compile('"([A-Z]{1,4})\s?!?"')
        # "AAL !" ,"$0.00 0.00%" ,"+$0.0 +0.0%" ,"AMERICAN AIRLS GROUP INC" ,"0" ,"+$0.0" ,"$15.77" ,"$0.00" ,"$0.00"
        # "QQQ !", "$0.00 0.00%", "+$2,399.39 +7.33%", "INVESCO QQQ TR    SER 1", "112", "$292.32", "$313.74", "$35,138.88", "$0.00"
        # "FFTY !" ,"$0.00 0.00%" ,"$0.00 0.00%" ,"INNOVATOR ETFS TR  IBD" ,"25" ,"$41.05" ,"$41.05" ,"$1,026.25" ,"$0.00"
        # "ESPO !", "$0.00 0.00%", "+$27.13 +6.90%", "VANECK VECTORS VIDEO", "6", "$65.49", "$70.01", "$420.06", "$0.00"
        # "TMUS" ,"$0.00 0.00%" ,"+$10.15 +3.91%" ,"T-MOBILE US INC SHS" ,"2" ,"$129.78" ,"$134.85" ,"$269.70" ,"$0.00"
        # "ORCL !" ,"$0.00 0.00%" ,"+$67.50 +4.98%" ,"ORACLE CORP $0.01    DEL" ,"22" ,"$61.62" ,"$64.69" ,"$1,423.18" ,"$0.00"
        # "GOOG", "+$12.36 +0.71%", "-$57.54 -3.18%", "ALPHABET INC SHS    CL C", "1", "$1,809.42", "$1,751.88", "$1,751.88", "+$12.36"

        lines = f.readlines()
        stocks_dict = {}
        stock_counter = []  # use for reconciliation

        for line in lines:
            # when stock is sold it places -- for unrealized gain and unit cost.
            # need to replace with zeros before regex handle it
            line = re.sub('-- --', '+$0.0 +0.0%', line)
            line = re.sub('--', '$0.0', line)

            if m := r_stock.match(line):
                stock_counter.append(m.group(1))
            if m := r_unit_cost.match(line):
                stock_details = {STOCK_GAIN: m.group(2), STOCK_LAST_PRICE: re.sub(',', '', m.group(3))}
                stocks_dict[m.group(1)] = stock_details

        if len(stocks_dict) != len(stock_counter):
            print(f'Error ***\n{stock_counter=}\n{stocks_dict.keys()=}\n*** not equal when parsing holdings')
            print(f'Difference is {set(stock_counter).difference(set(stocks_dict.keys()))}')
            sys.exit(1)

        return stocks_dict


def extract_orders(input_file: str, stocks_dict: dict):
    """
    extract existing orders from open orders csv file and update stocks_dict

    :param input_file: name of the order file
    :param stocks_dict: dict to store the existing orders
    """
    verbose_print(f'Processing {input_file=} for orders.')

    with open(input_file, 'r') as f:
        # m.group(1) = symbol
        # m.group(2) = stop quote
        r_order = re.compile('.*"\s?([A-Z]{1,4})\s?!?".*"Stop quote\$([0-9,]+\.?[0-9]{2})')
        r_stock = re.compile('.*"\s?([A-Z]{1,4})\s?!?"')
        # "", "12/19/2020 11:21 PM ET", "VVT-5919", "CMA-Edge 5F3-62P16", "Sell", " BA", "3", "Stop quote$208.00", "$0.00 / $0.00", "$214.06", "GTC Expires: 6/18/2021", "Open  "
        # "" ,"9/21/2020 1:53 AM ET" ,"VVT-6890" ,"CMA-Edge 5F3-62P16" ,"Sell" ," GOOG" ,"3" ,"Stop quote$1,691.00" ,"$0.00 / $0.00" ,"$1,751.88" ,"GTC Expires: 3/19/2021" ,"Open  "
        lines = f.readlines()

        stock_counter = []  # for reconciliation
        stock_handle = []  # for reconciliation
        for line in lines:
            if m := r_stock.match(line):
                stock_counter.append(m.group(1))
            if m := r_order.match(line):
                try:
                    stocks_dict[m.group(1)][STOCK_EXIST_STOP] = re.sub(',', '', m.group(2))
                except KeyError:
                    if verbose_flag_indicator == VERBOSE_ARG_ON:
                        print(f'{m.group(1)}: No entry for cost. Adding entry for order.')
                    stocks_dict[m.group(1)] = {}
                    stocks_dict[m.group(1)][STOCK_EXIST_STOP] = re.sub(',', '', m.group(2))
                finally:
                    # for reconciliation
                    stock_handle.append(m.group(1))
        if len(stock_counter) != len(stock_handle):
            print(f'Error ***\n{stock_counter=}\n{stock_handle=}\n*** not equal when parsing existing orders')
            sys.exit(1)

        if verbose_flag_indicator == VERBOSE_ARG_ON:
            for stock, value in stocks_dict.items():
                print(f'{stock=} {value=}')


def calc_95stop_quote(stocks_dict: dict) -> dict:
    """
    calc 95% of unit cost for stop quote

    :param stocks_dict:
    :return: dict with calculated stop quote price
    """
    for stock, stock_details in stocks_dict.items():
        last_price = float(stock_details[STOCK_LAST_PRICE])
        stop_quote_price = round((last_price * PERCENT_FOR_STOP_QUOTE), 2)
        stocks_dict[stock][STOCK_95STOP_QUOTE] = (str(stop_quote_price))

    return stocks_dict


def calc_avg_quote(stocks_dict: dict) -> dict:
    """
    if no exist_stop, then stop_quote is round down of 95%
    if exist stop, then average of 95% and existing stop
    if stop quote is higher than 1000, round to int. if stop quote is higher than 50, round to one precision

    :param stocks_dict:
    :return: dict with calculated new stop quote price
    """
    verbose_print(f'Calculating stop quotes.')

    for stock, stock_details in stocks_dict.items():
        if float(stock_details[STOCK_GAIN]) >= 5 or \
                float(stock_details[STOCK_GAIN]) <= -5 or \
                stock_details[STOCK_EXIST_STOP] != '':
            # calculate only if gain +/-5% or already existing stop quote
            stock_95stop_quote = float(stock_details[STOCK_95STOP_QUOTE])
            if stock_details[STOCK_EXIST_STOP] != '':
                exist_stop = float(stock_details[STOCK_EXIST_STOP])
                avg_stop_quote = round(((stock_95stop_quote + exist_stop) / 2), 2)
                if avg_stop_quote >= 1000:
                    avg_stop_quote = int(avg_stop_quote)
                elif avg_stop_quote >= 50:
                    avg_stop_quote = round(avg_stop_quote, 1)
            else:
                # no existing stop quotes, then round 95% for stop quote
                avg_stop_quote = int(stock_95stop_quote)
            stocks_dict[stock][STOCK_NEW_STOP] = (str(avg_stop_quote))
        else:
            verbose_print(f'No calculation for stock {stock} with gain {stock_details[STOCK_GAIN]}% and existing stop '
                          f'quote of {stock_details[STOCK_EXIST_STOP]}$')
            stocks_dict[stock][STOCK_NEW_STOP] = ''

    if verbose_flag_indicator == VERBOSE_ARG_ON:
        for stock, value in stocks_dict.items():
            print(f'{stock=} {value=}')

    return stocks_dict


def calc_quotes(stocks_dict: dict):
    """
    fill stock exist stop for missing entries and calc stop quotes

    :param stocks_dict:
    :return:
    """
    # fill empty exist stop quote for stocks without existing stop quotes
    for stock, stock_details in stocks_dict.items():
        try:
            _ = stock_details[STOCK_EXIST_STOP]
        except KeyError:
            stock_details[STOCK_EXIST_STOP] = ''

    calc_95stop_quote(stocks_dict)
    calc_avg_quote(stocks_dict)


def print_results(stocks_dict: dict, output_indicator: str):
    if output_indicator == OUTPUT_ARG_YES:
        datetime.now().strftime('%m%d%Y_%H%M%S')
        output_file = os.path.join(os.path.expanduser('~/Downloads'), datetime.now().strftime('%m%d%Y_%H%M%S') + '.summary.csv')
    else:
        output_file = None
    verbose_print(f'Writing output to {output_file}')
    with open(output_file, 'x') if output_file else sys.stdout as f:
        f.write('Symbol,Gain,Last Price,Existing Stop Quote,New Stop Quote,Comments\n')
        for stock, stock_details in stocks_dict.items():
            comments = ''
            try:
                if float(stock_details[STOCK_EXIST_STOP]) > float(stock_details[STOCK_NEW_STOP]):
                    comments = 'New stop quote is lower than the existing!'
            except ValueError:
                # when stock exist stop not exist
                pass
            f.write(stock + ',' + stock_details[STOCK_GAIN] + ',' + stock_details[STOCK_LAST_PRICE] + ',' +
                    stock_details[STOCK_EXIST_STOP] + ',' + stock_details[STOCK_NEW_STOP] + ',' + comments + '\n')


def main():
    files_dict = get_input_file_argparse()
    verify_input_file(files_dict[COST_FILE])
    verify_input_file(files_dict[ORDER_FILE])
    stocks_dict = extract_stocks(files_dict[COST_FILE][0])
    extract_orders(files_dict[ORDER_FILE][0], stocks_dict)
    calc_quotes(stocks_dict)
    print_results(stocks_dict, files_dict[OUTPUT_FLAG])
    sys.exit(0)


if __name__ == '__main__':
    main()
