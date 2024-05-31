from ..models import  Order,OrderPaymentDetail,ExchangeType,StatusEnum,OrderTypeEnum,TransactionStatusEnum,\
    ExchangeTypeEnum,ExchangeMarket,BackgroundSchedule,JobTask,ArbitrageTrade,WalletType,Account,TransactionStatus,\
    RoundTripOrderDetail,CurrencyType,ArbitrageTradeOrderDetail,WalletTypeEnum,CurrencyTypeSymbolEnum,Wallet


from apscheduler.schedulers.background import BackgroundScheduler
from app import db
from numpy.testing import assert_almost_equal

import  apscheduler
import  sys
import  time
import datetime
import hashlib
import base64,requests, hmac
import hmac
from flask import render_template, redirect, request, url_for, flash, json, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from ..Util.utility import  Utility
import logging


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://venus:venus@localhost/Autopilot'
sql = SQLAlchemy()



def performArbitrageTask():
    with app.app_context():
        sql.init_app(app)
        arbitrage_trade_list=ArbitrageTrade.query.filter_by(withdrawal_status="Pending").all()
 #for withdrawal part
    if arbitrage_trade_list:
        print("==== withdrawal activated======")
        for arbitrage in arbitrage_trade_list:
           if arbitrage.exchange_type_from==ExchangeTypeEnum.BITFINEX.value:
              msg =withdrawBitfinex(arbitrage)
           else:
               #for bittrex=================
               msg=withdrawBittrex(arbitrage)
           if msg:
                continue
#for updating the successful withdrawal
    arbitrage_trade_update_list=ArbitrageTrade.query.filter(ArbitrageTrade.withdrawal_status ==StatusEnum.ACTIVATED.value,ArbitrageTrade.withdrawal_id != None,ArbitrageTrade.order_status == None).all()
    if arbitrage_trade_update_list:
        print("====updating withdrawal activated======")
        for arbitrage in arbitrage_trade_update_list:
            if arbitrage.exchange_type_from == ExchangeTypeEnum.BITFINEX.value:
                msg = updateWithdrawBitfinex(arbitrage)
            else:
                #for bittrex
                msg=updateWithdrawBittrex(arbitrage)
            if msg:
                continue

#place order
    arbitrage_trade_order_detail=ArbitrageTradeOrderDetail.query.filter_by(status=StatusEnum.RUNNING.value).all()
    if arbitrage_trade_order_detail:
        print("====placing arbitrage order======")
        for arbitrage in arbitrage_trade_order_detail:
            if arbitrage.exchange_type == ExchangeTypeEnum.BITFINEX.value:
                msg = placeOrderBitfinex(arbitrage)
            else:
                # for bittrex
                msg = placeOrderBittrex(arbitrage)
            if msg:
                continue



#update order
    arbitrage_trade_order_update_detail =ArbitrageTradeOrderDetail.query.filter_by(status=StatusEnum.ACTIVATED.value).all()
    if arbitrage_trade_order_update_detail:
        print("====update arbitrage order======")
        for arbitrage in arbitrage_trade_order_update_detail:
            if arbitrage.exchange_type == ExchangeTypeEnum.BITFINEX.value:
                msg = updateOrderBitfinex(arbitrage)
            else:
                # for bittrex
                msg = updateOrderBittrex(arbitrage)
            if msg:
                continue




#round trip#withdraw

    round_trip_list=RoundTripOrderDetail.query.filter(RoundTripOrderDetail.status=="Pending").all()
    if round_trip_list:
        print("==== withdrawal activated====== roundtrip")
        for round_trip in round_trip_list:
            if round_trip.exchange_type_from == ExchangeTypeEnum.BITFINEX.value:
                arbitrage_trade=ArbitrageTrade.query.filter_by(ref_number=round_trip.ref_number)
                msg = withdrawBitfinexRoundTrip(round_trip)
            else:
                # for bittrex=================
                msg = withdrawBittrexRoundTrip(round_trip)
            if msg:
                continue

    #for updating the successful withdrawal for roundtrip
    round_trip_order_list = RoundTripOrderDetail.query.filter(
        RoundTripOrderDetail.status == StatusEnum.ACTIVATED.value,RoundTripOrderDetail.withdrawal_id is not None).all()
    if round_trip_order_list:
        print("====updating withdrawal activated======roundtrip")
        for round_trip in arbitrage_trade_update_list:
            if round_trip.exchange_type_from == ExchangeTypeEnum.BITFINEX.value:
                msg = updateWithdrawBitfinexRoundTrip(round_trip)
            else:
                # for bittrex
                msg = updateWithdrawBittrexRoundTrip(round_trip)
            if msg:
                continue


    return True




def updateOrderBitfinex(arbitrage_order_detail=ArbitrageTradeOrderDetail()):
    date_now = time.mktime(datetime.datetime.now().timetuple())
    date = str(date_now).index('.')
    sub_string_date = str(date_now)[0:date]
    nonce = sub_string_date + "000"
    arbitrage_trade = arbitrage_order_detail.arbitrage
    account_to = Account.query.filter_by(user_id=arbitrage_trade.user_id,exchange_type_id=arbitrage_trade.exchange_type_to).first()

    api_key = account_to.api_key
    api_secret_key = bytes(account_to.api_secret_key)
    url = '/v1/order/status'
    nonce = nonce
    completeUrl = 'https://api.bitfinex.com' + url


    body = {'request': url,
            'nonce': nonce,
            'order_id': long(arbitrage_order_detail.uuid)
            }
    jsonifideBody = json.dumps(body)
    payLoad = base64.b64encode(bytes(jsonifideBody))

    signature = hmac.new(key=api_secret_key, msg=payLoad, digestmod=hashlib.sha384).hexdigest()

    headers = {'X-BFX-APIKEY': api_key,
               'X-BFX-PAYLOAD': payLoad,
               'X-BFX-SIGNATURE': signature}
    data = requests.post(completeUrl, headers=headers)
    if data:
        try:
            print(data.content)
            json_object = json.loads(data.content)
            if float(json_object['original_amount'])==float(json_object['executed_amount']):
                arbitrage_order_detail.original_amount = json_object['original_amount']
                arbitrage_order_detail.remaining_amount = json_object['remaining_amount']
                arbitrage_order_detail.executed_amount = json_object['executed_amount']
                arbitrage_order_detail.is_cancelled = json_object['is_cancelled']
                arbitrage_order_detail.is_live = json_object['is_live']
                arbitrage_order_detail.uuid = json_object['id']
                arbitrage_order_detail.status = StatusEnum.COMPLETED.value
                db.session.add(arbitrage_order_detail)
                db.session.commit()
                if checkIfRoundTrip(arbitrage_order_detail.arbitragetrade):
                   try:
                       round_trip=RoundTripOrderDetail()
                       currency_type=CurrencyType.qeury.filter_by(description="USD").first()
                       if TransactionStatusEnum.SELL.value==arbitrage_order_detail.transaction_status:
                            amount_to_transfer=arbitrage_order_detail.arbitragetrade.price*arbitrage_order_detail.original_amount
                       round_trip.crypto_amount=arbitrage_order_detail.original_amount
                       round_trip.price=arbitrage_order_detail.arbitragetrade.price
                       round_trip.exchange_type_from=arbitrage_order_detail.arbitragetrade.exchange_type_to
                       round_trip.exchange_type_to=arbitrage_order_detail.arbitragetrade.exchange_type_from
                       round_trip.user_id=current_user.id
                       round_trip.ref_number=arbitrage_order_detail.order_ref
                       round_trip.date_time=datetime.datetime.now()
                       round_trip.withdrawal_amount=amount_to_transfer
                       round_trip.currency_type=currency_type.id
                       round_trip.status=StatusEnum.RUNNING.value
                       db.session.add(round_trip)
                       db.session.commit()
                   except Exception as e:
                       db.session.rollback()





            if  json_object['is_cancelled']:
                arbitrage_order_detail.is_cancelled = True
                arbitrage_order_detail.is_live = False
                arbitrage_order_detail.status=StatusEnum.CANCELLED.value
                db.session.add(arbitrage_order_detail)
                db.session.commit()

                #send email that order has been cancelled

            return True
        except Exception as e:
            db.session.rollback()
    return False



def checkIfRoundTrip(arbitrage_trade=ArbitrageTrade()):
    if arbitrage_trade.do_round_trip:
        return True
    else:
        return False







def placeOrderBitfinex( arbitrage_order_detail = ArbitrageTradeOrderDetail()):
    date_now = time.mktime(datetime.datetime.now().timetuple())
    date = str(date_now).index('.')
    sub_string_date = str(date_now)[0:date]
    nonce = sub_string_date + "000"
    arbitrage_trade=arbitrage_order_detail.arbitragetrade
    account_to = Account.query.filter_by(user_id=arbitrage_trade.user_id, exchange_type_id=arbitrage_trade.exchange_type_to).first()
    api_key = account_to.account.api_key
    api_secret_key = bytes(account_to.account.api_secret_key)
    url = '/v1/order/new'
    completeUrl = 'https://api.bitfinex.com' + url
    symbol = arbitrage_trade.currencytype.symbol.upper()


    body = {'request': url,
            'nonce': nonce,
            'symbol': symbol +"USD",
            'amount': str(arbitrage_trade.crypto_amount),
            'price': str(arbitrage_trade.price),
            'exchange': arbitrage_order_detail.exchange_type.description.lower(),
            'side': arbitrage_order_detail.transactionstatus.description.lower(),
            'type': ExchangeMarket.EXCHANGELIMIT.value
            }
    jsonifideBody = json.dumps(body)
    payLoad = base64.b64encode(bytes(jsonifideBody))

    signature = hmac.new(key=api_secret_key, msg=payLoad, digestmod=hashlib.sha384).hexdigest()

    headers = {'X-BFX-APIKEY': api_key,
               'X-BFX-PAYLOAD': payLoad,
               'X-BFX-SIGNATURE': signature}
    data = requests.post(completeUrl, headers=headers)
    if data:
        try:
            json_object = json.loads(data.content)
            arbitrage_order_detail.original_amount = json_object['original_amount']
            arbitrage_order_detail.remaining_amount = json_object['remaining_amount']
            arbitrage_order_detail.executed_amount = json_object['executed_amount']
            arbitrage_order_detail.date_time = datetime.datetime.now()
            arbitrage_order_detail.is_cancelled = json_object['is_cancelled']
            arbitrage_order_detail.is_live = json_object['is_live']
            arbitrage_order_detail.uuid = json_object['order_id']
            arbitrage_order_detail.status=StatusEnum.ACTIVATED.value
            db.session.add(arbitrage_order_detail)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
    return  False


def updateWithdrawBitfinex(arbitrage=ArbitrageTrade()):
    try:
        date_now = time.mktime(datetime.datetime.now().timetuple())
        date = str(date_now).index('.')
        sub_string_date = str(date_now)[0:date]
        nonce = sub_string_date + "000"
        current_method = CurrencyType.query.filter_by(id=arbitrage.currency_type).first()
        account_from = Account.query.filter_by(user_id=arbitrage.user_id,exchange_type_id=arbitrage.exchange_type_from).first()
        account_to=Account.query.filter_by(user_id=arbitrage.user_id,exchange_type_id=arbitrage.exchange_type_to).first()

        apiKey = account_from.api_key
        apiSecret = bytes(account_from.api_secret_key)
        baseUrl = 'https://api.bitfinex.com'
        newurl = '/v1/history/movements'
        completUrl = baseUrl + newurl

        bodybalance = {
            'request': newurl,
            'nonce': nonce,
            'currency': current_method.description
        }
        jsonifideBody = json.dumps(bodybalance)
        payLoad = base64.b64encode(bytes(jsonifideBody))
        signaturebalance = hmac.new(key=apiSecret, msg=payLoad, digestmod=hashlib.sha384).hexdigest()
        headers = {'X-BFX-APIKEY': apiKey,
                   'X-BFX-PAYLOAD': payLoad,
                   'X-BFX-SIGNATURE': signaturebalance}
        histories = requests.post(completUrl, headers=headers)
        if histories:
           history_object= json.loads(histories.content)
           for history in history_object:
               if history['status']=="COMPLETED" and history['id']==arbitrage.withdrawal_id:
                   currenct_wallet_balance=checkWithdrawalStatus(current_method.symbol,account_to)
                   if currenct_wallet_balance != "false":
                       wallet=Wallet.query.filter_by(account_id=account_to.id,currency_type=current_method.id,exchange_type_id=account_to.exchange_type_id).first()
                       available_balance=wallet.available_amount
                       available_amount_diffrence=currenct_wallet_balance -available_balance
                       amount_transfered=float(history['amount'])
                       if str(available_amount_diffrence) == str(amount_transfered):
                           pass
                       else:
                           return True
                   try:
                       arbitrage.order_status=StatusEnum.CREATED.value
                       arbitrage.withdrawal_status=StatusEnum.COMPLETED.value
                       db.session.add(arbitrage)
                       db.session.flush()
                       arbitrage_order_detail_trade=ArbitrageTradeOrderDetail()
                       arbitrage_order_detail_trade.date_time=datetime.datetime.now()
                       arbitrage_order_detail_trade.status=StatusEnum.RUNNING.value
                       arbitrage_order_detail_trade.order_ref=arbitrage.ref_number
                       arbitrage_order_detail_trade.is_live=False
                       arbitrage_order_detail_trade.account_id=account_to.id
                       arbitrage_order_detail_trade.exchange_type=arbitrage.exchange_type_to
                       arbitrage_order_detail_trade.transaction_status=arbitrage.transaction_status
                       arbitrage_order_detail_trade.is_cancelled=False
                       arbitrage_order_detail_trade.original_amount=arbitrage.crypto_amount
                       arbitrage_order_detail_trade.arbitrage_trade_id=arbitrage.id
                       db.session.add(arbitrage_order_detail_trade)
                       db.session.commit()
                       return True
                   except Exception as e:
                       db.session.rollback()

    except Exception as e:
        pass

    return False




def withdrawBitfinex(arbitrage=ArbitrageTrade()):

    account_from = Account.query.filter_by(user_id=arbitrage.user_id,exchange_type_id=arbitrage.exchange_type_from).first()
    account_to=Account.query.filter_by(user_id=arbitrage.user_id,exchange_type_id=arbitrage.exchange_type_to).first()
    currency = CurrencyType.query.filter_by(id=arbitrage.currency_type).first()
    date_now = time.mktime(datetime.datetime.now().timetuple())
    date = str(date_now).index('.')
    sub_string_date = str(date_now)[0:date]
    nonce = sub_string_date + "000"
    if arbitrage.exchange_type_to==ExchangeTypeEnum.BITFINEX.value:
        address=depositBitfinex(currency.method,account_to)
    if arbitrage.exchange_type_to==ExchangeTypeEnum.BITTREX.value:
        currency_symbol=arbitrage.currencytype.symbol
        address=depositBittrex(currency_symbol,account_to)
    if address !="false":
        try:
            apiKey = account_from.api_key
            apiSecret = bytes(account_from.api_secret_key)
            baseUrl = 'https://api.bitfinex.com'
            url = '/v1/withdraw'
            completeURL = baseUrl + url
            body = {
                "request": url,
                "withdraw_type": currency.method,
                "walletselected": WalletTypeEnum.EXCHANGE.value,
                "amount": str(arbitrage.crypto_amount),
                "address": address,
                "nonce": nonce
            }
            jsonifideBody = json.dumps(body)
            payload = base64.b64encode(bytes(jsonifideBody))
            signature = hmac.new(key=apiSecret, msg=payload, digestmod=hashlib.sha384).hexdigest()
            header = {
                'X-BFX-APIKEY': apiKey,
                'X-BFX-PAYLOAD': payload,
                'X-BFX-SIGNATURE': signature
            }
            reponse = requests.post(completeURL, headers=header)
            if reponse:
                data = json.loads(reponse.content)
                if data[0]['status'] == 'success':
                    try:
                        arbitrage.withdrawal_id=data[0]['withdrawal_id']
                        arbitrage.withdrawal_status=StatusEnum.ACTIVATED.value
                        db.session.add(arbitrage)
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
                        pass

                    return True

        except Exception as e:
            db.session.rollback()
            return False
    return False


#===================round trip==========================================================
def withdrawBitfinexRoundTrip(round_trip=RoundTripOrderDetail()):
    arbitrage_trade=ArbitrageTrade.query.filter_by(ref_number=round_trip.ref_number).first()
    account_from = Account.query.filter_by(user_id=arbitrage_trade.user_id,exchange_type_id=round_trip.exchange_type_from).first()
    account_to=Account.query.filter_by(user_id=arbitrage_trade.user_id,exchange_type_id=round_trip.exchange_type_to).first()
    currency = CurrencyType.query.filter_by(id=round_trip.currency_type).first()
    date_now = time.mktime(datetime.datetime.now().timetuple())
    date = str(date_now).index('.')
    sub_string_date = str(date_now)[0:date]
    nonce = sub_string_date + "000"
    if round_trip.exchange_type_to==ExchangeTypeEnum.BITFINEX.value:
        address=depositBitfinex(currency.method,account_to)
    if round_trip.exchange_type_to==ExchangeTypeEnum.BITTREX.value:
        address=depositBittrex(round_trip.currencytype.symbol,account_to)
    if address !="false":
        try:

            apiKey = account_from.api_key
            apiSecret = bytes(account_from.api_secret_key)
            baseUrl = 'https://api.bitfinex.com'
            url = '/v1/withdraw'
            completeURL = baseUrl + url
            body = {
                "request": url,
                "withdraw_type": currency.method,
                "walletselected": WalletType.EXCHANGE.value,
                "amount": round_trip.withdrawal_amount,
                "address": address,
                "nonce": nonce
            }
            jsonifideBody = json.dumps(body)
            payload = base64.b64encode(bytes(jsonifideBody))
            signature = hmac.new(key=apiSecret, msg=payload, digestmod=hashlib.sha384).hexdigest()
            header = {
                'X-BFX-APIKEY': apiKey,
                'X-BFX-PAYLOAD': payload,
                'X-BFX-SIGNATURE': signature
            }
            reponse = requests.post(completeURL, headers=header)
            if reponse:
                data = json.loads(reponse.content)
                if data[0]['status'] == 'success':
                    round_trip.withdrawal_id=data[0]['withdrawal_id']
                    round_trip.status=StatusEnum.ACTIVATED.value
                    db.session.add(round_trip)
                    db.session.commit()
        except Exception as e:
            db.session.rollback()
            return False
    return False








def updateWithdrawBitfinexRoundTrip(round_trip=RoundTripOrderDetail()):
    try:
        date_now = time.mktime(datetime.datetime.now().timetuple())
        date = str(date_now).index('.')
        sub_string_date = str(date_now)[0:date]
        nonce = sub_string_date + "000"
        arbitrage_trade = ArbitrageTrade.query.filter_by(ref_number=round_trip.ref_number).first()
        current_method = CurrencyType.query.filter_by(id=round_trip.currency_type).first()
        account_from = Account.query.filter_by(user_id=arbitrage_trade.user_id,exchange_type_id=round_trip.exchange_type_from).first()

        apiKey = account_from.api_key
        apiSecret = bytes(account_from.api_secret_key)
        baseUrl = 'https://api.bitfinex.com'
        newurl = '/v1/history/movements'
        completUrl = baseUrl + newurl

        bodybalance = {
            'request': newurl,
            'nonce': nonce,
            'currency': current_method.description
        }
        jsonifideBody = json.dumps(bodybalance)
        payLoad = base64.b64encode(bytes(jsonifideBody))
        signaturebalance = hmac.new(key=apiSecret, msg=payLoad, digestmod=hashlib.sha384).hexdigest()
        headers = {'X-BFX-APIKEY': apiKey,
                   'X-BFX-PAYLOAD': payLoad,
                   'X-BFX-SIGNATURE': signaturebalance}
        histories = requests.post(completUrl, headers=headers)
        if histories:
           history_object= json.loads(histories.content)
           for history in history_object:
               if history['COMPLETED']=="COMPLETED" and history['id']==round_trip.withdrawal_id:
                   try:
                       round_trip.status=StatusEnum.COMPLETED.value
                       db.session.add(round_trip)
                       db.session.commit()
                       return True
                   except:
                       db.session.rollback()

    except:
        pass

    return False


def depositBitfinex(currency_method,account=Account()):

    date_now = time.mktime(datetime.datetime.now().timetuple())
    date = str(date_now).index('.')
    sub_string_date = str(date_now)[0:date]
    nonce = sub_string_date + "000"
    try:
        apiKey = account.api_key
        apiSecret = bytes(account.api_secret_key)
        baseUrl = 'https://api.bitfinex.com'
        url = '/v1/deposit/new'
        completeURL = baseUrl + url
        body = {
            "request": url,
            "nonce": nonce,
            "method": currency_method,
            "wallet_name": "exchange",
            "renew": 0
        }
        jsonifideBody = json.dumps(body)
        payload = base64.b64encode(bytes(jsonifideBody))

        signature = hmac.new(key=apiSecret, msg=payload, digestmod=hashlib.sha384).hexdigest()

        header = {
            'X-BFX-APIKEY': apiKey,
            'X-BFX-PAYLOAD': payload,
            'X-BFX-SIGNATURE': signature
        }
        data = requests.post(completeURL, headers=header)
        if data:
            data = json.loads(data.content)
            return data['address']
        else:
            return "false"
    except Exception as e:
        return "Error occured! " + e.message
    return  "false"




#=====================Bittrex arbitrage trading=====================================================
def withdrawBittrex(arbitrage=ArbitrageTrade()):
    try:
        account_from = Account.query.filter_by(user_id=arbitrage.user_id,exchange_type_id=arbitrage.exchange_type_from).first()
        account_to = Account.query.filter_by(user_id=arbitrage.user_id,exchange_type_id=arbitrage.exchange_type_to).first()
        currency=arbitrage.currencytype.symbol
        crypto_amount=arbitrage.crypto_amount
        API_KEY=account_from.api_key
        API_SECRET=bytes(account_from.api_secret_key)
        NONCE = str(int(time.time()))
        if arbitrage.exchange_type_to == ExchangeTypeEnum.BITFINEX.value:
            address = depositBitfinex(arbitrage.currencytype.method, account_to)
        if arbitrage.exchange_type_to == ExchangeTypeEnum.BITFINEX.value:
            address = depositBittrex(arbitrage.currencytype.symbol, account_to)
        if address != "false":
            base_url = 'https://bittrex.com/api/v1.1/account/withdraw?apikey='+API_KEY+'&nonce='+NONCE+'&currency='+currency+'&quantity='+crypto_amount+'&address='+address
            signature = hmac.new(API_SECRET, base_url, hashlib.sha512).hexdigest()
            headers = {'apisign': signature}
            response = requests.get(base_url, headers=headers)
            if response:
                data = json.loads(response.content)
                if data['success'] ==True:
                    arbitrage.withdrawal_id = data['result']['uuid']
                    arbitrage.withdrawal_status = StatusEnum.ACTIVATED.value
                    db.session.add(arbitrage)
                    db.session.commit()
                    return True
            else:
                return False
    except Exception as e:
        return "Error occured! "+e.message
    return False




def depositBittrex(currency_symbol,account_to=Account()):
    try:
        API_KEY = account_to.api_key
        API_SECRET=bytes(account_to.api_secret_key)
        NONCE=str(int(time.time()))
        if currency_symbol==CurrencyTypeSymbolEnum.Bittfinex_BCH.value:
            currency_symbol=CurrencyTypeSymbolEnum.Bittrex_BCH.value

        base_url = 'https://bittrex.com/api/v1.1/account/getdepositaddress?apikey='+API_KEY+'&nonce='+NONCE+'&currency='+currency_symbol
        signature = hmac.new(API_SECRET, base_url,hashlib.sha512).hexdigest()
        headers = {'apisign': signature}
        response = requests.get(base_url,headers=headers)
        if response:
            data = json.loads(response.content)
            if data['success']==True:
                return data['result']['Address']
        else:
            return "false"
    except Exception as e:
        return "Error occured! " + e.message
    return "false"


def placeOrderBittrex(arbitrage_order_detail = ArbitrageTradeOrderDetail()):
    try:
        arbitrage_trade = arbitrage_order_detail.arbitragetrade
        account_to = Account.query.filter_by(user_id=arbitrage_trade.user_id,exchange_type_id=arbitrage_trade.exchange_type_to).first()
        API_KEY = account_to.api_key
        API_SECRET = bytes(account_to.api_secret_key)
        NONCE=str(int(time.time()))
        quantity=str(arbitrage_trade.crypto_amount)
        currency_symbol=arbitrage_trade.currencytype.symbol
        if currency_symbol == CurrencyTypeSymbolEnum.Bittfinex_BCH.value:
            currency_symbol = CurrencyTypeSymbolEnum.Bittrex_BCH.value
        rate=str(arbitrage_trade.price)
        base_url = 'https://bittrex.com/api/v1.1/market/selllimit?apikey='+API_KEY+'&nonce='+NONCE+'&market='+'USDT-'+ currency_symbol+'&quantity='+quantity+'&rate='+rate
        signature = hmac.new(API_SECRET, base_url,hashlib.sha512).hexdigest()
        headers = {'apisign': signature}
        response = requests.get(base_url,headers=headers)
        if response:
            data = json.loads(response.content)
            if data['success']==True:
                try:
                    arbitrage_order_detail.uuid = data['result']['uuid']
                    arbitrage_order_detail.date_time = datetime.datetime.now()
                    arbitrage_order_detail.status = StatusEnum.ACTIVATED.value
                    arbitrage_order_detail.is_live=True
                    db.session.add(arbitrage_order_detail)
                    db.session.commit()
                    return True
                except Exception as e :
                    db.session.rollback()
        else:
            return False
    except Exception as e:
        return "Error occured! " + e.message
    return False




def updateOrderBittrex(arbitrage_order_detail = ArbitrageTradeOrderDetail()):
    try:
        arbitrage_trade = arbitrage_order_detail.arbitragetrade
        account_to = Account.query.filter_by(user_id=arbitrage_trade.user_id,exchange_type_id=arbitrage_trade.exchange_type_to).first()
        API_KEY = account_to.api_key
        API_SECRET = bytes(account_to.api_secret_key)
        NONCE=str(int(time.time()))
        base_url = 'https://bittrex.com/api/v1.1/account/getorder?apikey='+API_KEY+'&nonce='+NONCE+'&uuid='+arbitrage_order_detail.uuid
        signature = hmac.new(API_SECRET, base_url,hashlib.sha512).hexdigest()
        headers = {'apisign': signature}
        response = requests.get(base_url,headers=headers)
        if response:
            json_result = json.loads(response.content)
            json_object=json_result['result']
            if json_result['success']==True:
                try:
                    if float(json_object['QuantityRemaining']) == 0:
                        arbitrage_order_detail.original_amount = json_object['Quantity']
                        arbitrage_order_detail.remaining_amount = json_object['QuantityRemaining']
                        # arbitrage_order_detail.executed_amount = json_object['executed_amount']
                        arbitrage_order_detail.is_cancelled = json_object['CancelInitiated']
                        arbitrage_order_detail.is_live = json_object['IsOpen']
                        arbitrage_order_detail.status = StatusEnum.COMPLETED.value
                        db.session.add(arbitrage_order_detail)
                        db.session.commit()
                        if checkIfRoundTrip(arbitrage_order_detail.arbitragetrade):
                            try:
                                round_trip = RoundTripOrderDetail()
                                currency_type = CurrencyType.qeury.filter_by(description="USDT").first()
                                if TransactionStatusEnum.SELL.value == arbitrage_order_detail.transaction_status:
                                    amount_to_transfer = arbitrage_order_detail.arbitragetrade.price * arbitrage_order_detail.original_amount
                                round_trip.crypto_amount = arbitrage_order_detail.original_amount
                                round_trip.price = arbitrage_order_detail.arbitragetrade.price
                                round_trip.exchange_type_from = arbitrage_order_detail.arbitragetrade.exchange_type_to
                                round_trip.exchange_type_to = arbitrage_order_detail.arbitragetrade.exchange_type_from
                                round_trip.user_id = current_user.id
                                round_trip.ref_number = arbitrage_order_detail.order_ref
                                round_trip.date_time = datetime.datetime.now()
                                round_trip.withdrawal_amount = amount_to_transfer
                                round_trip.currency_type = currency_type.id
                                round_trip.status = StatusEnum.RUNNING.value
                                db.session.add(round_trip)
                                db.session.commit()
                            except Exception as e:
                                db.session.rollback()

                    if json_object['CancelInitiated']:
                        arbitrage_order_detail.is_cancelled = True
                        arbitrage_order_detail.is_live = False
                        arbitrage_order_detail.status = StatusEnum.CANCELLED.value
                        db.session.add(arbitrage_order_detail)
                        db.session.commit()
                        # send email that order has been cancelled

                    return True
                except Exception as e:
                    db.session.rollback()
        else:
            return False
    except Exception as e:
        return "Error occured! " + e.message
    return False


def updateWithdrawBittrex(arbitrage_order_detail=ArbitrageTradeOrderDetail()):
    try:
        arbitrage = arbitrage_order_detail.arbitragetrade
        NONCE = str(int(time.time()))
        account_from = Account.query.filter_by(user_id=arbitrage.user_id,exchange_type_id=arbitrage.exchange_type_from).first()
        account_to = Account.query.filter_by(user_id=arbitrage.user_id,exchange_type_id=arbitrage.exchange_type_to).first()
        API_KEY=account_from.api_key

        API_SECRET=bytes(account_from.api_secret_key)
        currency_symbol=arbitrage.currencytype.symbol
        if currency_symbol == CurrencyTypeSymbolEnum.Bittfinex_BCH.value:
            currency_symbol = CurrencyTypeSymbolEnum.Bittrex_BCH.value
        base_url = 'https://bittrex.com/api/v1.1/account/getwithdrawalhistory?currency='+currency_symbol+'apikey='+API_KEY+'&nonce='+NONCE
        signature = hmac.new(API_SECRET, base_url,hashlib.sha512).hexdigest()
        headers = {'apisign': signature}
        response = requests.get(base_url,headers=headers)
        if response:
            history_object = json.loads(response.content)
            for history in history_object['result']:
                if history['Authorized'] == True and history['PendingPayment'] == False and history['PaymentUuid']==arbitrage.withdrawal_id:
                    try:
                        arbitrage.order_status = StatusEnum.CREATED.value
                        arbitrage.withdrawal_status = StatusEnum.COMPLETED.value
                        db.session.add(arbitrage)
                        db.session.flush()

                        arbitrage_order_detail_trade = ArbitrageTradeOrderDetail()
                        arbitrage_order_detail_trade.date_time = datetime.datetime.now()
                        arbitrage_order_detail_trade.status = StatusEnum.RUNNING.value
                        arbitrage_order_detail_trade.order_ref = arbitrage.ref_number
                        arbitrage_order_detail_trade.is_live = False
                        arbitrage_order_detail_trade.account_id = account_to
                        arbitrage_order_detail_trade.exchange_type = arbitrage.exchange_type_to
                        arbitrage_order_detail_trade.transaction_status = arbitrage.transaction_status
                        arbitrage_order_detail_trade.is_cancelled = False
                        arbitrage_order_detail_trade.original_amount = arbitrage.crypto_amount
                        arbitrage_order_detail_trade.arbitrage_trade_id = arbitrage.id
                        db.session.add(arbitrage_order_detail_trade)
                        db.session.commit()
                        return True
                    except:
                        db.session.rollback()
        else:
            return False
    except Exception as e:

        return "Error occured! " + e.message
    return False




#===================Roundtrip bittrex==============================================
def withdrawBittrexRoundTrip(round_trip=RoundTripOrderDetail()):
    try:
        arbitrage_trade = ArbitrageTrade.query.filter_by(ref_number=round_trip.ref_number).first()
        account_from = Account.query.filter_by(user_id=arbitrage_trade.user_id,exchange_type_id=round_trip.exchange_type_from).first()
        account_to = Account.query.filter_by(user_id=arbitrage_trade.user_id,exchange_type_id=round_trip.exchange_type_to).first()
        currency = CurrencyType.query.filter_by(id=round_trip.currency_type).first()
        API_KEY = account_from.api_key
        API_SECRET=account_from.api_secret_key
        crypto_amount=round_trip.withdrawal_amount
        if arbitrage_trade.exchange_type_to == ExchangeTypeEnum.BITFINEX.value:
            address = depositBitfinex(arbitrage_trade.currencytype.method, account_to)
        if arbitrage_trade.exchange_type_to == ExchangeTypeEnum.BITFINEX.value:
            address = depositBittrex(arbitrage_trade.currencytype.symbol, account_to)
        if address != "false":
            base_url = 'https://bittrex.com/api/v1.1/account/withdraw?apikey=' + API_KEY + '&currency=' + currency + '&quantity='+crypto_amount + '&address=' + address
            signature = hmac.new(API_SECRET, base_url, hashlib.sha512).hexdigest()
            headers = {'apisign': signature}
            response = requests.get(base_url, headers=headers)
            if response:
                data = json.loads(response.content)
                if data['success'] == True:
                    round_trip.withdrawal_id = data['result']['uuid']
                    round_trip.status = StatusEnum.ACTIVATED.value
                    db.session.add(round_trip)
                    db.session.commit()
                    return True
            else:
                return False
    except Exception as e:
        return "Error occured! " + e.message
    return False




def updateWithdrawBittrexRoundTrip(round_trip=RoundTripOrderDetail()):
    try:
        arbitrage=ArbitrageTrade.query.filter_by(ref_number=round_trip.ref_number).first()
        NONCE = str(int(time.time()))
        account_from = Account.query.filter_by(user_id=arbitrage.user_id,exchange_type_id=arbitrage.exchange_type_from).first()
        API_KEY = account_from.api_key
        API_SECRET = bytes(account_from.api_secret_key)
        currency_symbol = arbitrage.currencytype.symbol
        if currency_symbol == CurrencyTypeSymbolEnum.Bittfinex_BCH.value:
            currency_symbol = CurrencyTypeSymbolEnum.Bittrex_BCH.value
        base_url = 'https://bittrex.com/api/v1.1/account/getwithdrawalhistory?currency=' + currency_symbol + 'apikey=' + API_KEY + '&nonce=' + NONCE
        signature = hmac.new(API_SECRET, base_url, hashlib.sha512).hexdigest()
        headers = {'apisign': signature}
        response = requests.get(base_url, headers=headers)
        if response:
            history_object = json.loads(response.content)
            for history in history_object['result']:
                if history['Authorized'] == True and history['PendingPayment'] == False and history['PaymentUuid'] == round_trip.withdrawal_id:
                    try:
                        round_trip.status = StatusEnum.COMPLETED.value
                        db.session.add(round_trip)
                        db.session.commit()
                        return True
                    except:
                        db.session.rollback()
        else:
            return False
    except Exception as e:

        return "Error occured! " + e.message
    return False











#====================================check withdrawal status=========================================
def checkWithdrawalStatus(currency_symbol,account_to=Account()):
    try:
        API_KEY = account_to.api_key
        API_SECRET=bytes(account_to.api_secret_key)
        NONCE=str(int(time.time()))
        if currency_symbol==CurrencyTypeSymbolEnum.Bittfinex_BCH.value:
            currency_symbol=CurrencyTypeSymbolEnum.Bittrex_BCH.value

        base_url = 'https://bittrex.com/api/v1.1/account/getbalance?apikey='+API_KEY+'&nonce='+NONCE+'&currency='+currency_symbol
        signature = hmac.new(API_SECRET, base_url,hashlib.sha512).hexdigest()
        headers = {'apisign': signature}
        response = requests.get(base_url,headers=headers)
        if response:
            data = json.loads(response.content)
            if data['success']==True:
                return data['result']['Available']
        else:
            return "false"
    except Exception as e:
        return "Error occured! " + e.message
    return "false"





class ArbitrageLogic:



    def tradeEngine(self):
        scheduler = BackgroundScheduler()
        url = sys.argv[1] if len(sys.argv) > 1 else 'sqlite:///jobs.sqlite'
        scheduler.add_jobstore('sqlalchemy', url=url)
        scheduler.start()
        jobs = scheduler.get_jobs()
        if len(jobs)==0:
            return "Trading has been suspended till further notice"
        msg = False
        for jobObj in jobs:
            if jobObj.id == JobTask.ARBITRAGETASK.value:
                msg = True
                break
        if not msg:
            return "Trading has been suspended till further notice"

        return True




    def removeJob(self, jobScheduler=BackgroundSchedule()):
        scheduler = BackgroundScheduler()
        url = sys.argv[1] if len(sys.argv) > 1 else 'sqlite:///jobs.sqlite'
        scheduler.add_jobstore('sqlalchemy', url=url)
        scheduler.start()
        jobs=scheduler.get_jobs()
        msg=False
        if len(jobs)!=0:
            for jobObj in jobs:
                if jobObj.id==jobScheduler.job:
                    try:
                        scheduler.remove_job(job_id=jobScheduler.job)
                        jobScheduler.status=StatusEnum.STOPPED.value
                        db.session.add(jobScheduler)
                        db.session.commit()
                        msg=True
                        break
                    except Exception as e:
                        db.session.rollback()
        if len(scheduler.get_jobs()) ==0:
            print("=========Backgroundtask closed==============")
            scheduler.shutdown
        return msg




    def addArbitrageJob(self, jobScheduler=BackgroundSchedule()):
        scheduler = BackgroundScheduler()
        url = sys.argv[1] if len(sys.argv) > 1 else 'sqlite:///jobs.sqlite'
        scheduler.add_jobstore('sqlalchemy', url=url)
        if jobScheduler.job ==JobTask.ARBITRAGETASK.value:
            scheduler.add_job(performArbitrageTask, 'interval', seconds=jobScheduler.interval, id=jobScheduler.job)
        scheduler.start()
        jobs=scheduler.get_jobs()
        msg=False
        if len(jobs)!=0:
                try:
                    jobScheduler.status=StatusEnum.ACTIVATED.value
                    db.session.add(jobScheduler)
                    db.session.commit()
                    msg=True
                except Exception as e:
                    db.session.rollback()
        return msg






