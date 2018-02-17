
from flask import Flask, request
from flask_restful import Resource, Api
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

# from json import dumps
# from flask_jsonpify import jsonify
# from pymongo import MongoClient
from bson.json_util import loads
from bson.json_util import dumps
# from cursesmenu import CursesMenu, SelectionMenu
# from cursesmenu.items import FunctionItem, SubmenuItem, CommandItem, MenuItem
# from pprint import pprint
import requests
from math import log10, floor
from time import time
from binance.client import Client
import json
import os
from datetime import datetime

# configs
# app.config['MONGO_DBNAME'] = 'coinaged-api'
MONGO_URL = sos.environ.get('MONGO_URL')
if not MONGO_URL:
    MONGO_URL = "mongodb://***REMOVED***:fknc43vtadufaq5ci2dh7qqgps@***REMOVED***:***REMOVED***/***REMOVED***";
app = Flask(__name__)
mongo = PyMongo(app)
app.config['MONGO_URI'] = MONGO_URL
api = Api(app)
# api.representations = DEFAULT_REPRESENTATIONS

# future shift to mongo engine
import coinagedPyMongo
DEBUG = False
SYMS = ['ADA', 'ARK', 'BCC', 'BNB', 'BTC', 'DASH', 'EOS', 'ETH', 'ICX', 'IOTA', 'LSK', 'LTC', 'NEO', 'OMG', 'TRX', 'VEN', 'WTC', 'XLM', 'XMR', 'XRP', 'XVG']
binanceApiKey = '***REMOVED***'
binanceSecret = '***REMOVED***'
# BINANCE_CLIENT = Client(binanceApiKey, binanceSecret)
# client = MongoClient()
# DB = client.coinaged

# only use active ones in each route
# histoPricesDB = mongo.db.histoPrices
# usersDB = mongo.db.users
# transactionsDB = mongo.transactions
# tradesDB = mongo.trades


# TODO: write class / function to handle objectid encode / decode
class Users(Resource):
    def get(self):
        users = []
        for user in mongo.db.users.find():
            user['_id'] = str(user['_id'])
            for i in range(0, len(user['transactions'])):
                user['transactions'][i] = str(user['transactions'][i])
            users.append(user)
        return jsonify(users)


class UsersId(Resource):
    def get(self, userId):
        users = []
        for user in mongo.db.users.find({'_id': ObjectId(userId)}):
            user['_id'] = str(user['_id'])
            for i in range(0, len(user['transactions'])):
                user['transactions'][i] = str(user['transactions'][i])
            users.append(user)
        return jsonify(users)


class UsersAccount(Resource):
    def get(self, userId):
        account = coinagedPyMongo.getUserAccount(mongo.db.users, mongo.db.transactions, mongo.db.trades, mongo.db.histoPrices, userId)
        return jsonify(account)


class Transactions(Resource):
    def get(self):
        transactions = []
        for transaction in mongo.db.transactions.find():
            transaction['_id'] = str(transaction['_id'])
            transactions.append(transaction)
        return jsonify(transactions)


class TransactionsId(Resource):
    def get(self, transactionId):
        transactions = []
        for transaction in mongo.db.transactions.find({'_id': ObjectId(transactionId)}):
            transaction['_id'] = str(transaction['_id'])
            transactions.append(transaction)
        return jsonify(transactions)


class Trades(Resource):
    def get(self):
        trades = []
        for trade in mongo.db.trades.find():
            trade['_id'] = str(trade['_id'])
            trades.append(trade)
        return jsonify(trades)


api.add_resource(Users, '/users')
api.add_resource(UsersId, '/users/<userId>')
api.add_resource(UsersAccount, '/users/<userId>/account')
api.add_resource(Transactions, '/transactions')
api.add_resource(TransactionsId, '/transactions/<transactionId>')
api.add_resource(Trades, '/trades')
# api.add_resource(, '/portfolio')


if __name__ == '__main__':
    app.run()
