"""
calculate stop quotes for BOFA orders
"""
import argparse
import os
import re
import sys
from collections import OrderedDict
from datetime import datetime

# args constants
COST_FILE = 'cost_file'
ORDER_FILE = 'order_file'
OUTPUT_FLAG = 'csv_file'
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
STOCK_HOLDING_QUANTITY = 'HOLDING_QUANTITY'
STOCK_ORDER_QUANTITY = 'ORDER_QUANTITY'
GAIN_RATE = 5  # from which gain to calculate the stop quotes


class Verbose:
    """
    handle verbose status and print messages
    """
    _indicator_flag = VERBOSE_ARG_OFF

    @classmethod
    def set_indicator(cls, indicator_status: str):
        """
        set verbose indicator (on/off)

        :param indicator_status: VERBOSE_ARG_OFF/VERBOSE_ARG_ON
        """
        cls._indicator_flag = indicator_status

    @classmethod
    def print(cls, text: str):
        """
        print text if verbose flag is on

        :param text:
        """
        if cls._indicator_flag == VERBOSE_ARG_ON:
            print(text)


def get_input_file_argparse() -> dict:
    """
    get input file/s from command line arguments

    :return: the input file name/s, verbose flag
    """
    parser = argparse.ArgumentParser(description='Extract stock price and calculate stop quote '
                                                 'price')
    parser.add_argument('-c', '--cost_file',
                        metavar='COST FILE',
                        required=True,
                        help='file name/s with unit cost',
                        nargs='+')
    parser.add_argument('-o', '--order_file',
                        metavar='ORDER FILE',
                        required=True,
                        help='file name/s with order status',
                        nargs='+')
    parser.add_argument('-csv',
                        choices=[OUTPUT_ARG_YES, OUTPUT_ARG_NO],
                        nargs=1,
                        required=False,
                        default='no',
                        help='send output to csv file <date,time>.summary.csv')
    parser.add_argument('-v', '--verbose',
                        choices=[VERBOSE_ARG_ON, VERBOSE_ARG_OFF],
                        nargs=1,
                        required=False,
                        default=VERBOSE_ARG_OFF,
                        help='verbose indicator')
    args = parser.parse_args()
    files_dict = dict()
    if args.cost_file == args.order_file:
        print(f'Error: holding file {args.cost_file} same as order file {args.order_file}')
        sys.exit(1)
    verify_input_file(args.cost_file)
    files_dict[COST_FILE] = args.cost_file
    verify_input_file(args.order_file)
    files_dict[ORDER_FILE] = args.order_file
    files_dict[OUTPUT_FLAG] = args.csv
    # when option is default, argparse return params as str, and if it get arg in command line,
    # it return it as list
    if isinstance(args.verbose, list):
        Verbose.set_indicator(args.verbose[0])
    else:
        Verbose.set_indicator(args.verbose)
    Verbose.print('Verbose is ON')

    if isinstance(args.csv, list):
        files_dict[OUTPUT_FLAG] = args.csv[0]
    else:
        files_dict[OUTPUT_FLAG] = args.csv

    Verbose.print(f'Arguments to be used:\n{files_dict}')
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


def extract_stocks(input_file_name: str) -> dict:
    """
    extract stock symbol and unit cost from holding csv file

    :param input_file_name: str
    :return: dict with symbol as key, and unit cost as value
    """
    Verbose.print(f'Processing {input_file_name=} for holdings.')

    with open(input_file_name, 'r') as file_output_stream:
        # group(1) = Symbol
        # group(2) = Unrealized gain
        # group(3) = Quantity
        # group(4) = Price
        r_unit_cost = re.compile(r'"([A-Z]{1,4})\s?!?"..'  # Symbol
                                 r'"[+-]?\$\d+\.[0-9]{2,4} [+-]?\d+\.[0-9]{2,4}%"..'  # Day price
                                 r'"[+-]?\$[0-9,]+\.?\d* ([+-]?\d+\.?\d*)%"..'  # Unrealized gain
                                 r'"[A-Z].*"..'  # Description
                                 r'"(\d*.?\d*)"..'  # Quantity
                                 r'"\$[0-9,]+\.?\d*"..'  # Unit cost
                                 r'"\$([0-9,]+\.?\d*)"')  # Price
        r_stock = re.compile(r'"([A-Z]{1,4})\s?!?"')
        stocks_dict = {}
        stock_counter = []  # use for reconciliation

        for line in file_output_stream:
            # when stock is sold it places -- for unrealized gain and unit cost.
            # need to replace with zeros before regex handle it
            line = re.sub('-- --', '+$0.0 +0.0%', line)
            line = re.sub('--', '$0.0', line)

            if m_stock := r_stock.match(line):
                stock_counter.append(m_stock.group(1))
            if m_order := r_unit_cost.match(line):
                stock_details = {STOCK_GAIN: float(m_order.group(2)),
                                 STOCK_LAST_PRICE: float(re.sub(',', '', m_order.group(4))),
                                 STOCK_HOLDING_QUANTITY: float(m_order.group(3))}
                stocks_dict[m_order.group(1)] = stock_details

        if len(stocks_dict) != len(stock_counter):
            print(f'Error ***\n{stock_counter=}\n{stocks_dict.keys()=}\n'
                  f'*** not equal when parsing holdings')
            print(f'Difference is {set(stock_counter).difference(set(stocks_dict.keys()))}')
            sys.exit(1)
        else:
            print(f'Found {len(stocks_dict)} stocks in holding files')

        return stocks_dict


def extract_orders(input_file_name: str, stocks_dict: dict):
    """
    extract existing orders from open orders csv file and update stocks_dict

    :param input_file_name: name of the order file
    :param stocks_dict: dict to store the existing orders
    """
    Verbose.print(f'Processing {input_file_name=} for orders.')

    with open(input_file_name, 'r') as file_output_stream:
        # m.group(1) = symbol
        # m.group(2) = quantity
        # m.group(3) = stop quote
        r_order = re.compile(r'.*"\s?'  # any text in the begining of the line
                             r'([A-Z]{1,4})\s?!?".*'  # Symbol
                             r'"(\d*.?\d*)"..'  # Quantity
                             r'"Stop quote'  # Order Type - only Stop quote
                             r'\$([0-9,]+\.?[0-9]{2})')  # Stop quantity price
        r_stock = re.compile(r'.*"\s?'  # any text in the begining of the line
                             r'([A-Z]{1,4})\s?!?".*'  # Symbol
                             r'"Stop quote\$')  # Order Type - only Stop quote
        stock_counter = []  # for reconciliation
        stock_handle = []  # for reconciliation

        for line in file_output_stream:
            if m_stock := r_stock.match(line):
                stock_counter.append(m_stock.group(1))
            if m_order := r_order.match(line):
                stock_details = stocks_dict[m_order.group(1)]
                stock_details[STOCK_EXIST_STOP] = float(re.sub(',', '', m_order.group(3)))
                stock_details[STOCK_ORDER_QUANTITY] = float(m_order.group(2))
                stocks_dict[m_order.group(1)] = stock_details
                # for reconciliation
                stock_handle.append(m_order.group(1))
        if len(stock_counter) != len(stock_handle):
            print(f'Error ***\n{stock_counter=}\n{stock_handle=}\n'
                  f'*** not equal when parsing existing orders')
            sys.exit(1)

        for stock, value in stocks_dict.items():
            Verbose.print(f'{stock=} {value=}')


def calc_95stop_quote(stocks_dict: dict) -> dict:
    """
    calc 95% of unit cost for stop quote

    :param stocks_dict:
    :return: dict with calculated stop quote price
    """
    for stock, stock_details in stocks_dict.items():
        last_price = stock_details[STOCK_LAST_PRICE]
        stop_quote_price = round((last_price * PERCENT_FOR_STOP_QUOTE), 2)
        stocks_dict[stock][STOCK_95STOP_QUOTE] = stop_quote_price

    return stocks_dict


def calc_avg_quote(stocks_dict: dict) -> dict:
    """
    if no exist_stop, then stop_quote is round down of 95% if exist stop, then average of 95% and
    existing stop if stop quote is higher than 1000, round to int. if stop quote is higher than
    50, round to one precision

    :param stocks_dict:
    :return: dict with calculated new stop quote price
    """
    Verbose.print('Calculating stop quotes.')

    for stock, stock_details in stocks_dict.items():
        if stock_details[STOCK_GAIN] >= GAIN_RATE or \
                stock_details[STOCK_GAIN] <= -GAIN_RATE or \
                stock_details[STOCK_EXIST_STOP] != '':
            # calculate only if gain +/-5% or already existing stop quote
            stock_95stop_quote = stock_details[STOCK_95STOP_QUOTE]
            if stock_details[STOCK_EXIST_STOP] != '':
                exist_stop = stock_details[STOCK_EXIST_STOP]
                avg_stop_quote = round(((stock_95stop_quote + exist_stop) / 2), 2)
                # no decimal for stock price higher than 1000
                # one decimal for stock price higher than 50
                if avg_stop_quote >= 1000:
                    avg_stop_quote = int(avg_stop_quote)
                elif avg_stop_quote >= 50:
                    avg_stop_quote = round(avg_stop_quote, 1)
            else:
                # no existing stop quotes, then round 95% for stop quote
                avg_stop_quote = int(stock_95stop_quote)
            stocks_dict[stock][STOCK_NEW_STOP] = avg_stop_quote
        else:
            Verbose.print(f'No calculation for stock {stock} '
                          f'with gain {stock_details[STOCK_GAIN]}% '
                          f'and existing stop quote of {stock_details[STOCK_EXIST_STOP]}$')
            stocks_dict[stock][STOCK_NEW_STOP] = ''

    for stock, value in stocks_dict.items():
        Verbose.print(f'{stock=} {value=}')

    return stocks_dict


def calc_quotes(stocks_dict: dict):
    """
    fill stock exist stop for missing entries and calc stop quotes

    :param stocks_dict:
    :return:
    """
    # fill empty exist stop quote for stocks without existing stop quotes
    for _, stock_details in stocks_dict.items():
        try:
            _ = stock_details[STOCK_EXIST_STOP]
        except KeyError:
            stock_details[STOCK_EXIST_STOP] = ''

    calc_95stop_quote(stocks_dict)
    calc_avg_quote(stocks_dict)


def print_results(stocks_dict: dict, output_indicator: str):
    """
    print calculation results to file or stdout

    :param stocks_dict:
    :param output_indicator: OUTPUT_ARG_YES will send output to csv file
    :return:
    """
    if output_indicator == OUTPUT_ARG_YES:
        output_file_name = datetime.now().strftime('%m%d%Y_%H%M%S') + '.summary.csv'
        output_file_name = os.path.join(os.path.expanduser('~'), 'Downloads', output_file_name)
    else:
        output_file_name = None
    Verbose.print(f'Writing output to {output_file_name}')

    # order stocks before printing
    stocks_dict_ordered = OrderedDict(sorted(stocks_dict.items()))

    with open(output_file_name, 'x') if output_file_name else sys.stdout as file_output_stream:
        file_output_stream.write('Symbol,Gain,Last Price,Existing Stop Quote,New Stop Quote,'
                                 'Comments\n')
        for stock, stock_details in stocks_dict_ordered.items():
            comments = ''
            try:
                if float(stock_details[STOCK_EXIST_STOP]) > float(stock_details[STOCK_NEW_STOP]):
                    comments = 'New stop quote is lower than the existing! '
            except ValueError:
                # when STOCK_EXIST_STOP value not exist
                pass
            else:
                # holding quantity can be fractions of a stock
                # round it to int for comparing holding and order quantity
                if int(stock_details[STOCK_HOLDING_QUANTITY]) != \
                        stock_details[STOCK_ORDER_QUANTITY]:
                    comments += 'Quantities are different! '
            file_output_stream.write(f'{stock},'
                                     f'{stock_details[STOCK_GAIN]},'
                                     f'{stock_details[STOCK_LAST_PRICE]},'
                                     f'{stock_details[STOCK_EXIST_STOP]},'
                                     f'{stock_details[STOCK_NEW_STOP]},'
                                     f'{comments}\n')


def main():
    """
    main function to execute parsing and calculation
    """
    files_dict = get_input_file_argparse()
    stocks_dict = extract_stocks(files_dict[COST_FILE][0])
    extract_orders(files_dict[ORDER_FILE][0], stocks_dict)
    calc_quotes(stocks_dict)
    print_results(stocks_dict, files_dict[OUTPUT_FLAG])
    sys.exit(0)


if __name__ == '__main__':
    main()
