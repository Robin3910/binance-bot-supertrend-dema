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

import time

coin = config.COIN
print(coin)
# 1 buy 2 sell
direction = 1
# 是否已开仓
inPosition = False
# 开仓价格
buyPrice = 0
# 计算数据
bars = []
# 收益率
revenueRate = 0
# 收线价格数组closeArr，用于计算DEMA
closeArr = []

exchange = ccxt.binanceus({
    "apiKey": config.BINANCE_API_KEY,
    "secret": config.BINANCE_SECRET_KEY
})

# 转换成时间数组
timeArray = time.strptime(config.PERIOD_START, "%Y-%m-%d %H:%M:%S")
# 转换成时间戳
timestamp = time.mktime(timeArray)

# 源数据，每次最多1000根K线
sourceData = exchange.fetch_ohlcv(coin, timeframe='1h', since=int(timestamp * 1000 - config.DEMA_PRE_FIX_TIME),
                                  limit=1000)
# 源数据索引
index = 0


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
    global inPosition
    global bars
    global buyPrice
    global direction
    global revenueRate
    global closeArr
    print("checking for buy and sell signals")
    print(df.tail(5))
    last_row_index = len(df.index) - 1
    previous_row_index = last_row_index - 1

    dema144 = calcDEMA(closeArr, 144)
    dema169 = calcDEMA(closeArr, 169)

    # 出现多头信号
    if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]:

        print("changed to uptrend, buy")
        # 方向切换了，如果现在还持有仓位，则止损平仓
        if inPosition and direction == 2:
            inPosition = False
            revenueRate -= (df["close"][last_row_index] - buyPrice) / buyPrice
            print("sell direction, close the position, revenue -", (df["open"][last_row_index] - buyPrice) / buyPrice)
        # 微信通知
        # requests.get(
        #         'https://sctapi.ftqq.com/SCT143186TIvKuCgmwWnzzzGQ6mE5qmyFU.send?title='+coin+'/buy')
        if not inPosition and df["close"][last_row_index] >= dema169:
            inPosition = True
            buyPrice = df["close"][last_row_index]
            direction = 1
            print("buy: ", df["timestamp"][last_row_index], "|", buyPrice, "|")

    # 出现空头信号
    if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]:
        print("changed to downtrend, sell")
        # 方向切换了，如果现在还持有仓位，则止损平仓
        if inPosition and direction == 1:
            inPosition = False
            revenueRate -= (buyPrice - df["close"][last_row_index]) / buyPrice
            print("buy direction, close the position, revenue -", (buyPrice - df["open"][last_row_index]) / buyPrice)

        # 微信通知
        # requests.get(
        #         'https://sctapi.ftqq.com/SCT143186TIvKuCgmwWnzzzGQ6mE5qmyFU.send?title='+coin+'/sell')
        if not inPosition and df["close"][last_row_index] <= dema144:
            inPosition = True
            buyPrice = df["close"][last_row_index]
            direction = 2
            print("sell: ", df["timestamp"][last_row_index], "|", buyPrice, "|")


def init():
    global index
    global bars
    global sourceData
    global closeArr
    # init
    # 需要加载足够的K线才能开始计算DEMA，否则会出现nan
    while index < 400:
        bars.append(sourceData[index])
        closeArr.append(sourceData[index][4])
        index += 1
    print("load data finished")
    print(sourceData[index])


def run_bot():
    global index
    global bars
    global inPosition
    global direction
    global buyPrice
    global revenueRate
    global sourceData

    # 每次循环加入一根K线
    bars.append(sourceData[index])
    closeArr.append(sourceData[index][4])

    # 判断是否平仓，收益率
    if inPosition:
        if direction == 1 and ((sourceData[index][2] - buyPrice) / buyPrice >= config.PROFIT_POINT):
            print("buy direction, close the position, +", config.PROFIT_POINT, " revenue")
            inPosition = False
            revenueRate += config.PROFIT_POINT
        if direction == 2 and ((buyPrice - sourceData[index][3]) / buyPrice >= config.PROFIT_POINT):
            print("sell direction, close the position, +", config.PROFIT_POINT, " revenue")
            inPosition = False
            revenueRate += config.PROFIT_POINT

    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], origin='1970-01-01 08:00:00', unit='ms')
    supertrend_data = supertrend(df)
    # print(supertrend_data)

    check_buy_sell_signals(supertrend_data)

    index += 1

    print("cur revenue: ", revenueRate, "|cur inPosition: ", inPosition, "|direction: ", direction)
    if inPosition:
        print("buyPrice: ", buyPrice)


# 计算DEMA
def calcDEMA(arr, type):
    close = numpy.asarray(arr)
    output = talib.DEMA(close, timeperiod=type)
    a = output.tolist()
    print(a[len(a) - 1])
    return a[len(a) - 1]


init()
# time.sleep(5)
# schedule.every(0.2).seconds.do(run_bot)

while True:
    run_bot()
    time.sleep(1)
    # schedule.run_pending()
    # time.sleep(1)
