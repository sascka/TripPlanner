from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from .extensions import db
from .models import ChecklistItem, Note, Trip
from .weather import get_weather_for_city

api_bp = Blueprint('api', __name__)


def _trip_or_404(trip_id):
    trip = db.get_or_404(Trip, trip_id)
    if trip.owner_id != current_user.id:
        return None
    return trip


@api_bp.get('/trips')
@login_required
def trips_list():
    trips = (
        Trip.query.filter_by(owner_id=current_user.id)
        .order_by(Trip.start_date.asc(), Trip.created_at.desc())
        .all()
    )
    return jsonify([trip.to_dict(private=True) for trip in trips])


@api_bp.get('/trips/<int:trip_id>')
@login_required
def trip_detail(trip_id):
    trip = _trip_or_404(trip_id)
    if trip is None:
        return jsonify({'error': 'Нет доступа к этой поездке'}), 403
    return jsonify(trip.to_dict(private=True, nested=True))


@api_bp.post('/trips/<int:trip_id>/checklist')
@login_required
def add_checklist_item(trip_id):
    trip = _trip_or_404(trip_id)
    if trip is None:
        return jsonify({'error': 'Нет доступа к этой поездке'}), 403
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'Пункт чек-листа не может быть пустым'}), 400
    item = ChecklistItem(text=text, trip=trip)
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@api_bp.patch('/checklist/<int:item_id>')
@login_required
def toggle_checklist_item(item_id):
    item = db.get_or_404(ChecklistItem, item_id)
    if item.trip.owner_id != current_user.id:
        return jsonify({'error': 'Нет доступа к этому пункту'}), 403
    data = request.get_json(silent=True) or {}
    item.is_done = bool(data.get('is_done', not item.is_done))
    db.session.commit()
    return jsonify(item.to_dict())


@api_bp.delete('/checklist/<int:item_id>')
@login_required
def delete_checklist_item(item_id):
    item = db.get_or_404(ChecklistItem, item_id)
    if item.trip.owner_id != current_user.id:
        return jsonify({'error': 'Нет доступа к этому пункту'}), 403
    db.session.delete(item)
    db.session.commit()
    return jsonify({'status': 'deleted'})


@api_bp.post('/trips/<int:trip_id>/notes')
@login_required
def add_note(trip_id):
    trip = _trip_or_404(trip_id)
    if trip is None:
        return jsonify({'error': 'Нет доступа к этой поездке'}), 403
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or 'Заметка').strip()
    text = (data.get('content') or '').strip()
    if not text:
        return jsonify({'error': 'Текст заметки не может быть пустым'}), 400
    note = Note(title=title, content=text, trip=trip)
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@api_bp.delete('/notes/<int:note_id>')
@login_required
def delete_note(note_id):
    note = db.get_or_404(Note, note_id)
    if note.trip.owner_id != current_user.id:
        return jsonify({'error': 'Нет доступа к этой заметке'}), 403
    db.session.delete(note)
    db.session.commit()
    return jsonify({'status': 'deleted'})


@api_bp.get('/weather')
@login_required
def weather():
    city = (request.args.get('city') or '').strip()
    if not city:
        return jsonify({'error': 'Передайте город в параметре city'}), 400
    return jsonify(get_weather_for_city(city))
