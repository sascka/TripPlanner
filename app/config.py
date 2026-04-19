import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-tripplanner-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'tripplanner.sqlite3'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    WEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
    WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
