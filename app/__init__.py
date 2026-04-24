from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục.'
login_manager.login_message_category = 'warning'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.receptionist import receptionist_bp
    from app.routes.doctor import doctor_bp
    from app.routes.assistant import assistant_bp
    from app.routes.patient import patient_bp
    from app.routes.admin import admin_bp
    from app.routes.medicine import medicine_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(receptionist_bp, url_prefix='/receptionist')
    app.register_blueprint(doctor_bp, url_prefix='/doctor')
    app.register_blueprint(assistant_bp, url_prefix='/assistant')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(medicine_bp, url_prefix='/medicines')

    return app
