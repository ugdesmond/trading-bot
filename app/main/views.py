import os, shutil
from werkzeug.utils import secure_filename
# from app.main.ModelSchema import PersonSchema, QualificationSchema, DisplayMessageSchema, StaffSchema
# from app.main.Utility import Utility
# from app.models import DisplayMessage, Qualification, Person, User, RoleType, Staff,StaffQualification
from manage import app
from app import db



from flask import render_template, json, request, session, jsonify
from . import main
from app.models import BackgroundSchedule
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import time



@main.route('/')
def index():

    return render_template('auth/login.html')