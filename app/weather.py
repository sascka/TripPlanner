from flask import current_app
import requests

def _empty_weather(city, message):
    return {
        'ok': False,
        'city': city,
        'message': message,
        'temperature': None,
        'description': None,
        'wind_speed': None,
    }

def get_weather_for_city(city):
    key = current_app.config.get('WEATHER_API_KEY')
    if not key:
        return _empty_weather(
            city,
            'Добавьте ключ OPENWEATHER_API_KEY в .env, чтобы видеть реальную погоду.',
        )
    try:
        res = requests.get(
            current_app.config['WEATHER_API_URL'],
            params={
                'q': city,
                'appid': key,
                'units': 'metric',
                'lang': 'ru',
            },
            timeout=5,
        )
    except requests.RequestException:
        return _empty_weather(city, 'Не удалось получить погоду. Попробуйте позже.')
    if res.status_code == 401:
        return _empty_weather(city, 'OpenWeatherMap не принял API-ключ.')
    if not res.ok:
        return _empty_weather(city, 'Не удалось получить погоду. Попробуйте позже.')
    data = res.json()
    info = data.get('weather', [{}])[0]
    main = data.get('main', {})
    wind = data.get('wind', {})
    return {
        'ok': True,
        'city': data.get('name', city),
        'temperature': round(main.get('temp', 0)),
        'feels_like': round(main.get('feels_like', 0)),
        'description': info.get('description', 'без описания'),
        'wind_speed': wind.get('speed', 0),
    }
