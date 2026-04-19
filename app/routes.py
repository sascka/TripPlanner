from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from .extensions import db
from .models import ChecklistItem, Document, Note, Trip, User
from .pdf import generate_trip_pdf
from .weather import get_weather_for_city

main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
trip_bp = Blueprint('trips', __name__, url_prefix='/trips')


def _date(val):
    return datetime.strptime(val, '%Y-%m-%d').date()


def _file_ok(name):
    ext = Path(name).suffix.lower().lstrip('.')
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def _own_trip(trip_id):
    trip = db.get_or_404(Trip, trip_id)
    if trip.owner_id != current_user.id:
        abort(403)
    return trip


@main_bp.get('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('trips.dashboard'))
    return render_template('index.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('trips.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        pwd = request.form.get('password', '')
        pwd2 = request.form.get('pwd2', '')
        if not name or not email or not pwd:
            flash('Заполните имя, почту и пароль.', 'danger')
        elif pwd != pwd2:
            flash('Пароли не совпадают.', 'danger')
        elif len(pwd) < 6:
            flash('Пароль должен быть не короче 6 символов.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Пользователь с такой почтой уже существует.', 'danger')
        else:
            user = User(name=name, email=email)
            user.set_password(pwd)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Аккаунт создан. Можно планировать первую поездку.', 'success')
            return redirect(url_for('trips.dashboard'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('trips.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pwd = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(pwd):
            login_user(user, remember=bool(request.form.get('remember')))
            flash('С возвращением.', 'success')
            return redirect(url_for('trips.dashboard'))
        flash('Неверная почта или пароль.', 'danger')

    return render_template('auth/login.html')


@auth_bp.post('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из аккаунта.', 'info')
    return redirect(url_for('main.index'))


@trip_bp.get('/')
@login_required
def dashboard():
    q = request.args.get('q', '').strip()
    stmt = Trip.query.filter_by(owner_id=current_user.id)
    if q:
        like = f'%{q}%'
        stmt = stmt.filter(or_(Trip.title.ilike(like), Trip.destination.ilike(like)))
    trips = stmt.order_by(Trip.start_date.asc(), Trip.created_at.desc()).all()
    return render_template('trips/dashboard.html', trips=trips, query=q)


@trip_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        form = request.form.to_dict()
        try:
            start = _date(form.get('start_date', ''))
            end = _date(form.get('end_date', ''))
        except ValueError:
            flash('Проверьте даты поездки.', 'danger')
            return render_template('trips/form.html', trip=None, form=form)
        if end < start:
            flash('Дата возвращения не может быть раньше даты начала.', 'danger')
            return render_template('trips/form.html', trip=None, form=form)
        title = form.get('title', '').strip()
        city = form.get('destination', '').strip()
        if not title or not city:
            flash('Название и город обязательны.', 'danger')
            return render_template('trips/form.html', trip=None, form=form)
        trip = Trip(
            title=title,
            destination=city,
            start_date=start,
            end_date=end,
            budget=int(form.get('budget') or 0),
            description=form.get('description', '').strip(),
            owner=current_user,
        )
        db.session.add(trip)
        db.session.commit()
        flash('Поездка создана.', 'success')
        return redirect(url_for('trips.detail', trip_id=trip.id))

    return render_template('trips/form.html', trip=None, form={})


@trip_bp.route('/<int:trip_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(trip_id):
    trip = _own_trip(trip_id)
    if request.method == 'POST':
        form = request.form.to_dict()
        try:
            start = _date(form.get('start_date', ''))
            end = _date(form.get('end_date', ''))
        except ValueError:
            flash('Проверьте даты поездки.', 'danger')
            return render_template('trips/form.html', trip=trip, form=form)
        if end < start:
            flash('Дата возвращения не может быть раньше даты начала.', 'danger')
            return render_template('trips/form.html', trip=trip, form=form)
        trip.title = form.get('title', '').strip()
        trip.destination = form.get('destination', '').strip()
        trip.start_date = start
        trip.end_date = end
        trip.budget = int(form.get('budget') or 0)
        trip.description = form.get('description', '').strip()
        db.session.commit()
        flash('Поездка обновлена.', 'success')
        return redirect(url_for('trips.detail', trip_id=trip.id))

    form = {
        'title': trip.title,
        'destination': trip.destination,
        'start_date': trip.start_date.isoformat(),
        'end_date': trip.end_date.isoformat(),
        'budget': trip.budget,
        'description': trip.description,
    }
    return render_template('trips/form.html', trip=trip, form=form)


@trip_bp.get('/<int:trip_id>')
@login_required
def detail(trip_id):
    trip = _own_trip(trip_id)
    weather = get_weather_for_city(trip.destination)
    share = url_for('trips.shared', token=trip.share_token, _external=True)
    return render_template(
        'trips/detail.html', trip=trip, weather=weather, share_url=share
    )


@trip_bp.post('/<int:trip_id>/checklist')
@login_required
def add_checklist_item(trip_id):
    trip = _own_trip(trip_id)
    text = request.form.get('text', '').strip()
    if text:
        db.session.add(ChecklistItem(text=text, trip=trip))
        db.session.commit()
        flash('Пункт добавлен.', 'success')
    else:
        flash('Пункт не может быть пустым.', 'danger')
    return redirect(url_for('trips.detail', trip_id=trip.id))


@trip_bp.post('/checklist/<int:item_id>/toggle')
@login_required
def toggle_checklist_item(item_id):
    item = db.get_or_404(ChecklistItem, item_id)
    if item.trip.owner_id != current_user.id:
        abort(403)
    item.is_done = not item.is_done
    db.session.commit()
    return redirect(url_for('trips.detail', trip_id=item.trip_id))


@trip_bp.post('/checklist/<int:item_id>/delete')
@login_required
def delete_checklist_item(item_id):
    item = db.get_or_404(ChecklistItem, item_id)
    if item.trip.owner_id != current_user.id:
        abort(403)
    trip_id = item.trip_id
    db.session.delete(item)
    db.session.commit()
    flash('Пункт удалён.', 'info')
    return redirect(url_for('trips.detail', trip_id=trip_id))


@trip_bp.post('/<int:trip_id>/notes')
@login_required
def add_note(trip_id):
    trip = _own_trip(trip_id)
    title = request.form.get('title', 'Заметка').strip() or 'Заметка'
    text = request.form.get('content', '').strip()
    if not text:
        flash('Текст заметки не может быть пустым.', 'danger')
    else:
        db.session.add(Note(title=title, content=text, trip=trip))
        db.session.commit()
        flash('Заметка сохранена.', 'success')
    return redirect(url_for('trips.detail', trip_id=trip.id))


@trip_bp.post('/notes/<int:note_id>/delete')
@login_required
def delete_note(note_id):
    note = db.get_or_404(Note, note_id)
    if note.trip.owner_id != current_user.id:
        abort(403)
    trip_id = note.trip_id
    db.session.delete(note)
    db.session.commit()
    flash('Заметка удалена.', 'info')
    return redirect(url_for('trips.detail', trip_id=trip_id))


@trip_bp.post('/<int:trip_id>/documents')
@login_required
def upload_document(trip_id):
    trip = _own_trip(trip_id)
    file = request.files.get('document')
    if not file or not file.filename:
        flash('Выберите файл.', 'danger')
        return redirect(url_for('trips.detail', trip_id=trip.id))
    if not _file_ok(file.filename):
        flash('Можно загрузить только PDF, PNG, JPG или JPEG.', 'danger')
        return redirect(url_for('trips.detail', trip_id=trip.id))
    orig = secure_filename(file.filename)
    ext = Path(orig).suffix.lower()
    name = f'{uuid4().hex}{ext}'
    folder = current_app.config['UPLOAD_FOLDER'] / str(trip.id)
    folder.mkdir(parents=True, exist_ok=True)
    file.save(folder / name)
    db.session.add(
        Document(
            filename=name,
            original_name=orig,
            file_type=ext.lstrip('.'),
            trip=trip,
        )
    )
    db.session.commit()
    flash('Документ загружен.', 'success')
    return redirect(url_for('trips.detail', trip_id=trip.id))


@trip_bp.get('/documents/<int:document_id>')
@login_required
def download_document(document_id):
    document = db.get_or_404(Document, document_id)
    if document.trip.owner_id != current_user.id:
        abort(403)
    path = (
        current_app.config['UPLOAD_FOLDER'] / str(document.trip_id) / document.filename
    )
    return send_file(path, as_attachment=True, download_name=document.original_name)


@trip_bp.post('/documents/<int:document_id>/delete')
@login_required
def delete_document(document_id):
    document = db.get_or_404(Document, document_id)
    if document.trip.owner_id != current_user.id:
        abort(403)
    trip_id = document.trip_id
    path = current_app.config['UPLOAD_FOLDER'] / str(trip_id) / document.filename
    if path.exists():
        path.unlink()
    db.session.delete(document)
    db.session.commit()
    flash('Документ удалён.', 'info')
    return redirect(url_for('trips.detail', trip_id=trip_id))


@trip_bp.get('/<int:trip_id>/report.pdf')
@login_required
def report(trip_id):
    trip = _own_trip(trip_id)
    weather = get_weather_for_city(trip.destination)
    buf = generate_trip_pdf(trip, weather=weather)
    filename = f'tripplanner-{trip.id}.pdf'
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


@trip_bp.get('/share/<token>')
def shared(token):
    trip = Trip.query.filter_by(share_token=token).first_or_404()
    weather = get_weather_for_city(trip.destination)
    return render_template('trips/shared.html', trip=trip, weather=weather)


@trip_bp.post('/<int:trip_id>/delete')
@login_required
def delete_trip(trip_id):
    trip = _own_trip(trip_id)
    for doc in trip.documents:
        path = current_app.config['UPLOAD_FOLDER'] / str(trip.id) / doc.filename
        if path.exists():
            path.unlink()
    db.session.delete(trip)
    db.session.commit()
    flash('Поездка удалена.', 'info')
    return redirect(url_for('trips.dashboard'))
