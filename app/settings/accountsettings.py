
from flask import render_template, redirect, request, url_for, flash, json, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import settings
from ..models import User, Person,Account, Ticker,ExchangeTypeEnum
from app.Util.utility import Utility as util
from..BuisnessLogic.AccountLogic import Accountlogic
from app import db
import datetime


@settings.route('/save-user-account', methods=['GET', 'POST'])
def saveUserAccount():
    if request.method == "POST":
        apiKey = request.form['apiKey']
        secretKey = request.form['secretKey']
        exchangeType=request.form['exchangeTypeId']
        dateValue = request.form['dateValue']
        chekifaccountexist = Account.query.filter_by(api_key=apiKey,api_secret_key=secretKey).first()
        accountUser = Account.query.filter_by(user_id=current_user.id,exchange_type_id=exchangeType).first()
        if chekifaccountexist is  None and accountUser is None:
            if int(exchangeType)==ExchangeTypeEnum.BITFINEX.value:
                accountlogic = Accountlogic()
                checkAccountExist=accountlogic.getAccountDetailForBitfinex(apiKey,secretKey,dateValue,exchangeType)
                try:
                    if checkAccountExist:
                        check="true"
                except Exception as e:
                    db.session.rollback()
                    check="false"
                return check
        else:
            if accountUser is not None:
                accountlogic = Accountlogic()
                checkAccountExist = accountlogic.updateAccountDetailForBitfinex(apiKey, secretKey, dateValue, exchangeType,accountUser)
                if checkAccountExist == "true":
                    accountUser.api_key=apiKey
                    accountUser.api_secret_key =secretKey
                    accountUser.exchange_type_id = exchangeType
                    db.session.add(accountUser)
                    db.session.commit()
                    return "update-successful"

    return  checkAccountExist

@settings.route('/API-table', methods=['POST'])
# @login_required
def getApiTable():
    account=Account.query.filter_by(user_id=current_user.id).first()

    return render_template('partial/admin/_apikeymodal.html',account=account)






@settings.route('/set_ticker', methods=['GET', 'POST'])
@login_required
def set_tickers():
    if request.method == "POST":
        max_amount = request.form['maxamount']
        min_amount = request.form['minamount']
        markettype_id = request.form['markettype']
        currencytype_id = request.form['currencytype']
        exchangetype = request.form['exchangetype']
        ticker = Ticker.query.filter_by(currencytype_id=currencytype_id, user_id=current_user.id,markettype_id=markettype_id,exchangetype_id=exchangetype).first()
        if ticker is None:
            try:
                ticker = Ticker()
                ticker.markettype_id = markettype_id
                ticker.min_amount = min_amount
                ticker.max_amount = max_amount
                ticker.date_time = datetime.datetime.now()
                ticker.user_id = current_user.id
                ticker.currencytype_id = currencytype_id
                ticker.exchangetype_id = exchangetype
                db.session.add(ticker)
                db.session.flush()
                db.session.commit()
                return "True"
            except Exception as e:
                db.session.rollback()
                return "Error occured! "+e.message
        else:
            try:
                ticker.max_amount = max_amount
                ticker.min_amount = min_amount
                db.session.add(ticker)
                db.session.commit()
                return "True"
            except Exception as e:
                db.session.rollback()
                return "Error occured! " + e.message


@settings.route('/get_ticker_modal', methods=['GET', 'POST'])
@login_required
def get_ticker_modal():
    if request.method == "POST":
        accountKey = Account.query.filter_by(user_id=current_user.id).first()
        if accountKey is None:
           return "False"
        else:
            exchangeTypeList = util.exchange_type_dropdown_list()
            marketTypeList = util.market_type_dropdown_list()
            currencyTypeList = util.currency_type_dropdown_list()
            return render_template('partial/admin/tickers.html',marketTypeList=marketTypeList,currencyTypeList=currencyTypeList, exchangeTypeList=exchangeTypeList)

@settings.route('/get_order_book', methods=['GET', 'POST'])
@login_required
def get_order_book():

    return render_template('partial/admin/orderbook.html')



@settings.route('/get_ticker', methods=['GET', 'POST'])
@login_required
def get_ticker():
    if request.method == "POST":
        exchange = request.form['exchangeType']
        tickerList = sorted(Ticker.query.filter_by(user_id=current_user.id, exchangetype_id=exchange).all(),key=lambda x: x.markettype_id )
        return render_template('partial/admin/getTicker.html',tickerList=tickerList)