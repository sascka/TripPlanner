import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'instance' / 'tripplanner.sqlite3'
ENV_PATH = BASE_DIR / '.env'


def load_env():
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, val = line.split('=', 1)
        os.environ.setdefault(key.strip(), val.strip().strip('\''))


load_env()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-tripplanner-secret-xxxxxxxxx')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    WEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', '')
    WEATHER_API_URL = 'https://api.openweathermap.org/data/2.5/weather'
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
