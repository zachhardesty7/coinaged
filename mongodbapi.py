# future shift to mongo engine
import coinagedPyMongo

from flask import Flask, jsonify
from flask_restful import Resource, Api
from bson.objectid import ObjectId
import json

# from json import dumps
# from flask_jsonify import jsonify
from pymongo import MongoClient
# import requests
# from math import log10, floor
# from time import time
# from binance.client import Client
# import json
# from datetime import datetime

# configs
APP = Flask(__name__)
API = Api(APP)

DEBUG = False
SECRET = json.load(fp='secret.json')
DB_URI = SECRET['database']['uri']
DB_NAME = SECRET['database']['name']
DB_HOST = SECRET['database']['host']
DB_PORT = SECRET['database']['port']
DB_USER = SECRET['database']['user']
DB_PASS = SECRET['database']['pass']

CLIENT = MongoClient(DB_HOST, DB_PORT)
DB = CLIENT[DB_NAME]
DB.authenticate(DB_USER, DB_PASS)

# only use active ones in each route
# histoPricesDB = DB.histoPrices
# usersDB = DB.users
# transactionsDB = DB.transactions
# tradesDB = DB.trades


# TODO: write class / function to handle objectid encode / decode
class Users(Resource):
    def get(self):
        users = []
        for user in DB.users.find():
            user['_id'] = str(user['_id'])
            for i in range(0, len(user['transactions'])):
                user['transactions'][i] = str(user['transactions'][i])
            users.append(user)
        return jsonify(users)


class UsersId(Resource):
    def get(self, userId):
        users = []
        for user in DB.users.find({'_id': ObjectId(userId)}):
            user['_id'] = str(user['_id'])
            for i in range(0, len(user['transactions'])):
                user['transactions'][i] = str(user['transactions'][i])
            users.append(user)
        return jsonify(users)


class UsersPortfolio(Resource):
    def get(self, userId):
        account = coinagedPyMongo.getUserAccount(DB.users, DB.transactions, DB.trades, DB.histoPrices, userId)
        return jsonify(account)


class Transactions(Resource):
    def get(self):
        transactions = []
        for transaction in DB.transactions.find():
            transaction['_id'] = str(transaction['_id'])
            transactions.append(transaction)
        return jsonify(transactions)


class TransactionsId(Resource):
    def get(self, transactionId):
        transaction = coinagedPyMongo.getTransaction(DB.transactions, transactionId)
        return jsonify(transaction)


class Trades(Resource):
    def get(self):
        trades = []
        for trade in DB.trades.find():
            trade['_id'] = str(trade['_id'])
            trades.append(trade)
        return jsonify(trades)


class Portfolio(Resource):
    def get(self):
        portfolio = coinagedPyMongo.getPortfolio(DB.users, DB.transactions, DB.trades)
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
