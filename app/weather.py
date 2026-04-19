from flask import current_app
import requests


def _empty_weather(city, message):
    return {
        "ok": False,
        "city": city,
        "message": message,
        "temperature": None,
        "description": None,
        "wind_speed": None,
    }


def get_weather_for_city(city):
    api_key = current_app.config.get("WEATHER_API_KEY")
    if not api_key:
        return _empty_weather(
            city,
            "Добавьте ключ OPENWEATHER_API_KEY в переменные окружения, чтобы видеть реальную погоду.",
        )

    try:
        response = requests.get(
            current_app.config["WEATHER_API_URL"],
            params={
                "q": city,
                "appid": api_key,
                "units": "metric",
                "lang": "ru",
            },
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException:
        return _empty_weather(city, "Не удалось получить погоду. Попробуйте позже.")

    payload = response.json()
    weather = payload.get("weather", [{}])[0]
    main = payload.get("main", {})
    wind = payload.get("wind", {})
    return {
        "ok": True,
        "city": payload.get("name", city),
        "temperature": round(main.get("temp", 0)),
        "feels_like": round(main.get("feels_like", 0)),
        "description": weather.get("description", "без описания"),
        "wind_speed": wind.get("speed", 0),
    }
