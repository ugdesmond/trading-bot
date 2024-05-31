
from flask import render_template, redirect, request, url_for, flash, json, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from ..Util .ModelSchema import OrderValueType
from ..models import User,OrderTypeEnum,ExchangeType,Order, Person,Account,CurrencyMarket, Ticker, CurrencyType,Order,ExchangeTypeUrl,Wallet,OrderPaymentDetail,StatusEnum
from app.Util.utility import Utility as util
from app import db
import datetime
import hashlib
import base64,requests
import hmac
from operator import itemgetter, attrgetter, methodcaller
import time

class BitfinexOrder:
    #singleton
    def __init__(self):
        pass


    def CancelOrderBitfinex(self,dateValue,orderPaymentDetail=OrderPaymentDetail()):
        nonce = dateValue
        api_key=orderPaymentDetail.orders.account.api_key
        api_secret_key=bytes(orderPaymentDetail.orders.account.api_secret_key)
        url='/v1/order/cancel'
        completeUrl=ExchangeTypeUrl.BITFINEX.value+url

        body={'request':url,
              'nonce':nonce,
              'order_id': long(orderPaymentDetail.uuid)
              }
        jsonifideBody=json.dumps(body)
        payLoad=base64.b64encode(bytes(jsonifideBody))

        signature = hmac.new(key=api_secret_key,msg=payLoad, digestmod=hashlib.sha384).hexdigest()

        headers = {'X-BFX-APIKEY': api_key,
                   'X-BFX-PAYLOAD':payLoad,
                   'X-BFX-SIGNATURE':signature}
        data = requests.post(completeUrl,headers=headers)
        if data:
            try:
                print(data.content)
                json_object = json.loads(data.content)
                order=orderPaymentDetail.orders
                order.status = StatusEnum.CANCELLED.value
                db.session.add(order)
                db.session.flush()

                orderPaymentDetail = OrderPaymentDetail.query.filter_by(order_id=order.id).first()
                orderPaymentDetail.original_amount = json_object['original_amount']
                orderPaymentDetail.remaining_amount = json_object['remaining_amount']
                orderPaymentDetail.executed_amount = json_object['executed_amount']
                orderPaymentDetail.date_time = datetime.datetime.now()
                orderPaymentDetail.is_cancelled = True
                orderPaymentDetail.is_live = False
                db.session.add(orderPaymentDetail)
                db.session.commit()
                return "Cancelled Successfully"
            except Exception as e:
                db.session.rollback()
        else:
            json_object = json.loads(data.content)
            return json_object['message']


    def CancelUnsavedOrderBitfinex(self,dateValue,orderId,account=Account()):
        nonce = dateValue
        api_key=account.api_key
        api_secret_key=bytes(account.api_secret_key)
        url='/v1/order/cancel'
        completeUrl=ExchangeTypeUrl.BITFINEX.value+url

        body={'request':url,
              'nonce':nonce,
              'order_id': long(orderId)
              }
        jsonifideBody=json.dumps(body)
        payLoad=base64.b64encode(bytes(jsonifideBody))

        signature = hmac.new(key=api_secret_key,msg=payLoad, digestmod=hashlib.sha384).hexdigest()

        headers = {'X-BFX-APIKEY': api_key,
                   'X-BFX-PAYLOAD':payLoad,
                   'X-BFX-SIGNATURE':signature}
        data = requests.post(completeUrl,headers=headers)
        if data:
            try:
                print(data.content)
                return "Cancelled Successfully"
            except Exception as e:
                raise e.message
        else:
            json_object = json.loads(data.content)
            return json_object['message']

#for single==================================
    def getOrderHistoryBitfinex(self,dateValue,account=Account()):
        nonce = dateValue
        api_key = account.api_key
        api_secret_key = bytes(account.api_secret_key)
        url = '/v1/orders'
        completeUrl = ExchangeTypeUrl.BITFINEX.value + url

        body = {'request': url,
                'nonce': nonce
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


                orderList = Order.query.filter_by(account_id=account.id,order_type = OrderTypeEnum.SINGLE.value).order_by(Order.date_time).all()
                json_object = json.loads(data.content)
                OrderValueTypeList=[]


                for orderObject in orderList:
                    orderPaymentDetail=OrderPaymentDetail.query.filter_by(uuid=None,order_id=orderObject.id,order_type=OrderTypeEnum.SINGLE.value).first()
                    if orderPaymentDetail is not None:
                        updateOrderPaymentDetail(orderPaymentDetail)
                orderList = Order.query.filter_by(account_id=account.id, order_type=OrderTypeEnum.SINGLE.value).order_by(
                    Order.date_time).all()
                for orderMain in orderList:
                    orderObj1 = OrderValueType()
                    date=str(orderMain.date_time).index(':')
                    dateVal=long(date)-2
                    subStringDate=str(orderMain.date_time)[0:dateVal]
                    orderObj1.exchangetype=orderMain.exchange_type.description
                    orderObj1.price_to_pay=orderMain.price_to_pay
                    orderObj1.transaction_status=orderMain.transactionstatus.description
                    orderObj1.status=orderMain.status
                    orderObj1.date_time=subStringDate
                    orderObj1.id=orderMain.id
                    orderObj1.currency_amount=orderMain.currency_amount
                    orderObj1.currencytype=orderMain.currencytype.description
                    orderObj1.markettype=orderMain.markettype.description
                    orderObj1.order_ref=orderMain.order_ref
                    OrderValueTypeList.append(orderObj1)

                for order in json_object:
                    orderObj= OrderValueType()
                    orderPamentDetail=OrderPaymentDetail.query.filter_by(uuid=str(order['id']), order_type = OrderTypeEnum.SINGLE.value).first()
                    if orderPamentDetail is   None:
                        orderObj.currency_amount = order['price']
                        orderObj.date_time=order['cid_date']
                        orderObj.order_ref="-------"
                        orderObj.transaction_status=order['side']
                        orderObj.status=''
                        if order['is_live']:
                            orderObj.status=StatusEnum.RUNNING.value
                        if order['is_cancelled'] :
                            orderObj.status=StatusEnum.CANCELLED.value
                        if float(order['original_amount'])==float(order['executed_amount']):
                            orderObj.status=StatusEnum.COMPLETED.value

                        orderObj.price_to_pay=order['original_amount']
                        orderObj.id=order['id']

                        currencyMarket =CurrencyMarket.query.filter_by(symbol=order['symbol']).first()
                        orderObj.markettype =order['symbol']
                        orderObj.currencytype =order['symbol']
                        if currencyMarket is not None:
                            orderObj.markettype=currencyMarket.markettype.description
                            orderObj.currencytype=currencyMarket.currencytype.description
                        orderObj.exchangetype=order['exchange']
                        OrderValueTypeList.append(orderObj)

                list.sort(OrderValueTypeList, key=attrgetter('date_time'), reverse=True)

                return OrderValueTypeList
            except Exception as e:
                pass
        else:
            return None

#========pending task=====
def updateOrderPaymentDetail(orderPaymentDetail=OrderPaymentDetail()):
    date_now = time.mktime(datetime.datetime.now().timetuple())
    date = str(date_now).index('.')
    sub_string_date = str(date_now)[0:date]
    nonce = sub_string_date + "000"
    order = orderPaymentDetail.orders
    api_key = order.account.api_key
    api_secret_key = bytes(order.account.api_secret_key)
    url = '/v1/order/status'
    nonce = nonce
    completeUrl = 'https://api.bitfinex.com' + url


    body = {'request': url,
            'nonce': nonce,
            'order_id': long(orderPaymentDetail.uuid)
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
                orderPaymentDetail.original_amount = json_object['original_amount']
                orderPaymentDetail.remaining_amount = json_object['remaining_amount']
                orderPaymentDetail.executed_amount = json_object['executed_amount']
                orderPaymentDetail.is_cancelled = json_object['is_cancelled']
                orderPaymentDetail.is_live = json_object['is_live']
                orderPaymentDetail.uuid = json_object['id']
                db.session.add(orderPaymentDetail)
                db.session.commit()

            if  json_object['is_cancelled']:
                orderPaymentDetail.is_cancelled = True
                orderPaymentDetail.is_live = False
                orderPaymentDetail.status=StatusEnum.CANCELLED.value
                db.session.add(orderPaymentDetail)
                db.session.commit()

            return True
        except Exception as e:
            db.session.rollback()
    return False
