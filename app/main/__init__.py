__author__ = 'mark&ugo'

from flask import Blueprint

main = Blueprint('main', __name__)

from . import views