# TODO: function conversion to final product - research debug mode style
# TODO: clean get user val and get portfolioValue
# TODO: implement proper backtracking for calculating value
# TODO: mongoengine full swap
# TODO: query database instead of grabbing all data and processing in python

# from pymongo import MongoClient
from bson.objectid import ObjectId
import requests
from time import time
from binance.client import Client

import json
import os
import logging
import sys

import gevent
import gevent.monkey

gevent.monkey.patch_socket()

# configs
DEBUG = True
BINANCE_API_KEY = os.environ['BINANCE_API_KEY']
BINANCE_SECRET = os.environ['BINANCE_SECRET']
BINANCE_CLIENT = Client(BINANCE_API_KEY, BINANCE_SECRET)
if (DEBUG):
    logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

LAST_NAV = 1
LAST_TIMESTAMP = 0


#######################
# portfolio functions #
#######################


def getPortfolio(usersDB, transactionsDB, tradesDB, timestamp=int(time())):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    tickers = getTickers()
    tickerPrices = getTickerPrices(tickers, timestamp)
    portfolioPrinciple = getPortfolioPrinciple(transactionsDB, timestamp)
    updateTradeDB(tradesDB, transactionsDB, tickers)
    portfolioTrades = getPortfolioTrades(tradesDB)
    portfolioBalance = getPortfolioBalance()
    portfolioTransactions = getPortfolioTransactions(transactionsDB)

    # add or subtract past transactions to get historical balance
    portfolioHistoBalance = getPortfolioHistoBalance(portfolioBalance, portfolioTrades, portfolioTransactions, timestamp)

    portfolioValue = getPortfolioValue(portfolioHistoBalance, tickerPrices)
    portfolioValueAggregate = aggregatePortfolioValue(portfolioValue)

    curNav = calculateNavCached(transactionsDB, portfolioValueAggregate)

    output = {
        'time': timestamp,
        'nav': curNav,
        'principle': portfolioPrinciple,
        'value': portfolioValueAggregate,
        'performance': int((portfolioValueAggregate - portfolioPrinciple) / portfolioPrinciple * 100) / 100
    }

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return output


def getPortfolioPrinciple(transactionsDB, timestamp=int(time())):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    principle = 0

    for transaction in transactionsDB.find({}):
        if(int(transaction['timestamp']) < timestamp):
            if(transaction['action'] == 'deposit'):
                principle += int(transaction['amount'])
            elif(transaction['action'] == 'withdrawal'):
                principle -= int(transaction['amount'])

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return principle


def getPortfolioTrades(tradesDB):
    return tradesDB.find()


def getPortfolioTransactions(transactionsDB):
    return transactionsDB.find()


def aggregatePortfolioValue(portfolioValue):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    output = 0
    for value in portfolioValue.values():
        output += value

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return output


def getPortfolioValue(portfolioBalance, prices, time=int(time())):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    portfolioValue = {}

    for ticker, balance in portfolioBalance.items():
        if(balance > 0):
            portfolioValue[ticker] = balance * prices[ticker]

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return portfolioValue


def getPortfolioBalance():
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    balance = BINANCE_CLIENT.get_account()

    # hide empty balances / convert to dict
    output = {}
    for balance in balance['balances']:
        if(float(balance['free']) != 0):
            output[balance['asset']] = float(balance['free'])

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return output


# TODO: get historic tickers
def getTickers():
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    balance = BINANCE_CLIENT.get_account()

    # hide empty balances / convert to dict
    tickers = []
    for balance in balance['balances']:
        if(float(balance['free']) != 0):
            tickers.append(balance['asset'])

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return tickers


def getTickerPrices(tickers, timestamp=int(time())):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    prices = {}

    threads = []
    for i in range(len(tickers)):
        threads.append(gevent.spawn(getTickerPrice, tickers[i], 'USD'))
    gevent.joinall(threads)
    for g in threads:
        prices[g.value[1]] = g.value[0]

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return prices


def getTickerPricesBak(tickers, timestamp=int(time())):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    prices = {}
    url = 'https://min-api.cryptocompare.com/data/pricehistorical'

    for ticker in tickers:
        tickerFix = ticker
        if(ticker == 'IOTA'):
            tickerFix = 'IOT'
        elif(ticker == 'NANO'):
            tickerFix = 'XRB'
        elif(ticker == 'BCC'):
            tickerFix = 'BCH'

        params = {
            'fsym': tickerFix,
            'tsyms': 'USD',
            'market': 'BitTrex',
            'ts': timestamp
        }
        r = requests.get(url=url, params=params)
        prices[ticker] = r.json()[tickerFix]['USD']

        # ex: https://min-api.cryptocompare.com/data/pricehistorical?fsym=WTC&tsyms=USD&market=BitTrex

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return prices


def getTickerPrice(ticker1, ticker2, timestamp=int(time())):
    tickerOut = ticker1
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    price = 0
    url = 'https://min-api.cryptocompare.com/data/pricehistorical'

    if(ticker1 == 'IOTA'):
        ticker1 = 'IOT'
    elif(ticker2 == 'IOTA'):
        ticker2 = 'IOT'
    elif(ticker1 == 'NANO'):
        ticker1 = 'XRB'
    elif(ticker2 == 'NANO'):
        ticker2 = 'XRB'
    elif(ticker1 == 'BCC'):
        ticker1 = 'BCH'
    elif(ticker2 == 'BCC'):
        ticker2 = 'BCH'
    params = {
        'fsym': ticker1,
        'tsyms': ticker2,
        'market': 'BitTrex',
        'ts': timestamp
    }
    r = requests.get(url=url, params=params)
    print(r.json())
    price = r.json()[ticker1][ticker2]

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return [tickerOut, price]


def getPortfolioHistoBalance(portfolioBalance, portfolioTrades, portfolioTransactions, timestamp=int(time())):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    # eliminate trades after timestamp
    for trade in portfolioTrades:
        if(trade['timestamp'] > timestamp):
            quantity = float(trade['executedQty'])
            ticker1 = trade['symbol'][:-3]
            ticker2 = trade['symbol'][-3:]
            rate = getTickerPrice(ticker1, ticker2, trade['timestamp'])
            if(trade['side'] == 'BUY'):
                portfolioBalance[ticker1] -= quantity
                portfolioBalance[ticker2] += quantity * rate
            elif(trade['side'] == 'SELL'):
                portfolioBalance[ticker1] += quantity
                portfolioBalance[ticker2] -= quantity * rate

    # TODO: IMPLEMENT PROPER BACK TRACKING
    # eliminate transactions after timestamp using stored transactions - proper method
    # for transaction in portfolioTransactions:
    #     if(transaction['timestamp'] > timestamp):
    #         if(transaction['action'] == 'deposit'):
    #             for ticker, val in transaction['dist'].items():
    #                 portfolioBalance[ticker] -= val
    #         elif(transaction['action'] == 'withdrawal'):
    #             for ticker, val in transaction['dist'].items():
    #                 portfolioBalance[ticker] += val

    # temp back tracking
    if(timestamp <= 1516596360):
        portfolioBalance['BTC'] -= 0.03365017
        portfolioBalance['ETH'] -= 1.48342885
    if(timestamp <= 1517896740):
        portfolioBalance['ETH'] -= 0.39596584

    # clean negative balances due to rounding errors
    for ticker, balance in portfolioBalance.items():
        if(balance < 0):
            portfolioBalance[ticker] = 0

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return portfolioBalance


def calculateNav(transactionsDB, currentPortfolioValue, timestamp):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    newestTimestamp = 0
    newestNav = 1
    newestPortfolioValue = 0
    currentPortfolioValue = currentPortfolioValue

    # check if any newer nav val in DB
    for transaction in transactionsDB.find():
        if(transaction['timestamp'] < timestamp):
            if(transaction['timestamp'] > newestTimestamp):
                newestTimestamp = transaction['timestamp']
                newestNav = transaction['nav']

    for transaction in transactionsDB.find():
        if(transaction['timestamp'] < timestamp):
            if(transaction['action'] == 'deposit'):
                newestPortfolioValue += transaction['amount'] * newestNav

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return newestNav * (currentPortfolioValue / newestPortfolioValue)


def calculateNavCached(transactionsDB, currentPortfolioValue):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    timestamp = getUnixTime()
    global LAST_NAV
    global LAST_TIMESTAMP
    lastNav = LAST_NAV
    lastTimestamp = LAST_TIMESTAMP
    # lastNav = float(os.environ['LAST_NAV'])
    # lastTimestamp = int(os.environ['LAST_TIMESTAMP'])
    lastPortfolioValue = 0

    # check if any newer nav val in DB
    for transaction in transactionsDB.find():
        if(transaction['timestamp'] < timestamp):
            if(transaction['timestamp'] > lastTimestamp):
                lastTimestamp = transaction['timestamp']
                lastNav = transaction['nav']

    for transaction in transactionsDB.find():
        if(transaction['timestamp'] < timestamp):
            if(transaction['action'] == 'deposit'):
                lastPortfolioValue += transaction['amount'] * lastNav

    updatedNav = lastNav * (currentPortfolioValue / lastPortfolioValue)

    # print("Old Nav: " + str(LAST_NAV))
    # print("Old TS: " + str(LAST_TIMESTAMP))
    LAST_NAV = updatedNav
    LAST_TIMESTAMP = timestamp
    # print("New Nav: " + str(LAST_NAV))
    # print("New TS: " + str(LAST_TIMESTAMP))

    # seems to cause unnecessary program restarts
    # updateHerokuVar('LAST_NAV', updatedNav)
    # updateHerokuVar('LAST_TIMESTAMP', timestamp)

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return updatedNav


def updateHerokuVar(key, value):
    herokuApiKey = os.environ['HEROKU_API_KEY']
    url = 'https://api.heroku.com/apps/2fd602bb-b85f-41d0-89cb-ddd031908623/config-vars'
    headers = {
        "Accept": "application/vnd.heroku+json; version=3",
        "Authorization": "Bearer " + herokuApiKey,
        "Content-Type": "application/json"
    }
    data = dict()
    data[key] = value
    data = json.dumps(data)
    requests.patch(url=url, headers=headers, data=data)


#######################
# user menu functions #
#######################

def getUserAccount(usersDB, transactionsDB, tradesDB, histoPricesDB, userId, timestamp=int(time())):
    portfolio = getPortfolio(usersDB, transactionsDB, tradesDB, timestamp)

    portfolioNav = portfolio['nav']

    users = []
    for user in usersDB.find({'_id': ObjectId(userId)}):
        users.append(user)
    user = users[0]

    userPrinciple = getUserPrinciple(user, transactionsDB, timestamp)
    userValue = getUserValue(user, transactionsDB, userPrinciple, portfolioNav, timestamp)

    output = {
        'time': timestamp,
        'firstName': user['firstName'],
        'lastName': user['lastName'],
        'principle': userPrinciple,
        'value': userValue,
        'performance': int((userValue - userPrinciple) / userPrinciple * 100) / 100
    }

    return output


def getUserPrinciple(selectedUser, transactionsDB, timestamp=int(time())):
    userPrinciple = 0
    transactions = []
    for transactionId in selectedUser['transactions']:
        transactions.append(transactionsDB.find_one({'_id': transactionId}))

    for transaction in transactions:
        if(transaction['timestamp'] <= timestamp):
            if(transaction['action'] == 'deposit'):
                userPrinciple += int(transaction['amount'])
            elif(transaction['action'] == 'withdrawal'):
                userPrinciple -= int(transaction['amount'])

    return userPrinciple


def getUserValue(selectedUser, transactionsDB, userPrinciple, curNav, timestamp=int(time())):
    userValue = 0
    transactions = []
    for transactionId in selectedUser['transactions']:
        transactions.append(transactionsDB.find_one({'_id': transactionId}))

    for transaction in transactions:
        if(transaction['timestamp'] <= timestamp):
            if(transaction['action'] == 'deposit'):
                userValue += transaction['amount'] * (curNav / transaction['nav'])
            elif(transaction['action'] == 'withdrawal'):
                userValue -= transaction['amount'] * (curNav / transaction['nav'])

    return userValue


def getTransaction(transactionsDB, transactionId):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    transactions = []
    for transaction in transactionsDB.find({'_id': ObjectId(transactionId)}):
        transaction['_id'] = str(transaction['_id'])
        transactions.append(transaction)

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return transactions


# cleans up excess of properties unneeded for usecase
def sanitizeTrades(binanceTrades):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    sanitizedTrades = []

    for binanceTrade in binanceTrades:
        trade = {}
        trade['executedQty'] = binanceTrade['executedQty']
        trade['origQty'] = binanceTrade['origQty']
        trade['side'] = binanceTrade['side']
        trade['status'] = binanceTrade['status']
        trade['symbol'] = binanceTrade['symbol']
        trade['timestamp'] = int(binanceTrade['time'] / 1000)
        trade['type'] = binanceTrade['type']
        trade['orderId'] = binanceTrade['orderId']
        sanitizedTrades.append(trade)

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return sanitizedTrades


def updateTradeDB(tradesDB, transactionsDB, tickers):
    start = getUnixTimeLog()
    LOGGER.info(currentFuncName() + ': start time: ' + str(start))

    binanceTrades = []
    threads = []
    for i in range(len(tickers)):
        threads.append(gevent.spawn(updateTradeDBHelper1, tickers[i], i))
        threads.append(gevent.spawn(updateTradeDBHelper2, tickers[i], i))
    gevent.joinall(threads)
    for g in threads:
        for trade in g.value:
            binanceTrades.append(trade)

    binanceTrades = sanitizeTrades(binanceTrades)

    # add if not in DB
    for binanceTrade in binanceTrades:
        dbNumTrades = tradesDB.count({'orderId': binanceTrade['orderId']})
        if(dbNumTrades == 0):
            tradesDB.insert_one(binanceTrade)

    # add old trades from JSON in DB
    JSONtrades = json.load(open('oldTrades.json'))
    for JSONtrade in JSONtrades['data']:
        if(not tradesDB.count(JSONtrade)):
            tradesDB.insert_one(JSONtrade)

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')


def updateTradeDBHelper1(ticker, pid):
    start = getUnixTimeLog()
    binanceTrades = []

    # cycle tickers to collect binance trades
    if(ticker != 'BTC'):
        tradeTickers = ticker + 'BTC'
        trades = BINANCE_CLIENT.get_all_orders(symbol=tradeTickers, limit=500)
        for trade in trades:
            binanceTrades.append(trade)
        # print(str(pid) + ' - ' + tradeTickers + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return binanceTrades


def updateTradeDBHelper2(ticker, pid):
    binanceTrades = []
    start = getUnixTimeLog()

    # cycle tickers to collect binance trades
    # REVIEW: why not BTC?
    if(ticker != 'ETH' and ticker != 'BTC' and ticker != 'GAS'):
        # if(ticker == 'NANO'):
        #     ticker = 'XRB'
        tradeTickers = ticker + 'ETH'
        trades = BINANCE_CLIENT.get_all_orders(symbol=tradeTickers, limit=500)
        for trade in trades:
            binanceTrades.append(trade)
        # print(str(pid) + ' - ' + tradeTickers + ': took ' + str(getUnixTimeLog() - start) + ' seconds')

    return binanceTrades


def updateTradeDBBak(tradesDB, transactionsDB, tickers):
    LOGGER.info(currentFuncName() + ': start')
    start = getUnixTimeLog()

    binanceTrades = []

    # cycle tickers to collect binance trades
    for ticker in tickers:
        if(ticker != 'BTC'):
            ticker = ticker + 'BTC'
            trades = BINANCE_CLIENT.get_all_orders(symbol=ticker, limit=500)
            for trade in trades:
                binanceTrades.append(trade)
    for ticker in tickers:
        # REVIEW: why not BTC?
        if(ticker != 'ETH' and ticker != 'BTC' and ticker != 'GAS'):
            # if(ticker == 'NANO'):
            #     ticker = 'XRB'
            ticker = ticker + 'ETH'
            trades = BINANCE_CLIENT.get_all_orders(symbol=ticker, limit=500)
            for trade in trades:
                binanceTrades.append(trade)

    binanceTrades = sanitizeTrades(binanceTrades)

    # add if not in DB
    for binanceTrade in binanceTrades:
        dbNumTrades = tradesDB.count({'orderId': binanceTrade['orderId']})
        if(dbNumTrades == 0):
            tradesDB.insert_one(binanceTrade)

    # add old trades from JSON in DB
    JSONtrades = json.load(open('oldTrades.json'))
    for JSONtrade in JSONtrades['data']:
        if(not tradesDB.count(JSONtrade)):
            tradesDB.insert_one(JSONtrade)

    LOGGER.info(currentFuncName() + ': end')
    LOGGER.info(currentFuncName() + ': took ' + str(getUnixTimeLog() - start) + ' seconds')


def deleteDocs(db, match={}):
    db.delete_many(match)


def getUnixTime():
    return int(time())


def getUnixTimeLog():
    return time()


# for current func name, specify 0 or no argument.
# for name of caller of current func, specify 1.
# for name of caller of caller of current func, specify 2. etc.
currentFuncName = lambda n=0: sys._getframe(n + 1).f_code.co_name
