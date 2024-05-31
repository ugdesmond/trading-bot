__author__ = 'mark&ugo'

from flask import render_template,render_template_string, redirect, request, url_for, flash, json, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from ..models import User, Person,RoleType, Ticker,Account,ExchangeTypeEnum,Wallet,CurrencyTypeEnum
from app.Util.utility import Utility as util
from app import db
import urllib, os,time
import codecs, requests
from..BuisnessLogic.AccountLogic import Accountlogic
import pandas as pd
from app.models import BackgroundSchedule
from apscheduler.schedulers.background import BackgroundScheduler
import pickle
from lxml import html
import datetime




@auth.route('/', methods=['GET'])
def home():


    return render_template('auth/login.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password_hash=password).first()
        if user is not None:
            login_user(user)

            url = os.path.abspath('app/templates/email/emailtemp.html')
            subject = 'Login Notification'
            body = 'Our system has detected that you successfully logged in to your account '
            page = str(codecs.open(os.path.dirname(os.path.join(url, 'emailtemp.html'))).read())
            page = page.replace("{{COMPANY_NAME}}", 'AUTOPILOT')
            page = page.replace("{{Subject}}", subject)
            page = page.replace("{{Message}}", body )
            response = util.sendgrid(user.email, subject, page)
            if response.status_code == 401:
                return 'An error occurred: {}'.format(response.body), 500
                pass
            # util.sendgrid(user.email, subject, page)
            return "auth/dashboard"
        return "False"
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        password_confirm = request.form['confirmPassword']
        if password != password_confirm:
            flash("Password fields do not match", category='error') #set flash message and return to the same registration page
            return render_template('auth/register.html')
        exists = User.is_user_exisiting(email, password)
        if not exists:
            try:
                person = Person(firstname=email, surname=email)
                roleId= RoleType.USER
                db.session.add(person)
                db.session.flush()
                user = User(username=email, email=email, password_hash=password, role_id=roleId, person_id=person.id)
                db.session.add(user)
                db.session.commit()
                login_user(user)
                url = os.path.abspath('app/templates/email/emailtemp.html')
                subject = 'Login Notification'
                body = 'Your registration was successful.'
                page = str(codecs.open(os.path.dirname(os.path.join(url, 'emailtemp.html'))).read())
                page = page.replace("{{COMPANY_NAME}}", 'AUTOPILOT')
                page = page.replace("{{Subject}}", subject)
                page = page.replace("{{Message}}", body)
                response = util.sendgrid(user.email, subject, page)
                if response.status_code == 401:
                    return 'An error occurred: {}'.format(response.body), 500

                return "dashboard"
            except Exception as e:
                db.session.rollback()
                return "Error occured! "+e.message

    return render_template('auth/register.html')


@auth.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    exchangeTypeList = util.exchange_type_dropdown_list()
    marketTypeList =util.market_type_dropdown_list()
    currencyTypeList=util.currency_type_dropdown_list()
    accountlogic = Accountlogic()
    date_now = time.mktime(datetime.datetime.now().timetuple())
    date = str(date_now).index('.')
    sub_string_date = str(date_now)[0:date]
    nonce = sub_string_date + "000"
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    tickerList = Ticker.query.filter_by(user_id=current_user.id).all()

    if accounts is not None:
        for account in accounts:
            if account.exchange_type_id  == ExchangeTypeEnum.BITFINEX.value:
                accountlogic.updateAccountDetailForBitfinex(account.api_key, account.api_secret_key, nonce, ExchangeTypeEnum.BITFINEX.value, account)
            else:
                accountlogic.updateAccountForBittrex(account.api_key, account.api_secret_key, ExchangeTypeEnum.BITTREX.value, account)
    bitfinexwallet = Wallet.query.filter_by(exchange_type_id=ExchangeTypeEnum.BITFINEX.value)
    bittrexwallet = Wallet.query.filter_by(exchange_type_id=ExchangeTypeEnum.BITTREX.value)
    # walletaddress = Wallet.query.filter_by(currency_type=CurrencyTypeEnum.BTC).first()


    return render_template('auth/admin/dashboard.html',tickerList=tickerList, exchangeTypeList=exchangeTypeList,marketTypeList=marketTypeList,currencyTypeList=currencyTypeList, bitfinexwallet=bitfinexwallet,bittrexwallet=bittrexwallet)

@auth.route('/getgraphdata', methods=['GET', 'POST'])
@login_required
def getgraph():
    try:
        currenttime = request.form['currentdate']
        baseUrl = 'https://api.bitfinex.com/v2/candles/trade:1m:tBTCUSD/hist?start='+currenttime+'&sort=1&limit=1000'
        data = requests.get(baseUrl)
        if data:
            return data.content
        else:
            return "False"
    except Exception as e:
        return "Error occured! "+e.message
    return check