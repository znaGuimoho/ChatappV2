import os
from flask import Flask
from flask_socketio import SocketIO
from flask_session import Session

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-fixed-secret-key')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'public_files')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    Session(app)

    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', manage_session=False)
    return app, socketio