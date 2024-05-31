__author__ = 'mark$ugo'
from flask import Blueprint

settings = Blueprint('settings', __name__)

from . import accountsettings,ordersettings,backgroundschedularsettings,arbitrage