from flask import render_template, redirect, request, url_for, flash, json, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import settings
from ..models import User, Person,Account, Ticker,Wallet,Order,StatusEnum,ArbitrageTrade,\
    ExchangeType,ExchangeTypeEnum,JobStatus,CurrencyMarket,OrderTypeEnum,OrderPaymentDetail,TransactionStatusEnum,ExchangeMarket
from app.Util.utility import Utility as util
from app.Util.ModelSchema import WalletSchema,TickerSchema,ExchangeTypeSchema,CurrencyMarketSchema
from ..BitfinanceBuisnessLogic.trade import BitfinexTradeLogic
from..BittrexBuisnessLogic.trade import  BittrexTradeLogic
from..BuisnessLogic.AccountLogic import Accountlogic
from..BuisnessLogic.BitfinexOrderLogic import BitfinexOrder
from ..BuisnessLogic .ArbitrageTradeLogic import ArbitrageLogic
from app import db
import datetime
import os


@settings.route('/arbitragesettings', methods=['GET'])
def arbitrageSettings():
    exchange_type_list=util.exchange_type_dropdown_list()
    market_type_list=util.get_market_type_from_ticker()
    currency_type_list=util.currency_type_by_method_dropdown_list()
    transaction_buy_status=TransactionStatusEnum.BUY.value
    return render_template('orders/arbitrageorders.html',transaction_buy_status=transaction_buy_status,exchange_type_list=exchange_type_list,currency_type_list=currency_type_list,market_type_list=market_type_list)


@settings.route('/arbitragesettings/getexchange', methods=['POST'])
def getExchangeTypeList():
    try:
        exchange_type_id=request.form['exchangeTypeId']
        exchange_type_list=ExchangeType.query.filter(ExchangeType.id != exchange_type_id).all()
        exchange_type_schema = ExchangeTypeSchema()
        exchange_list_json = json.dumps(exchange_type_schema.dumps(exchange_type_list, True))
        return exchange_list_json
    except BaseException as e:
        raise e.message

@settings.route('/arbitragesettings/getcurrencybyexchangetypefromwallet', methods=['POST'])
def getCurrencyByExchangeType():
    try:
        exchange_type_id = request.form['exchangeTypeId']
        account=Account.query.filter_by(user_id=current_user.id,exchange_type_id=exchange_type_id).first()
        wallet_list=Wallet.query.filter_by(account_id=account.id,exchange_type_id=exchange_type_id).all()
        wallet_schema = WalletSchema()
        wallet_list_json = json.dumps(wallet_schema.dumps(wallet_list,True))
        return wallet_list_json
    except BaseException as e:
        raise e.message


@settings.route('/arbitragesettings/createnewarbitrageorder', methods=['POST'])
def createOrder():
    exchange_type_from_id = request.form['exchangeTypeFrom']
    exchange_type_to = request.form['exchangeTypeTo']
    usd_amount = request.form['usdAmount']
    crypto_amount = request.form['cryptoAmount']
    currency_type = request.form['currencyType']
    transaction_status=request.form['transactionStatus']
    round_trip = request.form['roundTrip']
    try:
        arbitrage_logic=ArbitrageLogic()
        msg=arbitrage_logic.tradeEngine()
        if TransactionStatusEnum.BUY.value==transaction_status:
            return"Buy is not yet Supported!"
        if  msg !=True:
            return msg
        check_if_exchange_type_from_exist=Account.query.filter_by(user_id=current_user.id,exchange_type_id=exchange_type_from_id).all()
        if not  check_if_exchange_type_from_exist:
            exchange_type_list=ExchangeType.query.filter_by(id=exchange_type_from_id).first();
            return "Api key not found for "+exchange_type_list.description
        check_if_exchange_type_to_exist = Account.query.filter_by(user_id=current_user.id,exchange_type_id=exchange_type_to).all()
        if not  check_if_exchange_type_to_exist:
            exchange_type_list=ExchangeType.query.filter_by(id=exchange_type_to).first();
            return "Api key not found for "+exchange_type_list.description

        arbitrage_trade=ArbitrageTrade()
        arbitrage_trade.exchange_type_to=exchange_type_to
        arbitrage_trade.exchange_type_from=exchange_type_from_id
        arbitrage_trade.date_time=datetime.datetime.now()
        arbitrage_trade.account_from=check_if_exchange_type_from_exist[0].id
        arbitrage_trade.account_to = check_if_exchange_type_to_exist[0].id
        arbitrage_trade.crypto_amount=crypto_amount
        arbitrage_trade.price=usd_amount
        arbitrage_trade.ref_number=util.generate_order_refrence()
        arbitrage_trade.transaction_status=transaction_status
        arbitrage_trade.currency_type=currency_type
        arbitrage_trade.withdrawal_status="Pending"
        arbitrage_trade.do_round_trip=(True if round_trip=="True" else False)
        arbitrage_trade.user_id=current_user.id
        db.session.add(arbitrage_trade)
        db.session.commit()
        return "true"

    except BaseException as e:
        db.session.rollback()
        return e.message
    return  "false"