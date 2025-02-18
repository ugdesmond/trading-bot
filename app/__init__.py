__author__ = 'markugo'
from flask import Flask
#from flask_socketio import SocketIO
from config import configDict
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_qrcode import QRcode
from apscheduler.schedulers.background import BackgroundScheduler

#from app import models



login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'
db = SQLAlchemy()
#socketio = SocketIO()



def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(configDict[config_name])
    configDict[config_name].init_app(app)
    db.init_app(app)
    # scheduler = APScheduler()
    # scheduler.init_app(app)
    # scheduler.start()
    login_manager.init_app(app)
    QRcode(app)



    #from .accounting import accounting as accounting_blueprint
    #app.register_blueprint(accounting_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .settings import settings as settings_blueprint
    app.register_blueprint(settings_blueprint, url_prefix='/settings')

    from .rest_api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    @app.route('/sw.js', methods=['GET'])
    def sw():
        return app.send_static_file('sw.js')

    return app
