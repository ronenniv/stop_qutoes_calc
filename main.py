import argparse
import os
import re
import sys

# args constants
COST_FILE = 'cost_file'
ORDER_FILE = 'order_file'
OUTPUT_FILE = 'output_file'
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

    :param text:
    :return:
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
    parser.add_argument('-output', choices=[OUTPUT_ARG_YES, OUTPUT_ARG_NO], nargs='?',
                        required=False, help='send output to file')
    parser.add_argument('-v', '--verbose', choices=[VERBOSE_ARG_ON, VERBOSE_ARG_OFF], nargs=1,
                        required=False, default=verbose_flag_indicator, help='verbose')
    args = parser.parse_args()
    files_dict = dict()
    files_dict[COST_FILE] = args.cost_file
    files_dict[ORDER_FILE] = args.order_file
    files_dict[OUTPUT_FILE] = args.output
    # when default, argparse return params as str, and if it get arg in command line, it return it as list
    if isinstance(args.verbose, list):
        files_dict[VERBOSE_FLAG] = args.verbose[0]
    else:
        files_dict[VERBOSE_FLAG] = args.verbose
    print(f'files_dict={files_dict}')
    return files_dict


def verify_input_file(input_file: list) -> list:
    """
    check if the input file exist and its size larger than 0

    :param input_file: list
    :return:
    """
    for file in input_file:
        if not os.path.isfile(file):
            print(f'Error: file {file} not found.')
            sys.exit(2)
        else:
            if os.path.getsize(file) == 0:
                print(f'Error: file {file} size is zero.')
                sys.exit(2)


def extract_stocks(input_file: str) -> dict:
    """
    extract stock symbol and unit cost from holding csv file

    :param input_file: str
    :return: dict with symbol as key, and unit cost as value
    """
    with open(input_file, 'r') as f:
        r_unit_cost = re.compile(
            '"([A-Z]{1,4})\s?!?".."[+-]?\$\d+\.?\d\d [+-]?\d+\.?\d\d%".."[+-]\$\d+\.?\d* ([+-]\d+\.?\d*)%".."[A-Z0-9- &]*".."\d*.?\d*".."\$[0-9,]+\.?\d*".."\$([0-9,]+\.?\d*)"')
        r_stock = re.compile('"([A-Z]{1,4})\s?!?"')
        # "TMUS" ,"$0.00 0.00%" ,"+$10.15 +3.91%" ,"T-MOBILE US INC SHS" ,"2" ,"$129.78" ,"$134.85" ,"$269.70" ,"$0.00"
        # "ESPO !", "$0.00 0.00%", "+$27.13 +6.90%", "VANECK VECTORS VIDEO", "6", "$65.49", "$70.01", "$420.06", "$0.00"
        # "MRNA" ,"-$6.66 -5.99%" ,"-$113.84 -35.27%" ,"MODERNA INC" ,"2" ,"$161.39" ,"$104.47" ,"$208.94" ,"-$13.32"
        # "GOOG", "+$12.36 +0.71%", "-$57.54 -3.18%", "ALPHABET INC SHS    CL C", "1", "$1,809.42", "$1,751.88", "$1,751.88", "+$12.36"

        lines = f.readlines()
        stocks_dict = {}
        stock_counter = []  # use for counting stocks to verify none got missed

        for line in lines:
            if m := r_stock.match(line):
                stock_counter.append(m.group(1))
            if m := r_unit_cost.match(line):
                stock_details = {STOCK_GAIN: m.group(2), STOCK_LAST_PRICE: re.sub(',', '', m.group(3))}
                stocks_dict[m.group(1)] = stock_details

        if len(stocks_dict) != len(stock_counter):
            print('Error: stock counter is different from found unit cost')
            print(f'{stock_counter=}')
            print(f'{stocks_dict=}')
            sys.exit(2)

        return stocks_dict


def extract_orders(input_file: str, stocks_dict: dict) -> dict:
    """
    extract existing orders from open orders csv file

    :param input_file: name of the order file
    :param stocks_dict: dict to store the existing orders
    :return: stocks_dict with updated existing orders
    """
    verbose_print(f'Processing {input_file=} for orders.')

    with open(input_file, 'r') as f:
        r_order = re.compile('.*"\s?([A-Z]{1,4})\s?!?".*"Stop quote\$([0-9,]+\.?[0-9]{2})')
        r_stock = re.compile('.*"\s?([A-Z]{1,4})\s?!?"')
        # "", "12/19/2020 11:21 PM ET", "VVT-5919", "CMA-Edge 5F3-62P16", "Sell", " BA", "3", "Stop quote$208.00", "$0.00 / $0.00", "$214.06", "GTC Expires: 6/18/2021", "Open  "
        # "" ,"9/21/2020 1:53 AM ET" ,"VVT-6890" ,"CMA-Edge 5F3-62P16" ,"Sell" ," GOOG" ,"3" ,"Stop quote$1,691.00" ,"$0.00 / $0.00" ,"$1,751.88" ,"GTC Expires: 3/19/2021" ,"Open  "
        lines = f.readlines()

        stock_counter = []
        stock_handle = []
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
                    stock_handle.append(m.group(1))
        if len(stock_counter) != len(stock_handle):
            print(f'Error: {stock_counter=} and {stock_handle=} not equal')
            sys.exit(2)

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


def main(argv):
    files_dict = get_input_file_argparse()
    global verbose_flag_indicator
    verbose_flag_indicator = files_dict[VERBOSE_FLAG]
    verbose_print('Verbose ON')
    verify_input_file(files_dict[COST_FILE])
    verify_input_file(files_dict[ORDER_FILE])
    stocks_dict = extract_stocks(files_dict[COST_FILE][0])
    extract_orders(files_dict[ORDER_FILE][0], stocks_dict)
    calc_quotes(stocks_dict)

    sys.exit(0)


if __name__ == '__main__':
    main(sys.argv)
