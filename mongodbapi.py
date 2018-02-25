# TODO: speed up nav calculation using cached value of most recently called nav and current nav
# TODO: write class / function to handle objectid encode / decode
# future shift to mongo engine
import coinagedPyMongo

from flask import Flask, jsonify
from flask_restful import Resource, Api
from bson.objectid import ObjectId
from pymongo import MongoClient
import os
from time import time

# configs
APP = Flask(__name__)
API = Api(APP)

DEBUG = False
MONGODB_URI = os.environ['MONGODB_URI']
MONGODB_NAME = os.environ['MONGODB_NAME']
MONGODB_HOST = os.environ['MONGODB_HOST']
MONGODB_PORT = int(os.environ['MONGODB_PORT'])
MONGODB_USER = os.environ['MONGODB_USER']
MONGODB_PASS = os.environ['MONGODB_PASS']

CLIENT = MongoClient(MONGODB_HOST, MONGODB_PORT)
DB = CLIENT[MONGODB_NAME]
DB.authenticate(MONGODB_USER, MONGODB_PASS)


# @RETURNS: list of users
#
# @METHOD: GET
# @URL: http://api.coinaged.com/users
class Users(Resource):
    def get(self):
        users = []
        for user in DB.users.find():
            user['_id'] = str(user['_id'])
            for i in range(0, len(user['transactions'])):
                user['transactions'][i] = str(user['transactions'][i])
            users.append(user)
        return jsonify(users)


# @RETURNS: single user's details
#
# @METHOD: GET
# @URL: http://api.coinaged.com/users/{userId}
class UsersId(Resource):
    def get(self, userId):
        users = []
        for user in DB.users.find({'_id': ObjectId(userId)}):
            user['_id'] = str(user['_id'])
            for i in range(0, len(user['transactions'])):
                user['transactions'][i] = str(user['transactions'][i])
            users.append(user)
        return jsonify(users)


# @RETURNS: single user's portfolio
#
# @METHOD: GET
# @URL: http://api.coinaged.com/users/{userId}/portfolio
class UsersPortfolio(Resource):
    def get(self, userId):
        account = coinagedPyMongo.getUserAccount(DB.users, DB.transactions, DB.trades, DB.histoPrices, userId)
        return jsonify(account)


# @RETURNS: all transactions
#
# @METHOD: GET
# @URL: http://api.coinaged.com/transactions
class Transactions(Resource):
    def get(self):
        transactions = []
        for transaction in DB.transactions.find():
            transaction['_id'] = str(transaction['_id'])
            transactions.append(transaction)
        return jsonify(transactions)


# @RETURNS: single transaction's details
#
# @METHOD: GET
# @URL: http://api.coinaged.com/transactions/{transactionId}
class TransactionsId(Resource):
    def get(self, transactionId):
        transaction = coinagedPyMongo.getTransaction(DB.transactions, transactionId)
        return jsonify(transaction)


# @RETURNS: all trades
#
# @METHOD: GET
# @URL: http://api.coinaged.com/trades
class Trades(Resource):
    def get(self):
        trades = []
        for trade in DB.trades.find():
            trade['_id'] = str(trade['_id'])
            trades.append(trade)
        return jsonify(trades)


# @RETURNS: overall portfolio performance
#
# @METHOD: GET
# @URL: http://api.coinaged.com/portfolio
class Portfolio(Resource):
    def get(self):
        portfolio = coinagedPyMongo.getPortfolio(DB.users, DB.transactions, DB.trades, int(time()))
        return jsonify(portfolio)


API.add_resource(Users, '/users')
API.add_resource(UsersId, '/users/<userId>')
API.add_resource(UsersPortfolio, '/users/<userId>/portfolio')
API.add_resource(Transactions, '/transactions')
API.add_resource(TransactionsId, '/transactions/<transactionId>')
API.add_resource(Trades, '/trades')
API.add_resource(Portfolio, '/portfolio')


if __name__ == '__main__':
    APP.run()
