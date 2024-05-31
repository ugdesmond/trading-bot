
from flask import render_template, redirect, request, url_for, flash, json, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User, Person,Account, Ticker, CurrencyType,Order,ExchangeTypeUrl,Wallet,CurrencyTypeSymbolEnum
from app.Util.utility import Utility as util
from app import db
import datetime, time
import hashlib
import base64,requests
import hmac
import  time


class Accountlogic:
    #singleton
    def __init__(self):
        pass



    def getAccountDetailForBitfinex(self,apiKey,secreteKey,dateValue,exchangeType):
        nonce = dateValue
        api_key=apiKey
        api_secret_key=bytes(secreteKey)
        url='/v1/balances'

        completeUrl=ExchangeTypeUrl.BITFINEX+url

        body={'request':url,
              'nonce':nonce
              # 'symbol': 'BTCUSD',
              # 'amount': order.currency_amount,
              # 'price': order.price,
              # 'exchange':order.exchange_type.description.lower(),
              # 'side': order.transaction_status,
              # 'type': 'exchange market'
              }
        jsonifideBody=json.dumps(body)
        payLoad=base64.b64encode(bytes(jsonifideBody))

        signature = hmac.new(key=api_secret_key,msg=payLoad, digestmod=hashlib.sha384).hexdigest()

        headers = {'X-BFX-APIKEY': api_key,
                   'X-BFX-PAYLOAD':payLoad,
                   'X-BFX-SIGNATURE':signature}
        data = requests.post(completeUrl,headers=headers)
        if data:
            print(data.content)
            json_object = json.loads(data.content)
            try:
                account = Account()
                account.api_key = apiKey
                account.user_id = current_user.id
                account.api_secret_key = secreteKey
                account.exchange_type_id = exchangeType
                db.session.add(account)
                db.session.flush()
                for walletObject in json_object:
                    wallet = Wallet()
                    currency = walletObject['currency']
                    wallet.total_amount = walletObject['amount']
                    wallet.available_amount = walletObject['available']
                    wallet.exchange_type_id = exchangeType
                    wallet.account_id = account.id
                    currencyType = CurrencyType.query.filter_by(symbol=currency.upper()).first()
                    wallet.currency_type = currencyType.id
                    db.session.add(wallet)
                    db.session.commit()
            except Exception as e:
                raise e.message
            return True
        else:

            return False

    def updateAccountDetailForBitfinex(self, apiKey, secreteKey, dateValue, exchangeType, accountUser=Account()):
        date_now = time.mktime(datetime.datetime.now().timetuple())
        date = str(date_now).index('.')
        sub_string_date = str(date_now)[0:date]
        nonce = sub_string_date + "000"
        api_key = apiKey
        api_secret_key = bytes(secreteKey)
        url = '/v1/balances'

        completeUrl = ExchangeTypeUrl.BITFINEX.value + url

        body = {'request': url,
                'nonce': nonce
                # 'symbol': 'BTCUSD',
                # 'amount': order.currency_amount,
                # 'price': order.price,
                # 'exchange':order.exchange_type.description.lower(),
                # 'side': order.transaction_status,
                # 'type': 'exchange market'
                }
        jsonifideBody = json.dumps(body)
        payLoad = base64.b64encode(bytes(jsonifideBody))

        signature = hmac.new(key=api_secret_key, msg=payLoad, digestmod=hashlib.sha384).hexdigest()

        headers = {'X-BFX-APIKEY': api_key,
                   'X-BFX-PAYLOAD': payLoad,
                   'X-BFX-SIGNATURE': signature}
        data = requests.post(completeUrl, headers=headers)
        if data:
            print(data.content)
            json_object = json.loads(data.content)
            try:
                for wallet_currency in json_object:
                    currency = wallet_currency['currency']
                    currencyType = CurrencyType.query.filter_by(symbol=currency.upper()).first()
                    wallet=Wallet.query.filter_by(account_id=accountUser.id,currency_type=currencyType.id).first()
                    if currencyType is not None and wallet is not None:
                        currency = wallet_currency['currency']
                        wallet.total_amount = wallet_currency['amount']
                        wallet.available_amount = wallet_currency['available']
                        wallet.exchange_type_id = exchangeType
                        wallet.account_id = accountUser.id
                        currencyType = CurrencyType.query.filter_by(symbol=currency.upper()).first()
                        wallet.currency_type = currencyType.id
                        db.session.add(wallet)
                        db.session.commit()
                    if currencyType is not None and wallet is None:
                        currency = wallet_currency['currency']
                        wallet.total_amount = wallet_currency['amount']
                        wallet.available_amount = wallet_currency['available']
                        wallet.exchange_type_id = exchangeType
                        wallet.account_id = accountUser.id
                        currencyType = CurrencyType.query.filter_by(symbol=currency.upper()).first()
                        wallet.currency_type = currencyType.id
                        db.session.add(wallet)
                        db.session.commit()
            except Exception as e:
                db.session.rollback()
                pass
            return "true"
        else:
            json_object = json.loads(data.content)
            return json_object['message']

    def updateAccountForBittrex(self,apiKey,secreteKey,exchangeType,accountUser=Account()):
            try:
                NONCE = str(int(time.time()))
                API_KEY = apiKey
                API_SECRET = bytes(secreteKey)

                base_url = 'https://bittrex.com/api/v1.1/account/getbalances?apikey='+ API_KEY + '&nonce=' + NONCE
                signature = hmac.new(API_SECRET, base_url, hashlib.sha512).hexdigest()
                headers = {'apisign': signature}
                response = requests.get(base_url, headers=headers)
                if response:
                    json_object = json.loads(response.content)
                    print(response.content)
                    try:
                        for wallet_currency in json_object['result']:
                            currency = wallet_currency['Currency']
                            if currency == CurrencyTypeSymbolEnum.Bittrex_BCH.value:
                                currency = CurrencyTypeSymbolEnum.Bittfinex_BCH.value
                            currencyType = CurrencyType.query.filter_by(symbol=currency.upper()).first()
                            wallet = Wallet.query.filter_by(account_id=accountUser.id, currency_type=currencyType.id).first()
                            if currencyType is not None and wallet is not None:

                                    wallet.total_amount = wallet_currency['Balance']
                                    wallet.available_amount = wallet_currency['Available']
                                    wallet.exchange_type_id = exchangeType
                                    wallet.account_id = accountUser.id
                                    currencyType = currencyType
                                    wallet.currency_type = currencyType.id
                                    db.session.add(wallet)
                                    db.session.flush()

                            if currencyType is not None and wallet is None:

                                    wallet = Wallet()
                                    wallet.total_amount = wallet_currency['Balance']
                                    wallet.available_amount = wallet_currency['Available']
                                    wallet.exchange_type_id = exchangeType
                                    wallet.account_id = accountUser.id
                                    currencyType = currencyType
                                    wallet.currency_type = currencyType.id
                                    db.session.add(wallet)
                                    db.session.flush()

                            db.session.commit()
                            walletList = Wallet.query.filter_by(exchange_type_id=ExchangeTypeUrl.BITFINEX.value)
                            return walletList
                    except Exception as e:
                        db.session.rollback()
                        pass
                else:
                    return 'False'

            except Exception as e:
                pass

