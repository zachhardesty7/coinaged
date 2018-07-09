#!/usr/bin/python
# -*- coding: utf-8 -*-
# TODO: clean get user val and get portfolioValue
# TODO: implement proper backtracking for calculating value
# TODO: prevent large time view queries from trying to get non-existent data
# TODO: mongoengine full swap
# TODO: query database instead of grabbing all data and processing in python

from time import time
import json
import os
import logging
import sys
from functools import wraps
from timeit import default_timer

# from pymongo import MongoClient

from bson.objectid import ObjectId
import requests
from binance.client import Client

import gevent
import gevent.monkey
gevent.monkey.patch_socket()

# configs

INFO = True
DEBUG = False
LOCAL = False

if LOCAL:
    JSON = json.load(open('secret.json'))
    BINANCE_API_KEY = JSON['binance']['binanceApiKey']
    BINANCE_SECRET = JSON['binance']['binanceSecret']
else:
    BINANCE_API_KEY = os.environ['BINANCE_API_KEY']
    BINANCE_SECRET = os.environ['BINANCE_SECRET']

BINANCE_CLIENT = Client(BINANCE_API_KEY, BINANCE_SECRET)

if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
if INFO:
    logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

LAST_NAV = 1
LAST_TIMESTAMP = 0


# source: https://gist.github.com/p7k/4238388

def gevent_throttle(calls_per_sec=0):
    """Decorates a Greenlet function for throttling."""

    interval = (1. / calls_per_sec if calls_per_sec else 0)

    def decorate(func):
        blocked = [False]

        # has to be a list to not get localised inside the while loop
        # otherwise, UnboundLocalError: local variable 'blocked' referenced
        # before assignment

        last_time = [0]  # ditto

        # propagates docstring

        @wraps(func)
        def throttled_func(*args, **kwargs):
            while True:

                # give other greenlets a chance to run, otherwise we
                # might get stuck while working thread is sleeping and the
                # block is ON

                gevent.sleep(0)
                if not blocked[0]:
                    blocked[0] = True

                    # check if actually might need to pause

                    if calls_per_sec:
                        (last, current) = (last_time[0],
                                           default_timer())
                        elapsed = current - last
                        if elapsed < interval:
                            gevent.sleep(interval - elapsed)
                        last_time[0] = default_timer()
                    blocked[0] = False
                    return func(*args, **kwargs)

        return throttled_func

    return decorate


#######################
# portfolio functions #
#######################

def getPortfolioHisto(
        usersDB,
        transactionsDB,
        tradesDB,
        interval,
        aggregate,
        limit,
):
    LOGGER.debug('%s: start', curFuncName())
    start = getTime()
    timestamp = int(time())

    tickers = getTickers()

    # REVIEW: formating is weird, http://127.0.0.1:5000/portfolio/historical/

    tickerPrices = getTickerPricesHisto(tickers, interval, aggregate,
                                        limit)

    # only update trades hourly

    if timestamp - LAST_TIMESTAMP > 3600:
        updateTradeDB(tradesDB, transactionsDB, tickerPrices.keys())

    portfolioTrades = getPortfolioTrades(tradesDB)
    portfolioTransactions = getPortfolioTransactions(transactionsDB)
    portfolioBalance = getPortfolioBalance()

    output = []

    # build all intervals

    for i in range(0, limit):
        ts = list(tickerPrices.values())[0][i]['timestamp']
        portfolioPrinciple = getPortfolioPrinciple(transactionsDB, ts)
        portfolioHistoBalance = \
            getPortfolioHistoBalance(portfolioBalance, portfolioTrades,
                                     portfolioTransactions, ts)

        # no data or balance held in intervals that fail this check

        if portfolioPrinciple > 0:

            # build single interval

            tickerPricesInterval = {}
            for (ticker, data) in tickerPrices.items():
                tickerPricesInterval[ticker] = data[i]['price']

            portfolioValue = getPortfolioValue(portfolioHistoBalance,
                                               tickerPricesInterval)
            portfolioValueAggregate = \
                aggregatePortfolioValue(portfolioValue)
            curNav = calculateNavCached(transactionsDB,
                                        portfolioValueAggregate)

            portfolioPerformance = int(
                (portfolioValueAggregate - portfolioPrinciple) / portfolioPrinciple * 100) / 100

            periodData = {
                'timestamp': ts,
                'principle': portfolioPrinciple,
                'value': portfolioValueAggregate,
                'nav': curNav,
                'tickers': {},
                'performance': portfolioPerformance,
            }

            # add each ticker data to output

            for (ticker, value) in portfolioValue.items():
                periodData['tickers'][ticker] = \
                    {'quantity': portfolioHistoBalance[ticker],
                     'price': tickerPricesInterval[ticker],
                     'value': value}

            output.append(periodData)

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime()
                 - start)

    return output


def getPortfolio(
        usersDB,
        transactionsDB,
        tradesDB,
        timestamp=int(time()),
):
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    tickers = getTickers()
    tickerPrices = getTickerPrices(tickers, timestamp)

    portfolioPrinciple = getPortfolioPrinciple(transactionsDB,
                                               timestamp)

    # only update hourly

    if timestamp - LAST_TIMESTAMP > 3600:
        updateTradeDB(tradesDB, transactionsDB, tickerPrices.keys())
    portfolioTrades = getPortfolioTrades(tradesDB)
    portfolioBalance = getPortfolioBalance()
    portfolioTransactions = getPortfolioTransactions(transactionsDB)

    # add or subtract past transactions to get historical balance

    portfolioHistoBalance = getPortfolioHistoBalance(
        portfolioBalance, portfolioTrades, portfolioTransactions, timestamp)

    portfolioValue = getPortfolioValue(portfolioHistoBalance,
                                       tickerPrices)
    portfolioValueAggregate = aggregatePortfolioValue(portfolioValue)

    curNav = calculateNavCached(transactionsDB, portfolioValueAggregate)

    portfolioPerformance = int((portfolioValueAggregate
                                - portfolioPrinciple)
                               / portfolioPrinciple * 100) / 100

    # add portfolio data to output

    output = {
        'time': timestamp,
        'tickers': {},
        'nav': curNav,
        'principle': portfolioPrinciple,
        'value': portfolioValueAggregate,
        'performance': portfolioPerformance,
    }

    # add all ticker data to output

    for (ticker, _) in tickerPrices.items():
        output['tickers'][ticker] = \
            {'quantity': portfolioHistoBalance[ticker],
             'price': tickerPrices[ticker],
             'value': portfolioValue[ticker]}

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return output


def getPortfolioPrinciple(transactionsDB, timestamp=int(time())):
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    principle = 0

    for transaction in transactionsDB.find({}):
        if int(transaction['timestamp']) < timestamp:
            if transaction['action'] == 'deposit':
                principle += int(transaction['amount'])
            elif transaction['action'] == 'withdrawal':
                principle -= int(transaction['amount'])

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return principle


def getPortfolioTrades(tradesDB):
    return tradesDB.find()


def getPortfolioTransactions(transactionsDB):
    return transactionsDB.find()


def aggregatePortfolioValue(portfolioValue):
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    output = 0
    for value in portfolioValue.values():
        output += value

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return output


def getPortfolioValue(portfolioBalance, prices, timestamp=int(time())):
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    portfolioValue = {}

    for (ticker, price) in prices.items():
        balance = portfolioBalance[ticker]
        if balance > 0:
            portfolioValue[ticker] = balance * price

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return portfolioValue


def getPortfolioBalance():
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    balance = BINANCE_CLIENT.get_account()

    # hide empty balances / convert to dict

    output = {}
    for balance in balance['balances']:
        if float(balance['free']) != 0:
            output[balance['asset']] = float(balance['free'])

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return output


# TODO: get historic tickers

def getTickers():
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    balance = BINANCE_CLIENT.get_account()

    # hide empty balances / convert to dict

    tickers = []
    for balance in balance['balances']:
        if float(balance['free']) != 0:
            tickers.append(balance['asset'])

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return tickers


def getTickerPrices(tickers, timestamp=int(time())):
    """get price of given tickers

    Arguments:
        tickers {object} -- list of tickers

    Keyword Arguments:
        timestamp {Time} -- desired time (default: {int(time())})

    Returns:
        object -- price of each ticker
    """

    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    prices = {}

    threads = []
    for ticker in tickers:
        threads.append(gevent.spawn(getTickerPrice, ticker, 'USD'))
    gevent.joinall(threads)
    for g in threads:
        if g.value is not None:
            prices[g.value[0]] = g.value[1]

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return prices


def getTickerPricesHisto(
        tickers,
        interval,
        aggregate,
        limit,
):
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    prices = {}

    threads = []
    for ticker in tickers:
        threads.append(gevent.spawn(
            getTickerPriceHisto,
            ticker,
            'USD',
            interval,
            aggregate,
            limit,
        ))
    gevent.joinall(threads)
    for g in threads:
        if g.value is not None:
            prices[g.value[0]] = g.value[1]

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return prices


# can fail in weird cases where tickers don't exist in price data and
# doesn't break anything

@gevent_throttle(14)
def getTickerPrice(ticker1, ticker2, timestamp=int(time())):
    tickerOrig = ticker1

    price = 0
    url = 'https://min-api.cryptocompare.com/data/pricehistorical'

    if ticker1 == 'IOTA':
        ticker1 = 'IOT'
    elif ticker2 == 'IOTA':
        ticker2 = 'IOT'
    elif ticker1 == 'NANO':
        ticker1 = 'XRB'
    elif ticker2 == 'NANO':
        ticker2 = 'XRB'
    elif ticker1 == 'BCC':
        ticker1 = 'BCH'
    elif ticker2 == 'BCC':
        ticker2 = 'BCH'

    params = {
        'fsym': ticker1,
        'tsyms': ticker2,
        'market': 'BitTrex',
        'ts': timestamp,
    }

    r = requests.get(url=url, params=params).json()

    if 'Response' in r:
        LOGGER.warning(
            '%s is not registered on the cryptocompare api, ticker will be ignored',
            ticker1)
        return None
    else:
        price = r[ticker1][ticker2]

    return [tickerOrig, price]


# can fail in weird cases where tickers don't exist in price data and
# doesn't break anything

@gevent_throttle(14)
def getTickerPriceHisto(
        ticker1,
        ticker2,
        interval,
        aggregate,
        limit,
):
    tickerOrig = ticker1

    url = 'https://min-api.cryptocompare.com/data/histo' + interval

    if ticker1 == 'IOTA':
        ticker1 = 'IOT'
    elif ticker2 == 'IOTA':
        ticker2 = 'IOT'
    elif ticker1 == 'NANO':
        ticker1 = 'XRB'
    elif ticker2 == 'NANO':
        ticker2 = 'XRB'
    elif ticker1 == 'BCC':
        ticker1 = 'BCH'
    elif ticker2 == 'BCC':
        ticker2 = 'BCH'

    params = {
        'fsym': ticker1,
        'tsym': ticker2,
        'aggregate': aggregate,
        'limit': limit,
    }

    r = requests.get(url=url, params=params).json()

    if r['Response'] != 'Success':
        LOGGER.warning(
            '%s is not registered on the cryptocompare api, ticker will be ignored',
            ticker1)
        return None
    else:
        prices = []

        for ts in r['Data']:
            prices.append({'timestamp': ts['time'], 'price': (
                ts['open'] + ts['close']) / 2})

    return [tickerOrig, prices]


def getPortfolioHistoBalance(
        portfolioBalance,
        portfolioTrades,
        portfolioTransactions,
        timestamp=int(time()),
):

    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    # eliminate trades after timestamp

    for trade in portfolioTrades:
        if trade['timestamp'] > timestamp:
            quantity = float(trade['executedQty'])
            ticker1 = (trade['symbol'])[:-3]
            ticker2 = (trade['symbol'])[-3:]
            rate = getTickerPrice(ticker1, ticker2, trade['timestamp'])[1]
            if trade['side'] == 'BUY':
                portfolioBalance[ticker1] -= quantity
                portfolioBalance[ticker2] += quantity * rate
            elif trade['side'] == 'SELL':
                portfolioBalance[ticker1] += quantity
                portfolioBalance[ticker2] -= quantity * rate

    # TODO: IMPLEMENT PROPER BACK TRACKING
    # eliminate transactions after timestamp using stored transactions - proper method
    # for transaction in portfolioTransactions:
    #     if transaction['timestamp'] > timestamp:
    #         if transaction['action'] == 'deposit':
    #             for ticker, val in transaction['dist'].items():
    #                 portfolioBalance[ticker] -= val
    #         elif transaction['action'] == 'withdrawal':
    #             for ticker, val in transaction['dist'].items():
    #                 portfolioBalance[ticker] += val

    # temp back tracking

    if timestamp <= 1516596360:
        portfolioBalance['BTC'] -= 0.03365017
        portfolioBalance['ETH'] -= 1.48342885
    if timestamp <= 1517896740:
        portfolioBalance['ETH'] -= 0.39596584

    # clean negative balances due to rounding errors

    for (ticker, balance) in portfolioBalance.items():
        if balance < 0:
            portfolioBalance[ticker] = 0

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return portfolioBalance


def calculateNav(transactionsDB, currentPortfolioValue, timestamp):
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    newestTimestamp = 0
    newestNav = 1
    newestPortfolioValue = 0
    currentPortfolioValue = currentPortfolioValue

    # check if any newer nav val in DB

    for transaction in transactionsDB.find():
        if transaction['timestamp'] < timestamp:
            if transaction['timestamp'] > newestTimestamp:
                newestTimestamp = transaction['timestamp']
                newestNav = transaction['nav']

    for transaction in transactionsDB.find():
        if transaction['timestamp'] < timestamp:
            if transaction['action'] == 'deposit':
                newestPortfolioValue += transaction['amount'] \
                    * newestNav

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return newestNav * (currentPortfolioValue / newestPortfolioValue)


# pylint: disable=W0603

def calculateNavCached(transactionsDB, currentPortfolioValue):
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    timestamp = int(time())
    global LAST_NAV
    global LAST_TIMESTAMP
    lastNav = LAST_NAV
    lastTimestamp = LAST_TIMESTAMP

    lastPortfolioValue = 0

    # check if any newer nav val in DB

    for transaction in transactionsDB.find():
        if transaction['timestamp'] < timestamp:
            if transaction['timestamp'] > lastTimestamp:
                lastTimestamp = transaction['timestamp']
                lastNav = transaction['nav']

    for transaction in transactionsDB.find():
        if transaction['timestamp'] < timestamp:
            if transaction['action'] == 'deposit':
                lastPortfolioValue += transaction['amount'] * lastNav

    updatedNav = lastNav * (currentPortfolioValue / lastPortfolioValue)

    LAST_NAV = updatedNav
    LAST_TIMESTAMP = timestamp

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return updatedNav


#######################
# user menu functions #
#######################

def getUserAccount(
        usersDB,
        transactionsDB,
        tradesDB,
        histoPricesDB,
        userId,
        timestamp=int(time()),
):

    portfolio = getPortfolio(usersDB, transactionsDB, tradesDB,
                             timestamp)

    portfolioNav = portfolio['nav']

    users = []
    for user in usersDB.find({'_id': ObjectId(userId)}):
        users.append(user)
    user = users[0]

    userPrinciple = getUserPrinciple(user, transactionsDB, timestamp)
    userValue = getUserValue(user, transactionsDB, userPrinciple,
                             portfolioNav, timestamp)

    userPerformance = int((userValue - userPrinciple) / userPrinciple
                          * 100) / 100
    output = {
        'time': timestamp,
        'firstName': user['firstName'],
        'lastName': user['lastName'],
        'principle': userPrinciple,
        'value': userValue,
        'performance': userPerformance,
    }

    return output


def getUserPrinciple(selectedUser, transactionsDB,
                     timestamp=int(time())):
    userPrinciple = 0
    transactions = []
    for transactionId in selectedUser['transactions']:
        transactions.append(transactionsDB.find_one({'_id': transactionId}))

    for transaction in transactions:
        if transaction['timestamp'] <= timestamp:
            if transaction['action'] == 'deposit':
                userPrinciple += int(transaction['amount'])
            elif transaction['action'] == 'withdrawal':
                userPrinciple -= int(transaction['amount'])

    return userPrinciple


def getUserValue(
        selectedUser,
        transactionsDB,
        userPrinciple,
        curNav,
        timestamp=int(time()),
):

    userValue = 0
    transactions = []
    for transactionId in selectedUser['transactions']:
        transactions.append(transactionsDB.find_one({'_id': transactionId}))

    for transaction in transactions:
        if transaction['timestamp'] <= timestamp:
            if transaction['action'] == 'deposit':
                userValue += transaction['amount'] * (curNav
                                                      / transaction['nav'])
            elif transaction['action'] == 'withdrawal':
                userValue -= transaction['amount'] * (curNav
                                                      / transaction['nav'])

    return userValue


def getTransaction(transactionsDB, transactionId):
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    transactions = []
    for transaction in \
            transactionsDB.find({'_id': ObjectId(transactionId)}):
        transaction['_id'] = str(transaction['_id'])
        transactions.append(transaction)

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return transactions


# cleans up excess of properties unneeded for usecase

def sanitizeTrades(binanceTrades):
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    sanitizedTrades = []

    for binanceTrade in binanceTrades:
        trade = {
            'executedQty': binanceTrade['executedQty'],
            'origQty': binanceTrade['origQty'],
            'side': binanceTrade['side'],
            'status': binanceTrade['status'],
            'symbol': binanceTrade['symbol'],
            'timestamp': int(binanceTrade['time'] / 1000),
            'type': binanceTrade['type'],
            'orderId': binanceTrade['orderId'],
        }

        sanitizedTrades.append(trade)

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)

    return sanitizedTrades


def updateTradeDB(tradesDB, transactionsDB, tickers):
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    binanceTrades = []
    threads = []
    for ticker in tickers:
        threads.append(gevent.spawn(updateTradeDBHelper1, ticker))
        threads.append(gevent.spawn(updateTradeDBHelper2, ticker))
    gevent.joinall(threads)
    for g in threads:
        for trade in g.value:
            binanceTrades.append(trade)

    binanceTrades = sanitizeTrades(binanceTrades)

    # add if not in DB

    for binanceTrade in binanceTrades:
        dbNumTrades = tradesDB.count({'orderId': binanceTrade['orderId']})
        if dbNumTrades == 0:
            tradesDB.insert_one(binanceTrade)

    # add old trades from JSON in DB

    JSONtrades = json.load(open('oldTrades.json'))
    for JSONtrade in JSONtrades['data']:
        if not tradesDB.count(JSONtrade):
            tradesDB.insert_one(JSONtrade)

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)


def updateTradeDBHelper1(ticker):
    binanceTrades = []

    if ticker != 'BTC':
        tradeTickers = ticker + 'BTC'
        LOGGER.debug('%s: started at %s', tradeTickers, getTime())
        trades = BINANCE_CLIENT.get_all_orders(symbol=tradeTickers,
                                               limit=500)
        for trade in trades:
            binanceTrades.append(trade)

    return binanceTrades


def updateTradeDBHelper2(ticker):
    binanceTrades = []

    # REVIEW: why not BTC?

    if ticker != 'ETH' and ticker != 'BTC' and ticker != 'GAS':

        # if ticker == 'NANO':
        #     ticker = 'XRB'

        tradeTickers = ticker + 'ETH'
        LOGGER.debug('%s: started at %s', tradeTickers, getTime())
        trades = BINANCE_CLIENT.get_all_orders(symbol=tradeTickers,
                                               limit=500)
        for trade in trades:
            binanceTrades.append(trade)

    return binanceTrades


def updateTradeDBBak(tradesDB, transactionsDB, tickers):
    start = getTime()
    LOGGER.debug('%s: start', curFuncName())

    binanceTrades = []

    # cycle tickers to collect binance trades

    for ticker in tickers:
        if ticker != 'BTC':
            ticker = ticker + 'BTC'
            trades = BINANCE_CLIENT.get_all_orders(symbol=ticker,
                                                   limit=500)
            for trade in trades:
                binanceTrades.append(trade)
    for ticker in tickers:

        # REVIEW: why not BTC?

        if ticker != 'ETH' and ticker != 'BTC' and ticker != 'GAS':

            # if ticker == 'NANO':
            #     ticker = 'XRB'

            ticker = ticker + 'ETH'
            trades = BINANCE_CLIENT.get_all_orders(symbol=ticker,
                                                   limit=500)
            for trade in trades:
                binanceTrades.append(trade)

    binanceTrades = sanitizeTrades(binanceTrades)

    # add if not in DB

    for binanceTrade in binanceTrades:
        dbNumTrades = tradesDB.count({'orderId': binanceTrade['orderId']})
        if dbNumTrades == 0:
            tradesDB.insert_one(binanceTrade)

    # add old trades from JSON in DB

    JSONtrades = json.load(open('oldTrades.json'))
    for JSONtrade in JSONtrades['data']:
        if not tradesDB.count(JSONtrade):
            tradesDB.insert_one(JSONtrade)

    LOGGER.debug('%s: took %s seconds', curFuncName(), getTime() - start)


# pylint: disable=W0102
def deleteDocs(db, match={}):
    db.delete_many(match)


# for current func name, specify 0 or no argument.
# for name of caller of current func, specify 1.
# for name of caller of caller of current func, specify 2. etc.

def curFuncName(n=0):
    return sys._getframe(n + 1).f_code.co_name  # pylint: disable=W0212


def getTime():
    return time()
