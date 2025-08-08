from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from config import Config
from dotenv import load_dotenv
from flask_cors import CORS
load_dotenv()
import cloudinary
import os

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(
    app,
    origins=["http://localhost:5173"],
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],  # <- allow bearer header
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app

from .models import *

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)