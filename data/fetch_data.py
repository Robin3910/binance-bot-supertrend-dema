import time
import config
import ccxt
import json


def transTime(timestamp):
    # 转换为localtime
    time_local = time.localtime(timestamp)
    # 转换为新的时间格式
    return time.strftime("%Y-%m-%d %H:%M:%S", time_local)


exchange = ccxt.binanceus({
    "apiKey": config.BINANCE_API_KEY,
    "secret": config.BINANCE_SECRET_KEY
})
coin = config.COIN
# 转换成时间数组
start = time.strptime(config.START_TIME, "%Y-%m-%d %H:%M:%S")
# 转换成时间戳
startTimeStamp = time.mktime(start) * 1000

# 转换成时间数组
end = time.strptime(config.END_TIME, "%Y-%m-%d %H:%M:%S")
# 转换成时间戳
endTimeStamp = time.mktime(end) * 1000

period = config.PERIOD

data = []

print("start load data| start time: " + config.START_TIME + "|ent time: " + config.END_TIME)
while startTimeStamp < endTimeStamp:
    sourceData = exchange.fetch_ohlcv(coin, timeframe=period, since=int(startTimeStamp),
                                      limit=1000)
    print("end time: " + config.END_TIME + "| cur progress: " + transTime(startTimeStamp / 1000))
    data += sourceData
    for source in sourceData:
        if source[0] > endTimeStamp:
            break
        data.append(source)

    startTimeStamp += 1000 * 60 * 60 * 1000

dataJson = json.dumps(data)
fileName = config.COIN.split('/')[0] + config.START_TIME.split(' ')[0] + '-' + config.END_TIME.split(' ')[0] + '.json'

with open(fileName, "w") as file:
    file.write(dataJson)
