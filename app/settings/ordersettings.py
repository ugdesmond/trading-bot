from flask import render_template, redirect, request, url_for, flash, json, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import settings
from ..models import User, Person,Account, Ticker,Wallet,Order,StatusEnum,\
    ExchangeType,ExchangeTypeEnum,JobStatus,CurrencyMarket,OrderTypeEnum,OrderPaymentDetail,TransactionStatusEnum,ExchangeMarket,CurrencyType
from app.Util.utility import Utility as util
from app.Util.ModelSchema import WalletSchema,TickerSchema,ExchangeTypeSchema,CurrencyMarketSchema
from ..BitfinanceBuisnessLogic.trade import BitfinexTradeLogic
from..BittrexBuisnessLogic.trade import  BittrexTradeLogic
from..BuisnessLogic.AccountLogic import Accountlogic
from..BuisnessLogic.BitfinexOrderLogic import BitfinexOrder
from ..BuisnessLogic.BittrexOrderLogic import BittrexOrder
from app import db
import datetime
import os


@settings.route('/ordersettings', methods=['GET'])
def orderSettings():
    exchange_type_list=util.exchange_type_dropdown_list()
    market_type_list=util.get_market_type_from_ticker()


    return render_template('auth/admin/order.html',exchange_type_list=exchange_type_list,market_type_list=market_type_list)


@settings.route('/ordersettings/getwallet', methods=['POST'])
def getWallet():
    try:
        exchange_type_id=request.form['exchangeTypeId']
        account = Account.query.filter_by(user_id=current_user.id,exchange_type_id=exchange_type_id).first()
        wallet_json= Wallet()
        if account is not None:
            walletSchema=WalletSchema()
            wallet=Wallet.query.filter_by(account_id=account.id,exchange_type_id=exchange_type_id).order_by(Wallet.id).all()
            wallet_json = json.dumps(walletSchema.dumps(wallet,True))


        return wallet_json
    except BaseException as e:
        raise e.message

@settings.route('/ordersettings/getticker', methods=['POST'])
def getTicker():
    try:
        exchange_type_id = request.form['marketTypeId']
        walletId=request.form['wallet']
        wallet=Wallet.query.filter_by(id=walletId).first()
        currencyType=wallet.currencytype.id
        ticker = Ticker.query.filter_by(markettype_id=exchange_type_id,currencytype_id=currencyType,user_id=current_user.id).first()

        if ticker is not None:
            tickerSchema = TickerSchema()
            ticker_json = json.dumps(tickerSchema.dump(ticker))
            return ticker_json
        else:
            return ""
    except BaseException as e:
        raise e.message

@settings.route('/ordersettings/getorderstable', methods=['GET'])
def getMyOrdersTable():
    account = Account.query.filter_by(user_id=current_user.id).first()
    orderList=Order.query.filter_by(account_id=account.id,order_type=OrderTypeEnum.MULTIPLE.value).order_by(Order.date_time).all()
    return render_template('partial/myorders/myorderstable.html',orderList=orderList)



@settings.route('/ordersettings/create-order', methods=['GET', 'POST'])
def saveNewOrder():
    if request.method == "POST":
        walletId = request.form['walletId']
        ticker_min_amount=request.form['minAmount']
        ticker_max_amount=request.form['maxAmount']
        transactionAmount = request.form['transactionAmount']
        currency_market=request.form['currencyMarket']
        if transactionAmount==0:
            return "false"
        currencyMarket=CurrencyMarket.query.filter_by(id=currency_market).first()
        wallet=Wallet.query.filter_by(id=walletId).first()

        if wallet is not  None :
            currencyAmount =float(transactionAmount)/float(ticker_min_amount)
            try:
                order = Order()
                order.date_time=datetime.datetime.now()
                order.account_id=wallet.account_id
                order.currency_type=wallet.currency_type
                order.exchange_type_id=wallet.exchange_type_id
                order.currency_amount=currencyAmount
                order.price=transactionAmount
                order.market_type_id=currencyMarket.market_type_id
                order.tickers_max=ticker_max_amount
                order.tickers_min=ticker_min_amount
                order.wallet_id=wallet.id
                order.transaction_status=TransactionStatusEnum.BUY
                order.order_type=OrderTypeEnum.MULTIPLE
                order.status=StatusEnum.NOTACTIVATED
                order.order_ref=util.generate_order_refrence()
                order.market_exchange=ExchangeMarket.EXCHANGELIMIT
                db.session.add(order)
                db.session.commit()
                check="true"
            except Exception as e:
                db.session.rollback()
                check=e.message
            return check
        else:

                return "false"

    return "false"


@settings.route('/ordersettings/start-trade', methods=['POST'])
def startTrade():
    try:
        order_id = request.form['orderId']
        order = Order.query.filter_by(id=order_id).first()
        if order.exchange_type_id==ExchangeTypeEnum.BITFINEX.value:
            usdt_currency=CurrencyType.query.filter_by(symbol="USD").first()
        if order.exchange_type_id==ExchangeTypeEnum.BITTREX.value:
            usdt_currency = CurrencyType.query.filter_by(symbol="USDT").first()
        usdt_wallet=Wallet.query.filter_by(exchange_type_id=order.exchange_type_id,account_id=order.account_id,currency_type=usdt_currency.id).first()
        amount=usdt_wallet.available_amount
        remaining_amount=amount-order.price

        if amount==0 or remaining_amount<0 :
            return "insuficient-fund"
        if ExchangeTypeEnum.BITFINEX ==order.exchange_type.id:
           bitFinexTradeLogic=BitfinexTradeLogic()
           jobStatus=JobStatus.ADDJOB
           msg=bitFinexTradeLogic.tradeEngine(jobStatus,order)
           if msg == True :
               return "true"
        else:
            bitFinexTradeLogic = BitfinexTradeLogic()
            jobStatus = JobStatus.ADDJOB
            #also used for bittrex
            msg = bitFinexTradeLogic.tradeEngine(jobStatus, order)
            if msg == True:
                return "true"

    except BaseException as e:
        return e.message

    return msg


@settings.route('/ordersettings/cancel-trade', methods=['POST'])
def cancelTrade():
    try:
        order_id = request.form['orderId']
        order = Order.query.filter_by(id=order_id).first()
        bitFinexTradeLogic=BitfinexTradeLogic()
        msg=bitFinexTradeLogic.cancelTrade(order)
        if msg:
           return "true"
    except BaseException as e:
        return e.message

    return  msg




@settings.route('/ordersettings/view-order-detail-multiple', methods=['POST'])
def getOrderDetail():
    order_ref = request.form['orderRef']
    orderPaymentList=OrderPaymentDetail.query.filter_by(order_ref=order_ref).all()
    return render_template('partial/myorders/orderdetailmodaltable.html',orderPaymentList=orderPaymentList)



#===========================================for single order================================================================>
#===========================================================================================================================>
#==============================================single order module started==================================================>



@settings.route('/singleordersettings', methods=['GET'])
def singleOrderSettings():
    accountlogic = Accountlogic()
    account_bitfinex = Account.query.filter_by(user_id=current_user.id,exchange_type_id=ExchangeTypeEnum.BITFINEX.value).first()
    dateValue = request.args['dateTime']
    account_bittrex=Account.query.filter_by(user_id=current_user.id,exchange_type_id=ExchangeTypeEnum.BITTREX.value).first()
    if account_bitfinex is not None:
        accountlogic.updateAccountDetailForBitfinex(account_bitfinex.api_key,account_bitfinex.api_secret_key,dateValue,ExchangeTypeEnum.BITFINEX.value,account_bitfinex)
    if  account_bittrex is not None:
        accountlogic.updateAccountForBittrex(account_bittrex.api_key, account_bittrex.api_secret_key, ExchangeTypeEnum.BITTREX.value, account_bittrex)

    exchange_type_list=util.exchange_type_dropdown_list()
    market_type_list=util.get_market_type_from_ticker()
    transaction_status=util.get_transaction_status()
    exchange_market_enum=util.exchange_market_enum()


    return render_template('auth/admin/singleorder.html',transaction_status=transaction_status,exchange_type_list=exchange_type_list,market_type_list=market_type_list,exchange_market_enum=exchange_market_enum)


@settings.route('/ordersettings/getsingleordermarkettype', methods=['POST'])
def getSingleOrderMarketType():
    try:
        walletId = request.form['walletId']
        wallet = Wallet.query.filter_by(id=walletId).first()
        currencyMarket=CurrencyMarket.query.filter_by(currency_type_id=wallet.currency_type).all()
        currency_market_json = CurrencyMarket()
        if currencyMarket is not None:
            currencyMarketSchema = CurrencyMarketSchema()
            currency_market_json = json.dumps(currencyMarketSchema.dumps(currencyMarket,True))
        return currency_market_json
    except BaseException as e:
        raise e.message



@settings.route('/ordersettings/create-single-order', methods=['GET', 'POST'])
def saveNewSingleOrder():
    if request.method == "POST":
        cryptoAmount = request.form['cryptoAmount']
        walletId = request.form['walletId']
        crytpoPrice = request.form['crytpoPrice']
        currencyMarketTypeId = request.form['marketType']
        transactionStatus = request.form['transactionStatus']
        price= request.form['price']
        availableBallanceUsd =  request.form['availableBallanceUsd']
        exchangeMarket = request.form['exchangeMarket']


        wallet=Wallet.query.filter_by(id=walletId).first()
        currencyMarketTypemarketType=CurrencyMarket.query.filter_by(id=currencyMarketTypeId).first()

        if  float(availableBallanceUsd) <=0 or float(crytpoPrice) > float(availableBallanceUsd):
            return "insuficient-fund"
        if wallet is not  None :
            try:
                order = Order()
                order.date_time=datetime.datetime.now()
                order.account_id=wallet.account_id
                order.currency_type=wallet.currency_type
                order.exchange_type_id=wallet.exchange_type_id
                order.currency_amount=cryptoAmount
                order.price_to_pay=crytpoPrice
                order.order_type=OrderTypeEnum.SINGLE
                order.wallet_id=wallet.id
                order.price=price
                order.status=StatusEnum.NOTACTIVATED
                order.market_exchange = exchangeMarket
                order.transaction_status=transactionStatus
                order.market_type_id=currencyMarketTypemarketType.markettype.id
                order.order_ref=util.generate_order_refrence()
                db.session.add(order)

                orderPaymentDetail= OrderPaymentDetail()
                orderPaymentDetail.order_ref=order.order_ref
                orderPaymentDetail.original_amount=cryptoAmount
                orderPaymentDetail.date_time=datetime.datetime.now()
                orderPaymentDetail.order_id=order.id
                orderPaymentDetail.is_cancelled=False
                orderPaymentDetail.order_type = OrderTypeEnum.SINGLE
                orderPaymentDetail.is_live=False
                orderPaymentDetail.account_id=wallet.account_id
                db.session.add(orderPaymentDetail)
                db.session.commit()
                check="true"
            except Exception as e:
                db.session.rollback()
                check=e.message
            return check
        else:

                return "false"

    return "false"


@settings.route('/ordersettings/getsingleorderstable', methods=['GET'])
def getMySingleOrdersTable():
    dateValue = request.args['dateTime']
    bifinexOrder = BitfinexOrder()
    bittrex_order=BittrexOrder()
    bitfinex_account = Account.query.filter_by(user_id=current_user.id,exchange_type_id=ExchangeTypeEnum.BITFINEX.value).first()
    bitfinex_order_list= bifinexOrder.getOrderHistoryBitfinex(dateValue,bitfinex_account)

    bittrex_account=Account.query.filter_by(user_id=current_user.id,exchange_type_id=ExchangeTypeEnum.BITTREX.value).first()
    overall_order_list=bittrex_order.getOrderHistoryBittrex(bitfinex_order_list,bittrex_account)
    return render_template('partial/myorders/singleordertable.html',orderList=overall_order_list)



@settings.route('/ordersettings/cancel-order', methods=['POST'])
def cancelOrder():
    orderId = request.form['orderId']
    dateValue=request.form['dateTime']
    exchange_type = request.form['exchangeType']
    bifinexOrder = BitfinexOrder()
    orderPaymentDetail=None
    try:
        order = Order.query.filter_by(id=orderId).first()
        orderPaymentDetail = OrderPaymentDetail.query.filter_by(order_id=orderId).first()
    except Exception as e:
        pass
    if orderPaymentDetail is not None :
        return"Completed"
    elif orderPaymentDetail.orders.status==StatusEnum.CANCELLED.value:
        return "Cancelled"
    elif orderPaymentDetail.orders.status==StatusEnum.NOTACTIVATED.value:
        return"Not-Activated"
    if order.exchange_type.id == ExchangeTypeEnum.BITFINEX.value:
       msg = bifinexOrder.CancelOrderBitfinex(dateValue, orderPaymentDetail)
    if order.exchange_type_id==ExchangeTypeEnum.BITTREX.value:
      pass

    else:
        if ExchangeTypeEnum.BITFINEXVALUE.value.lower()== exchange_type:
            account = Account.query.filter_by(user_id=current_user.id,exchange_type_id=ExchangeTypeEnum.BITFINEX.value).first()
            msg = bifinexOrder.CancelUnsavedOrderBitfinex(dateValue,orderId, account)
        if ExchangeTypeEnum.BITTREXVALUE.value.lower()==exchange_type:
            pass

    return msg
