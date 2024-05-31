__author__ = 'markugo'
from app import create_app
from app.models import db
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from apscheduler.schedulers.background import BackgroundScheduler

import  sys





app = create_app('development')
manager = Manager(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    #manager.run()
    scheduler = BackgroundScheduler()
    url = sys.argv[1] if len(sys.argv) > 1 else 'sqlite:///jobs.sqlite'
    scheduler.add_jobstore('sqlalchemy', url=url)
    scheduler.start()

    app.run(debug=True, port=8000)





    #socketio.run(app, debug=True, port=5564)
