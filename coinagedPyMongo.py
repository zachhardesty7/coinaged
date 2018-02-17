# TODO: python api
# TODO: remove manual user inputs
# TODO: function conversion to final product - research debug mode style
# TODO: clean get user val and get portfolioValue
# TODO: implement proper backtracking for calculating value
# TODO: implement cursesmenu
# TODO: mongoengine full swap
# TODO: query database instead of grabbing all data and processing in python

from pymongo import MongoClient
from bson.objectid import ObjectId
import requests
from math import log10, floor
from time import time
from binance.client import Client
import json
from datetime import datetime

# configs
MUTED = False
SYMS = ['ADA', 'ARK', 'BCC', 'BNB', 'BTC', 'DASH', 'EOS', 'ETH', 'ICX', 'IOTA', 'LSK', 'LTC', 'NEO', 'OMG', 'TRX', 'VEN', 'WTC', 'XLM', 'XMR', 'XRP', 'XVG']
binanceApiKey = '***REMOVED***'
binanceSecret = '***REMOVED***'
BINANCE_CLIENT = Client(binanceApiKey, binanceSecret)

# database struct reference
histoPricesStruct1 = {  # currently unused
    'timestamp': '1514760000',
    'data': {
        'BTC': {
            'value': 12345,
            'category': 'primary'
        },
        'ETH': {
            'value': 12345,
            'category': 'secondary'
        }
    }
}

usersStruct = {
    'firstName': 'zach',
    'lastName': 'hardesty',
    'email': 'name@example.com',
    'phone': '18000000000',
    'transactions': ['ObjectId("***REMOVED***")', 'ObjectId("***REMOVED***")']  # transaction IDs
}

transactionsStruct = [
    {
        "_id": 'ObjectId("***REMOVED***")',
        "action": "deposit",
        "amount": 500,
        "dist": {
            "BTC": 0.0123456789,
            "ETH": 0.0123456789,
            "BCH": 0.0123456789,
            "LTC": 0.0123456789
        },
        "nav": 1,
        "portfolio": "moderate",
        "timestamp": 1234567890
    },
    {
        "_id": 'ObjectId("***REMOVED***")',
        "action": "deposit",
        "amount": 500,
        "dist": {
            "BTC": 0.0123456789,
            "ETH": 0.0123456789,
            "BCH": 0.0123456789,
            "LTC": 0.0123456789
        },
        "nav": 1,
        "portfolio": "moderate",
        "timestamp": 1234567890
    },
    {
        "_id": 'ObjectId("***REMOVED***")',
        "action": "deposit",
        "amount": 30,
        "dist": {
            "BTC": 0.0123456789,
            "ETH": 0.0123456789,
            "BCH": 0.0123456789,
            "LTC": 0.0123456789
        },
        "nav": 1,
        "portfolio": "moderate",
        "timestamp": 1234567890
    }
]

tradesStruct = [
    {
        'executedQty': '900.00000000',
        'orderId': 1234,
        'origQty': '900.00000000',
        'side': 'BUY',
        'status': 'FILLED',
        'symbol': 'IOSTETH',
        'time': 1234567890,
        'type': 'MARKET'
    }
]


def main():
    # initialize and load databases
    client = MongoClient()
    db = client.coinaged
    histoPricesDB = db.histoPrices
    usersDB = db.users
    transactionsDB = db.transactions
    tradesDB = db.trades

    # commented for testing
    #
    # # main menu
    # menu = CursesMenu('coinaged.io database manager', 'choose category to interact with')
    #
    # # view portfolio
    # viewPortfolioItem = FunctionItem('view portfolio', getPortfolio, [usersDB, transactionsDB])
    #
    # # user menu
    # userMenu = CursesMenu('coinaged.io database manager', 'users:')
    # viewUserItem = FunctionItem('view', getUserAccount, [usersDB])
    # addUserItem = FunctionItem('add', addUser, [usersDB])
    # removeUserItem = FunctionItem('remove', removeUser, [usersDB])
    # editUserItem = FunctionItem('edit', getUser, [usersDB, transactionsDB])
    #
    # userMenu.append_item(viewUserItem)
    # userMenu.append_item(addUserItem)
    # userMenu.append_item(removeUserItem)
    # userMenu.append_item(editUserItem)
    #
    # userMenuItem = SubmenuItem('users', userMenu, menu)
    #
    # # transactions menu
    # transactionsMenu = CursesMenu('coinaged.io database manager', 'transactions:')
    # addTransactionItem = FunctionItem('add', addTransaction, [usersDB, transactionsDB])
    # removeTransactionItem = FunctionItem('remove', addTransaction, [usersDB, transactionsDB])
    # editTransactionItem = FunctionItem('edit', editTransaction, [usersDB, transactionsDB])
    # cleanTransactionItem = FunctionItem('clean', cleanTransactionsDB, [usersDB, transactionsDB])
    #
    # transactionsMenu.append_item(addTransactionItem)
    # transactionsMenu.append_item(removeTransactionItem)
    # transactionsMenu.append_item(editTransactionItem)
    # transactionsMenu.append_item(cleanTransactionItem)
    #
    # transactionsMenuItem = SubmenuItem('transactions', transactionsMenu, menu)
    #
    # # misc menu
    # miscMenu = CursesMenu('coinaged.io database manager', 'misc:')
    # refreshHistoPricesItem = FunctionItem('update historical prices', updateHourlyPrices, [histoPricesDB])
    #
    # miscMenu.append_item(refreshHistoPricesItem)
    #
    # miscMenuItem = SubmenuItem('misc', miscMenu, menu)
    #
    # # add submenus to main menu
    # menu.append_item(viewPortfolioItem)
    # menu.append_item(userMenuItem)
    # menu.append_item(transactionsMenuItem)
    # menu.append_item(miscMenuItem)
    #
    # menu.show()

    # quick testing
    # getPortfolio(usersDB, transactionsDB, tradesDB)
    getUserAccount(usersDB, transactionsDB, tradesDB, histoPricesDB)

    # pprint(BINANCE_CLIENT.get_all_orders(symbol='NANOBTC', limit=500))

    # editTransaction(usersDB, transactionsDB)
    # getUser(usersDB, transactionsDB)
    # deleteDocs(tradesDB)
    # updateTradeDB(tradesDB, usersDB, getTickers())
    # viewTrades(tradesDB)


#######################
# portfolio functions #
#######################

def getPortfolio(usersDB, transactionsDB, tradesDB, timestamp=int(time())):
    # initial deposit = 1234567890
    # first depost in new acct = 1234567890000
    # timestamp = 1234567890
    # timestamp = 1234567890
    timestamp = 1234567890
    tickers = getTickers()
    tickerPrices = getTickerPrices(tickers, timestamp)
    portfolioPrinciple = getPortfolioPrinciple(transactionsDB, timestamp)
    # updateTradeDB(tradesDB, transactionsDB, tickers)
    portfolioTrades = getPortfolioTrades(tradesDB)
    portfolioBalance = getPortfolioBalance()
    portfolioTransactions = getPortfolioTransactions(transactionsDB)

    # add or subtract past transactions to get historical balance
    portfolioHistoBalance = getPortfolioHistoBalance(portfolioBalance, portfolioTrades, portfolioTransactions, timestamp)

    portfolioValue = getPortfolioValue(portfolioHistoBalance, tickerPrices)
    portfolioValueAggregate = aggregatePortfolioValue(portfolioValue)

    curNav = calculateNav(transactionsDB, portfolioValueAggregate, timestamp)

    print('used time: ' + str(timestamp) + ' (' + str(datetime.utcfromtimestamp(timestamp)) + ')')
    print('portfolio principle: $' + str(int(portfolioPrinciple)))
    print('portfolio value: $' + str(int(portfolioValueAggregate)))
    if(int(portfolioPrinciple) != 0):
        print('overall performance: ' + str(int((portfolioValueAggregate - portfolioPrinciple) / portfolioPrinciple * 100)) + '%')
    print('portfolio nav: ' + str(curNav))


def getPortfolioPrinciple(transactionsDB, timestamp=int(time())):
    principle = 0

    for transaction in transactionsDB.find({}):
        if(int(transaction['timestamp']) < timestamp):
            if(transaction['action'] == 'deposit'):
                principle += int(transaction['amount'])
            elif(transaction['action'] == 'withdrawal'):
                principle -= int(transaction['amount'])

    return principle


def getPortfolioTrades(tradesDB):
    return tradesDB.find()


def getPortfolioTransactions(transactionsDB):
    return transactionsDB.find()


def aggregatePortfolioValue(portfolioValue):
    output = 0
    for value in portfolioValue.values():
        output += value
    return output


def getPortfolioValue(portfolioBalance, prices, time=int(time())):
    portfolioValue = {}

    for ticker, balance in portfolioBalance.items():
        if(balance > 0):
            portfolioValue[ticker] = balance * prices[ticker]

    return portfolioValue


def getPortfolioBalance():
    balance = BINANCE_CLIENT.get_account()

    # hide empty balances / convert to dict
    output = {}
    for balance in balance['balances']:
        if(float(balance['free']) != 0):
            output[balance['asset']] = float(balance['free'])

    return output


# TODO: get historic tickers
def getTickers():
    balance = BINANCE_CLIENT.get_account()

    # hide empty balances / convert to dict
    tickers = []
    for balance in balance['balances']:
        if(float(balance['free']) != 0):
            tickers.append(balance['asset'])

    return tickers


def getTickerPrices(tickers, timestamp=int(time())):
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

    return prices


def getTickerPrice(ticker1, ticker2, timestamp=int(time())):
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
    price = r.json()[ticker1][ticker2]

    return price


def getPortfolioHistoBalance(portfolioBalance, portfolioTrades, portfolioTransactions, timestamp=int(time())):
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
    # print('\ndatabase transactions: \n')
    # for transaction in portfolioTransactions:
    #     if(transaction['timestamp'] > timestamp):
    #         pprint(transaction)
    #         if(transaction['action'] == 'deposit'):
    #             for ticker, val in transaction['dist'].items():
    #                 portfolioBalance[ticker] -= val
    #             # pprint(portfolioBalance)
    #         elif(transaction['action'] == 'withdrawal'):
    #             for ticker, val in transaction['dist'].items():
    #                 portfolioBalance[ticker] += val
    #             # pprint(portfolioBalance)
    #         # pprint(portfolioBalance)

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

    return portfolioBalance


def calculateNav(transactionsDB, currentPortfolioValue, timestamp):
    newestTimestamp = 0
    newestNav = 1
    newestPortfolioValue = 0
    currentPortfolioValue = currentPortfolioValue

    for transaction in transactionsDB.find():
        if(transaction['timestamp'] < timestamp):
            if(transaction['timestamp'] > newestTimestamp):
                newestTimestamp = transaction['timestamp']
                newestNav = transaction['nav']

    for transaction in transactionsDB.find():
        if(transaction['timestamp'] < timestamp):
            if(transaction['action'] == 'deposit'):
                newestPortfolioValue += transaction['amount'] * newestNav

    return newestNav * (currentPortfolioValue / newestPortfolioValue)


#######################
# user menu functions #
#######################

def getUser(usersDB, transactionsDB):
    # refreshOutput()
    print('user list:')
    for user in usersDB.find():
        print(user['firstName'] + ' ' + user['lastName'] + ' | ' + user['email'])

    firstName = input('\nenter user first name: ')
    lastName = input('enter user last name: ')

    selectedUser = usersDB.find_one({'firstName': firstName, 'lastName': lastName})

    # refreshOutput()
    viewUser(selectedUser, transactionsDB)

    return selectedUser


def viewUser(user, transactionsDB):
    print('user id: ' + str(user['_id']))
    print('user first name: ' + user['firstName'])
    print('user last name: ' + user['lastName'])
    print('user email: ' + user['email'])
    print('user phone number: ' + user['phone'])
    print('user transactions: ')
    for transactionId in user['transactions']:
        transaction = getTransaction(transactionsDB, transactionId)
        viewTransaction(transaction)
        print()


def addUser(users):
    firstName = input('first name: ').lower()
    lastName = input('last name: ').lower()
    email = input('email: ').lower()
    phone = input('phone number: ').lower()

    user = {
        'firstName': firstName,
        'lastName': lastName,
        'email': email,
        'phone': phone,
        'transactions': []
    }

    users.insert_one(user)

    # refreshOutput()
    print('user created.\n')


def removeUser(users):
    firstName = input('\nenter user first name: ').lower()
    lastName = input('enter user last name: ').lower()

    selectedUser = users.find_one({'firstName': firstName, 'lastName': lastName})

    print('\ndeleted user: ')
    pprint(selectedUser)

    deleteDocs(users, {'firstName': firstName, 'lastName': lastName})


# TODO: testing
def editUser(usersDB, transactionsDB):
    selectedUser = getUser(usersDB, transactionsDB)

    print('\nenter new fields:')
    firstName = input('\nenter user first name: ')
    lastName = input('enter user last name: ')

    selectedUser = usersDB.find_one({'firstName': firstName, 'lastName': lastName})

    print('\nselected user:')
    pprint(selectedUser)

    firstName = input('first name: ').lower()
    lastName = input('last name: ').lower()
    email = input('email: ').lower()
    phone = input('phone number: ').lower()

    usersDB.update_one(selectedUser, {'$set': {
        'firstName': firstName,
        'lastName': lastName,
        'email': email,
        'phone': phone
    }})

    # refreshOutput()
    print('user updated.\n')


# updated portfolioHistoBalance to now consider the second ticker
def getUserAccount(usersDB, transactionsDB, tradesDB, histoPricesDB, userId, timestamp=int(time())):
    tickers = getTickers()
    tickerPrices = getTickerPrices(tickers, timestamp)
    portfolioPrinciple = getPortfolioPrinciple(transactionsDB, timestamp)
    # updateTradeDB(tradesDB, transactionsDB, tickers)
    portfolioTrades = getPortfolioTrades(tradesDB)
    portfolioBalance = getPortfolioBalance()
    portfolioTransactions = getPortfolioTransactions(transactionsDB)

    # add or subtract past transactions to get historical balance
    portfolioHistoBalance = getPortfolioHistoBalance(portfolioBalance, portfolioTrades, portfolioTransactions, timestamp)

    portfolioValue = getPortfolioValue(portfolioHistoBalance, tickerPrices)
    portfolioValueAggregate = aggregatePortfolioValue(portfolioValue)

    curNav = calculateNav(transactionsDB, portfolioValueAggregate, timestamp)

    users = []
    for user in usersDB.find({'_id': ObjectId(userId)}):
        users.append(user)
    user = users[0]

    userPrinciple = getUserPrinciple(user, transactionsDB, timestamp)
    userValue = getUserValue(user, transactionsDB, userPrinciple, curNav, timestamp)

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
    # test data
    # $100 @ 1
    # $100 @ 2
    # $100 @ 4
    # cur nav: 8
    #
    # 800 + 400 + 200 = 1400

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
    return transactionsDB.find_one({'_id': transactionId})


# cleans up excess of properties unneeded for usecase
def sanitizeTrades(binanceTrades):
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

    return sanitizedTrades


def updateTradeDB(tradesDB, transactionsDB, tickers):
    print('loading newest trades into database...')
    binanceTrades = []

    # cycle tickers to collect binance trades
    for ticker in tickers:
        if(ticker != 'BTC'):
            # if(ticker == 'NANO'):
            #     ticker = 'XRB'
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


########################
# other misc functions #
########################

def refreshOutput():
    if not MUTED:
        os.system('cls' if os.name == 'nt' else 'clear')
        print('|--------------------------------|')
        print('|  coinaged.io database manager  |')
        print('|--------------------------------|')
        print()


def roundToN(x, n):
    return round(x, -int(floor(log10(x))) + (n - 1))


def deleteDocs(db, match={}):
    result = db.delete_many(match)
    print('deleted ' + str(result.deleted_count) + ' documents\n')


# find the average coin value from prev 24hr
def updateHourlyPrices(tickers, histoPrices):
    print('refreshing historical prices...')

    docs = []
    curTime = int(time())
    url = 'https://min-api.cryptocompare.com/data/histohour'

    # form struct (temp)
    params = {
        'fsym': 'ETH',
        'tsym': 'USD',
        'toTs': curTime,
        'limit': 24  # 2000 hours max
    }
    r = requests.get(url=url, params=params)
    for hour in r.json()['Data']:
        docs.append({
            'timestamp': str(hour['time']),
            'data': {}
        })
        # STRUCT[str(TS)] = {}

    for ticker in tickers:
        params = {
            'fsym': ticker,
            'tsym': 'USD',
            'toTs': curTime,
            'limit': 24  # 2000 hours max
        }
        r = requests.get(url=url, params=params)
        # for hour in r.json()['Data']:
        data = r.json()['Data']
        for i in range(0, len(data)):
            OHLC = (data[i]['open'] +
                    data[i]['high'] +
                    data[i]['low'] +
                    data[i]['close']) / 4
            try:
                docs[i]['data'][ticker] = {
                    'price': roundToN(OHLC, 5)
                }
            except:
                pass

    deleteDocs(histoPrices)
    histoPrices.insert_many(docs)

    return docs


def getPortfolioValueBTC(portfolioBalance, prices, time=int(time())):
    portfolioValueBTC = 0
    for i in range(0, len(portfolioBalance)):
        if (portfolioBalance[i]['asset'] == 'BTC'):
            portfolioValueBTC += float(portfolioBalance[i]['free'])
        else:
            portfolioValueBTC += float(portfolioBalance[i]['free']) * float(prices['prices'][portfolioBalance[i]['asset']])

    conversionRate = getBTCUSDRate()

    return portfolioValueBTC
