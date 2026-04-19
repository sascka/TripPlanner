# TripPlanner

TripPlanner, или «Умный путешественник», — веб-приложение для планирования поездок. Пользователь создаёт маршрут, ведёт чек-лист подготовки, хранит заметки и документы, смотрит погоду в городе поездки и может сгенерировать PDF-отчёт.

## Возможности

- регистрация, вход и выход из аккаунта;
- ORM-модели `User`, `Trip`, `ChecklistItem`, `Note`, `Document`;
- создание, редактирование и удаление поездок;
- чек-лист подготовки с прогрессом;
- заметки по поездке;
- загрузка PDF, PNG, JPG и JPEG документов;
- REST API для поездок, чек-листа, заметок и погоды;
- интеграция с OpenWeatherMap;
- генерация PDF-отчёта;
- публичная read-only ссылка на поездку;
- SQLite для хранения данных;
- Bootstrap-интерфейс.

## Быстрый запуск

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
py main.py
```

После запуска сайт будет доступен по адресу `http://127.0.0.1:5000`.

## Настройка погоды

Для реальной погоды нужен ключ OpenWeatherMap. Его надо записать в переменную окружения:

```bash
set OPENWEATHER_API_KEY=ваш_ключ
```

Без ключа приложение продолжит работать, но вместо погоды покажет подсказку.

## REST API

Все приватные API-точки требуют авторизации через сайт.

- `GET /api/trips` — список поездок пользователя;
- `GET /api/trips/<id>` — подробная информация о поездке;
- `POST /api/trips/<id>/checklist` — добавить пункт чек-листа;
- `PATCH /api/checklist/<id>` — изменить статус пункта;
- `DELETE /api/checklist/<id>` — удалить пункт;
- `POST /api/trips/<id>/notes` — добавить заметку;
- `DELETE /api/notes/<id>` — удалить заметку;
- `GET /api/weather?city=Казань` — получить погоду.

## Структура проекта

```text
app/
  __init__.py       создание Flask-приложения
  api.py            REST API
  config.py         настройки
  extensions.py     SQLAlchemy и Flask-Login
  models.py         ORM-модели
  pdf.py            генерация PDF
  routes.py         HTML-маршруты
  weather.py        работа с OpenWeatherMap
static/
  css/styles.css
  js/trip_detail.js
templates/
  auth/
  trips/
docs/
  technical_spec.md
  explanatory_note.md
  presentation_outline.md
main.py
requirements.txt
```

## Хостинг

Проект подготовлен для хостинга, который умеет запускать Flask через `Procfile`, например Render. Команда запуска:

```bash
gunicorn main:app
```

Для production-развёртывания надо задать `SECRET_KEY`, `OPENWEATHER_API_KEY` и при необходимости `DATABASE_URL`.
