
from flask import render_template, redirect, request, url_for, flash, json, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from ..Util .ModelSchema import OrderValueType
from ..models import User,OrderTypeEnum,CurrencyTypeSymbolEnum,TransactionStatusEnum,ExchangeType,Order, Person,Account,CurrencyMarket, Ticker, CurrencyType,Order,ExchangeTypeUrl,Wallet,OrderPaymentDetail,StatusEnum,ExchangeTypeEnum
from app.Util.utility import Utility as util
from app import db
import datetime
import hashlib
import base64,requests
import hmac
from operator import itemgetter, attrgetter, methodcaller
import time

class BittrexOrder:
    #singleton
    def __init__(self):
        pass


    def CancelOrderBittrex(self,dateValue,orderPaymentDetail=OrderPaymentDetail()):
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
    def getOrderHistoryBittrex(self,bitfinex_order_list,account=Account()):
        NONCE = str(int(time.time()))
        API_KEY = account.api_key
        API_SECRET = bytes(account.api_secret_key)
        base_url = 'https://bittrex.com/api/v1.1/account/getorderhistory?apikey=' + API_KEY + '&nonce=' + NONCE
        signature = hmac.new(API_SECRET, base_url, hashlib.sha512).hexdigest()
        headers = {'apisign': signature}
        data = requests.get(base_url, headers=headers)

        if data:
            try:
                orderList = Order.query.filter_by(account_id=account.id,order_type = OrderTypeEnum.SINGLE.value).order_by(Order.date_time).all()
                content = json.loads(data.content)
                json_object=content['result']
                print("======",json_object)



                for orderObject in orderList:
                   orderPaymentDetail=OrderPaymentDetail.query.filter_by(order_id=orderObject.id,uuid=None,order_type=OrderTypeEnum.SINGLE.value).first()
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
                    if bitfinex_order_list is None:
                        bitfinex_order_list=[]
                    bitfinex_order_list.append(orderObj1)

                for order in json_object:
                    orderObj= OrderValueType()
                    orderPamentDetail=OrderPaymentDetail.query.filter_by(uuid=str(order['OrderUuid']), order_type = OrderTypeEnum.SINGLE.value).first()
                    if orderPamentDetail is   None:
                        orderObj.currency_amount = order['Quantity']
                        orderObj.date_time=order['TimeStamp']
                        orderObj.order_ref="-------"
                        orderObj.transaction_status=order['OrderType']
                        orderObj.status=''
                        if float(order['QuantityRemaining'])!=0:
                            orderObj.status=StatusEnum.RUNNING.value
                        if order['ImmediateOrCancel'] :
                            orderObj.status=StatusEnum.CANCELLED.value
                        if float(order['QuantityRemaining'])==0:
                            orderObj.status=StatusEnum.COMPLETED.value

                        orderObj.price_to_pay=order['Price']
                        orderObj.id=order['OrderUuid']
                        symbol=(order['Exchange']).replace("-","")
                        currencyMarket =CurrencyMarket.query.filter_by(symbol=symbol.lower()).first()
                        orderObj.markettype =order['Exchange']
                        orderObj.currencytype =order['Exchange']
                        if currencyMarket is not None:
                            orderObj.markettype=currencyMarket.markettype.description
                            orderObj.currencytype=currencyMarket.currencytype.description
                        orderObj.exchangetype=ExchangeTypeEnum.BITTREXVALUE.value
                        bitfinex_order_list.append(orderObj)

                list.sort(bitfinex_order_list, key=attrgetter('date_time'), reverse=True)
                sorted_overall_list=[]
                for order_filter in bitfinex_order_list:
                    if order_filter.status != StatusEnum.COMPLETED.value or order_filter.status is None:
                        sorted_overall_list.append(order_filter)


                return sorted_overall_list
            except Exception as e:
                pass
        else:
            return None


#update order payment detial for bittrex not yet implemented
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




