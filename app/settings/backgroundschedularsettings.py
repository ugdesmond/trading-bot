from flask import render_template, redirect, request, url_for, flash, json, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import settings
from ..models import User, Person,Account, Ticker,ExchangeTypeEnum,BackgroundSchedule,StatusEnum,JobTask
from app.Util.utility import Utility as util
from..BitfinanceBuisnessLogic.trade import  BitfinexTradeLogic
from ..BuisnessLogic .ArbitrageTradeLogic import ArbitrageLogic
from app import db
import datetime


@settings.route('/schedularsettings', methods=['GET'])
def scheduler():
    background_schedular_list=BackgroundSchedule.query.all()
    background_description_list=util.background_schedular_dropdownlist()
    return render_template('settings/schedulersettings.html',backgroundSchedularList=background_schedular_list,
                           background_description_list=background_description_list)



@settings.route('/schedularsettings/create-job', methods=['GET', 'POST'])
def createNewJob():
    if request.method == "POST":
        interval = request.form['interval']
        job_name = request.form['jobName']
        try:
            msg=BackgroundSchedule.query.filter_by(job=job_name).first()
            if msg:
                return "already-exist"
            scheduler = BackgroundSchedule()
            scheduler.job=job_name
            scheduler.status=StatusEnum.STOPPED.value
            scheduler.interval=interval
            db.session.add(scheduler)
            db.session.commit()
            return "true"
        except Exception as e:
            db.session.rollback()
            return "Error occured! "+e.message

    return "false"


@settings.route('/schedularsettings/job-table', methods=['GET'])
def getJobTable():
    background_schedular_list=BackgroundSchedule.query.all()

    return render_template('partial/settings/jobtable.html',backgroundSchedularList=background_schedular_list)

@settings.route('/schedularsettings/cancel-job', methods=['GET', 'POST'])
def canceljob():
    if request.method == "POST":
        job_id = request.form['jobId']

        try:
            job_logic=BitfinexTradeLogic()
            arbitrage_logic = ArbitrageLogic()
            job_object = BackgroundSchedule.query.filter_by(id=job_id).first()
            if job_object.job == JobTask.ARBITRAGETASK.value:
                msg = arbitrage_logic.removeJob(job_object)
            else:
                msg = job_logic.removeJob(job_object)
            if msg:
                return "true"
            else:
                return "false"
        except Exception as e:
            return "Error occured! "+e.message

    return "false"



@settings.route('/schedularsettings/activate-job', methods=['GET', 'POST'])
def createjob():
    if request.method == "POST":
        job_id = request.form['jobId']
        try:
            job_logic=BitfinexTradeLogic()
            arbitrage_logic=ArbitrageLogic()
            job_object = BackgroundSchedule.query.filter_by(id=job_id).first()
            if job_object.job==JobTask.ARBITRAGETASK.value:
                msg=arbitrage_logic.addArbitrageJob(job_object)
            else:
                msg = job_logic.addJob(job_object)
            if msg:
                return "true"
            else:
                return "false"
        except Exception as e:
            return "Error occured! "+e.message

    return "false"