# config.py
import os
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'super-secret-key')
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

    # Tokens: short access, long refresh
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # We’ll keep access token in headers, refresh in cookies
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_SECURE = False  # True in production (HTTPS)
    JWT_COOKIE_SAMESITE = "Lax"  # "None" in prod if cross-site + HTTPS
    JWT_COOKIE_CSRF_PROTECT = False  # you can turn this on later
    JWT_REFRESH_COOKIE_PATH = "/token/refresh"  # only send cookie for this route
