# TODO: speed up nav calculation using cached value of most recently called nav and current nav
# TODO: write class / function to handle objectid encode / decode
# future shift to mongo engine
import coinagedPyMongo

from flask import Flask, jsonify, request
from flask_restful import Resource, Api
from flask_cors import CORS
from bson.objectid import ObjectId
from pymongo import MongoClient
import os
import logging
from time import time

# configs
app = Flask(__name__)
CORS(app)
api = Api(app)

INFO = True
MONGODB_URI = os.environ['MONGODB_URI']
MONGODB_NAME = os.environ['MONGODB_NAME']
MONGODB_HOST = os.environ['MONGODB_HOST']
MONGODB_PORT = int(os.environ['MONGODB_PORT'])
MONGODB_USER = os.environ['MONGODB_USER']
MONGODB_PASS = os.environ['MONGODB_PASS']

CLIENT = MongoClient(MONGODB_HOST, MONGODB_PORT)
DB = CLIENT[MONGODB_NAME]
DB.authenticate(MONGODB_USER, MONGODB_PASS)

if INFO:
    logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


# @RETURNS: list of users
#
# @METHOD: GET
# @URL: http://api.coinaged.com/users
class Users(Resource):
    def get(self):
        start = time()
        users = []
        for user in DB.users.find():
            user['_id'] = str(user['_id'])
            for i in range(0, len(user['transactions'])):
                user['transactions'][i] = str(user['transactions'][i])
            users.append(user)
        LOGGER.info(self.__class__.__name__ + ': took ' + str(time() - start) +
                    ' seconds')
        return jsonify(users)


# @RETURNS: single user's details
#
# @METHOD: GET
# @URL: http://api.coinaged.com/users/{userId}
class UsersId(Resource):
    def get(self, userId):
        start = time()
        users = []

        for user in DB.users.find({'_id': ObjectId(userId)}):
            user['_id'] = str(user['_id'])
            for i in range(0, len(user['transactions'])):
                user['transactions'][i] = str(user['transactions'][i])
            users.append(user)

        LOGGER.info(self.__class__.__name__ + ': took ' + str(time() - start) +
                    ' seconds')
        return jsonify(users)


# @RETURNS: single user's portfolio
#
# @METHOD: GET
# @URL: http://api.coinaged.com/users/{userId}/portfolio
class UsersPortfolio(Resource):
    def get(self, userId):
        start = time()

        account = coinagedPyMongo.getUserAccount(
            DB.users, DB.transactions, DB.trades, DB.histoPrices, userId)

        LOGGER.info(self.__class__.__name__ + ': took ' + str(time() - start) +
                    ' seconds')
        return jsonify(account)


# @RETURNS: all transactions
#
# @METHOD: GET
# @URL: http://api.coinaged.com/transactions
class Transactions(Resource):
    def get(self):
        start = time()
        transactions = []

        for transaction in DB.transactions.find():
            transaction['_id'] = str(transaction['_id'])
            transactions.append(transaction)

        LOGGER.info(self.__class__.__name__ + ': took ' + str(time() - start) +
                    ' seconds')
        return jsonify(transactions)


# @RETURNS: single transaction's details
#
# @METHOD: GET
# @URL: http://api.coinaged.com/transactions/{transactionId}
class TransactionsId(Resource):
    def get(self, transactionId):
        start = time()

        transaction = coinagedPyMongo.getTransaction(DB.transactions,
                                                     transactionId)

        LOGGER.info(self.__class__.__name__ + ': took ' + str(time() - start) +
                    ' seconds')
        return jsonify(transaction)


# @RETURNS: all trades
#
# @METHOD: GET
# @URL: http://api.coinaged.com/trades
class Trades(Resource):
    def get(self):
        start = time()
        trades = []

        for trade in DB.trades.find():
            trade['_id'] = str(trade['_id'])
            trades.append(trade)

        LOGGER.info(self.__class__.__name__ + ': took ' + str(time() - start) +
                    ' seconds')
        return jsonify(trades)


# @RETURNS: overall portfolio performance
#
# @METHOD: GET
# @URL: http://api.coinaged.com/portfolio
class Portfolio(Resource):
    def get(self):
        start = time()

        portfolio = coinagedPyMongo.getPortfolio(DB.users, DB.transactions,
                                                 DB.trades)

        LOGGER.info(self.__class__.__name__ + ': took ' + str(time() - start) +
                    ' seconds')
        return jsonify(portfolio)


# @RETURNS: overall portfolio performance
#
# @METHOD: GET
# @URL: http://api.coinaged.com/portfolio/1day
class PortfolioHistorical(Resource):
    def get(self):
        start = time()

        # supports 'day', 'hour', 'minute'
        interval = request.args.get('interval', default='hour', type=str)
        aggregate = request.args.get('aggregate', default=1, type=int)
        limit = request.args.get('limit', default=24, type=int)

        portfolio = coinagedPyMongo.getPortfolioHisto(
            DB.users, DB.transactions, DB.trades, interval, aggregate, limit)

        LOGGER.info(self.__class__.__name__ + ': took ' + str(time() - start) +
                    ' seconds')
        return jsonify(portfolio)


api.add_resource(Users, '/users')
api.add_resource(UsersId, '/users/<userId>')
api.add_resource(UsersPortfolio, '/users/<userId>/portfolio')
api.add_resource(Transactions, '/transactions')
api.add_resource(TransactionsId, '/transactions/<transactionId>')
api.add_resource(Trades, '/trades')
api.add_resource(Portfolio, '/portfolio')
api.add_resource(PortfolioHistorical, '/portfolio/historical')

if __name__ == '__main__':
    app.run()
