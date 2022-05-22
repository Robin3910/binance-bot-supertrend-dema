import ccxt
import config
import schedule
import pandas as pd
import requests
import sys
import numpy
import talib



pd.set_option('display.max_rows', None)

import warnings
warnings.filterwarnings('ignore')

from datetime import datetime
import time

coin = sys.argv[1]
print(coin)
# 1 buy 2 sell
direction = 1
# 是否已满仓
inPosition = False
# 开仓价格
buyPrice = 0

bars = []

revenueRate = 0

exchange = ccxt.binanceus({
    "apiKey": config.BINANCE_API_KEY,
    "secret": config.BINANCE_SECRET_KEY
})

def tr(data):
    data['previous_close'] = data['close'].shift(1)
    data['high-low'] = abs(data['high'] - data['low'])
    data['high-pc'] = abs(data['high'] - data['previous_close'])
    data['low-pc'] = abs(data['low'] - data['previous_close'])

    tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)

    return tr

def atr(data, period):
    data['tr'] = tr(data)
    atr = data['tr'].rolling(period).mean()

    return atr

def supertrend(df, period=34, atr_multiplier=3):
    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df, period)
    df['upperband'] = hl2 + (atr_multiplier * df['atr'])
    df['lowerband'] = hl2 - (atr_multiplier * df['atr'])
    df['in_uptrend'] = True


    for current in range(1, len(df.index)):
        previous = current - 1

        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['lowerband'][previous]:
            df['in_uptrend'][current] = False
        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]

            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]

            if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]


    return df



def check_buy_sell_signals(df):

    print("checking for buy and sell signals")
    print(df.tail(5))
    last_row_index = len(df.index) - 1
    previous_row_index = last_row_index - 1
    if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]:
        closeArr = []
        for bar in bars:
            closeArr.append(bar[4])

        dema144 = calcDEMA(closeArr, 144)
        dema169 = calcDEMA(closeArr, 169)
        print("changed to uptrend, buy")
        # 微信通知
        # requests.get(
        #         'https://sctapi.ftqq.com/SCT143186TIvKuCgmwWnzzzGQ6mE5qmyFU.send?title='+coin+'/buy')
        if not inPosition:
            if df["open"][last_row_index] >= dema169 :




    
    if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]:
        print("changed to downtrend, sell")
        # 微信通知
        # requests.get(
        #         'https://sctapi.ftqq.com/SCT143186TIvKuCgmwWnzzzGQ6mE5qmyFU.send?title='+coin+'/sell')


def run_bot():
    print(f"Fetching new bars for {datetime.now().isoformat()}")
    bars = exchange.fetch_ohlcv(coin, timeframe='1h', since=1586394000000, limit=2000)
    print(bars)

    # df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    # df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    # supertrend_data = supertrend(df)
    # print(supertrend_data)
    #
    # check_buy_sell_signals(supertrend_data)

def calcDEMA(arr, type):
    close = numpy.asarray(arr)
    output = talib.DEMA(close, timeperiod=type)
    a = output.tolist()
    print(a[len(a) - 1])
    return a[len(a) - 1]


schedule.every(5).seconds.do(run_bot)

while True:
    schedule.run_pending()
    time.sleep(1)
