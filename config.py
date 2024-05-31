__author__ = 'mark$ugo'

class Config:
    SECRET_KEY = "stackunderflowoftheoverflow"
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    UPLOAD_FOLDER = 'app/static/uploads/'
    UPLOAD_FOLDER_TEMP = 'app/static/uploads/temp/'
    MAX_DOCUMENT_FILE = 150 * 1024
    MAX_PASSPORT_FILE = 50 * 1024
    ALLOWED_EXTENSIONS = ['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif']

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://venus:venus@localhost/Autopilot'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:computer007@localhost/ugarpayroll'
configDict = {'development': DevelopmentConfig, 'production': ProductionConfig}