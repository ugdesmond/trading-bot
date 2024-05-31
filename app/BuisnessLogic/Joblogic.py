from flask import render_template, redirect, request, url_for, flash, json, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User, Person,Account, Ticker,ExchangeTypeEnum,BackgroundSchedule,StatusEnum
from app.Util.utility import Utility as util
from..BuisnessLogic.AccountLogic import Accountlogic
from apscheduler.schedulers.background import BackgroundScheduler
from app import db
import datetime
import sys


class JobLogicClass:

    def removeJob(self, jobScheduler=BackgroundScheduler()):
        scheduler = BackgroundScheduler()
        url = sys.argv[1] if len(sys.argv) > 1 else 'sqlite:///example.sqlite'
        scheduler.add_jobstore('sqlalchemy', url=url)
        scheduler.add_job(job_id=jobScheduler.job)
        scheduler.start()
        jobs=scheduler.get_jobs()
        msg=False
        if len(jobs)!=0:
            for jobObj in jobs:
                if jobObj.id==jobScheduler.job:
                    try:
                        scheduler.remove_job(job_id=jobScheduler.job)
                        jobScheduler.status=StatusEnum.RUNNING.value
                        db.session.add(jobScheduler)
                        db.session.commit(jobScheduler)
                        msg=True
                        break
                    except Exception as e:
                        db.session.rollback()
        if len(scheduler.get_jobs()) ==0:
            scheduler.shutdown
        return msg