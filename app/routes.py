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

main_bp = Blueprint("main", __name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
trip_bp = Blueprint("trips", __name__, url_prefix="/trips")


def _parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def _allowed_file(filename):
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix in current_app.config["ALLOWED_EXTENSIONS"]


def _get_user_trip_or_404(trip_id):
    trip = db.get_or_404(Trip, trip_id)
    if trip.owner_id != current_user.id:
        abort(403)
    return trip


@main_bp.get("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("trips.dashboard"))
    return render_template("index.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("trips.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password_repeat = request.form.get("password_repeat", "")

        if not name or not email or not password:
            flash("Заполните имя, почту и пароль.", "danger")
        elif password != password_repeat:
            flash("Пароли не совпадают.", "danger")
        elif len(password) < 6:
            flash("Пароль должен быть не короче 6 символов.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("Пользователь с такой почтой уже существует.", "danger")
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Аккаунт создан. Можно планировать первую поездку.", "success")
            return redirect(url_for("trips.dashboard"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("trips.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=bool(request.form.get("remember")))
            flash("С возвращением.", "success")
            return redirect(url_for("trips.dashboard"))
        flash("Неверная почта или пароль.", "danger")

    return render_template("auth/login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("main.index"))


@trip_bp.get("/")
@login_required
def dashboard():
    query = request.args.get("q", "").strip()
    trips_query = Trip.query.filter_by(owner_id=current_user.id)
    if query:
        like_query = f"%{query}%"
        trips_query = trips_query.filter(
            or_(Trip.title.ilike(like_query), Trip.destination.ilike(like_query))
        )
    trips = trips_query.order_by(Trip.start_date.asc(), Trip.created_at.desc()).all()
    return render_template("trips/dashboard.html", trips=trips, query=query)


@trip_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        form_data = request.form.to_dict()
        try:
            start_date = _parse_date(form_data.get("start_date", ""))
            end_date = _parse_date(form_data.get("end_date", ""))
        except ValueError:
            flash("Проверьте даты поездки.", "danger")
            return render_template("trips/form.html", trip=None, form=form_data)

        if end_date < start_date:
            flash("Дата возвращения не может быть раньше даты начала.", "danger")
            return render_template("trips/form.html", trip=None, form=form_data)

        title = form_data.get("title", "").strip()
        destination = form_data.get("destination", "").strip()
        if not title or not destination:
            flash("Название и город обязательны.", "danger")
            return render_template("trips/form.html", trip=None, form=form_data)

        trip = Trip(
            title=title,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            budget=int(form_data.get("budget") or 0),
            description=form_data.get("description", "").strip(),
            owner=current_user,
        )
        db.session.add(trip)
        db.session.commit()
        flash("Поездка создана.", "success")
        return redirect(url_for("trips.detail", trip_id=trip.id))

    return render_template("trips/form.html", trip=None, form={})


@trip_bp.route("/<int:trip_id>/edit", methods=["GET", "POST"])
@login_required
def edit(trip_id):
    trip = _get_user_trip_or_404(trip_id)
    if request.method == "POST":
        form_data = request.form.to_dict()
        try:
            start_date = _parse_date(form_data.get("start_date", ""))
            end_date = _parse_date(form_data.get("end_date", ""))
        except ValueError:
            flash("Проверьте даты поездки.", "danger")
            return render_template("trips/form.html", trip=trip, form=form_data)

        if end_date < start_date:
            flash("Дата возвращения не может быть раньше даты начала.", "danger")
            return render_template("trips/form.html", trip=trip, form=form_data)

        trip.title = form_data.get("title", "").strip()
        trip.destination = form_data.get("destination", "").strip()
        trip.start_date = start_date
        trip.end_date = end_date
        trip.budget = int(form_data.get("budget") or 0)
        trip.description = form_data.get("description", "").strip()
        db.session.commit()
        flash("Поездка обновлена.", "success")
        return redirect(url_for("trips.detail", trip_id=trip.id))

    form = {
        "title": trip.title,
        "destination": trip.destination,
        "start_date": trip.start_date.isoformat(),
        "end_date": trip.end_date.isoformat(),
        "budget": trip.budget,
        "description": trip.description,
    }
    return render_template("trips/form.html", trip=trip, form=form)


@trip_bp.get("/<int:trip_id>")
@login_required
def detail(trip_id):
    trip = _get_user_trip_or_404(trip_id)
    weather = get_weather_for_city(trip.destination)
    share_url = url_for("trips.shared", token=trip.share_token, _external=True)
    return render_template(
        "trips/detail.html", trip=trip, weather=weather, share_url=share_url
    )


@trip_bp.post("/<int:trip_id>/checklist")
@login_required
def add_checklist_item(trip_id):
    trip = _get_user_trip_or_404(trip_id)
    text = request.form.get("text", "").strip()
    if text:
        db.session.add(ChecklistItem(text=text, trip=trip))
        db.session.commit()
        flash("Пункт добавлен.", "success")
    else:
        flash("Пункт не может быть пустым.", "danger")
    return redirect(url_for("trips.detail", trip_id=trip.id))


@trip_bp.post("/checklist/<int:item_id>/toggle")
@login_required
def toggle_checklist_item(item_id):
    item = db.get_or_404(ChecklistItem, item_id)
    if item.trip.owner_id != current_user.id:
        abort(403)
    item.is_done = not item.is_done
    db.session.commit()
    return redirect(url_for("trips.detail", trip_id=item.trip_id))


@trip_bp.post("/checklist/<int:item_id>/delete")
@login_required
def delete_checklist_item(item_id):
    item = db.get_or_404(ChecklistItem, item_id)
    if item.trip.owner_id != current_user.id:
        abort(403)
    trip_id = item.trip_id
    db.session.delete(item)
    db.session.commit()
    flash("Пункт удалён.", "info")
    return redirect(url_for("trips.detail", trip_id=trip_id))


@trip_bp.post("/<int:trip_id>/notes")
@login_required
def add_note(trip_id):
    trip = _get_user_trip_or_404(trip_id)
    title = request.form.get("title", "Заметка").strip() or "Заметка"
    content = request.form.get("content", "").strip()
    if not content:
        flash("Текст заметки не может быть пустым.", "danger")
    else:
        db.session.add(Note(title=title, content=content, trip=trip))
        db.session.commit()
        flash("Заметка сохранена.", "success")
    return redirect(url_for("trips.detail", trip_id=trip.id))


@trip_bp.post("/notes/<int:note_id>/delete")
@login_required
def delete_note(note_id):
    note = db.get_or_404(Note, note_id)
    if note.trip.owner_id != current_user.id:
        abort(403)
    trip_id = note.trip_id
    db.session.delete(note)
    db.session.commit()
    flash("Заметка удалена.", "info")
    return redirect(url_for("trips.detail", trip_id=trip_id))


@trip_bp.post("/<int:trip_id>/documents")
@login_required
def upload_document(trip_id):
    trip = _get_user_trip_or_404(trip_id)
    file = request.files.get("document")
    if not file or not file.filename:
        flash("Выберите файл.", "danger")
        return redirect(url_for("trips.detail", trip_id=trip.id))
    if not _allowed_file(file.filename):
        flash("Можно загрузить только PDF, PNG, JPG или JPEG.", "danger")
        return redirect(url_for("trips.detail", trip_id=trip.id))

    original_name = secure_filename(file.filename)
    suffix = Path(original_name).suffix.lower()
    storage_name = f"{uuid4().hex}{suffix}"
    trip_folder = current_app.config["UPLOAD_FOLDER"] / str(trip.id)
    trip_folder.mkdir(parents=True, exist_ok=True)
    file.save(trip_folder / storage_name)

    db.session.add(
        Document(
            filename=storage_name,
            original_name=original_name,
            file_type=suffix.lstrip("."),
            trip=trip,
        )
    )
    db.session.commit()
    flash("Документ загружен.", "success")
    return redirect(url_for("trips.detail", trip_id=trip.id))


@trip_bp.get("/documents/<int:document_id>")
@login_required
def download_document(document_id):
    document = db.get_or_404(Document, document_id)
    if document.trip.owner_id != current_user.id:
        abort(403)
    path = current_app.config["UPLOAD_FOLDER"] / str(document.trip_id) / document.filename
    return send_file(path, as_attachment=True, download_name=document.original_name)


@trip_bp.post("/documents/<int:document_id>/delete")
@login_required
def delete_document(document_id):
    document = db.get_or_404(Document, document_id)
    if document.trip.owner_id != current_user.id:
        abort(403)
    trip_id = document.trip_id
    path = current_app.config["UPLOAD_FOLDER"] / str(trip_id) / document.filename
    if path.exists():
        path.unlink()
    db.session.delete(document)
    db.session.commit()
    flash("Документ удалён.", "info")
    return redirect(url_for("trips.detail", trip_id=trip_id))


@trip_bp.get("/<int:trip_id>/report.pdf")
@login_required
def report(trip_id):
    trip = _get_user_trip_or_404(trip_id)
    weather = get_weather_for_city(trip.destination)
    buffer = generate_trip_pdf(trip, weather=weather)
    filename = f"tripplanner-{trip.id}.pdf"
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@trip_bp.get("/share/<token>")
def shared(token):
    trip = Trip.query.filter_by(share_token=token).first_or_404()
    weather = get_weather_for_city(trip.destination)
    return render_template("trips/shared.html", trip=trip, weather=weather)


@trip_bp.post("/<int:trip_id>/delete")
@login_required
def delete_trip(trip_id):
    trip = _get_user_trip_or_404(trip_id)
    for document in trip.documents:
        path = current_app.config["UPLOAD_FOLDER"] / str(trip.id) / document.filename
        if path.exists():
            path.unlink()
    db.session.delete(trip)
    db.session.commit()
    flash("Поездка удалена.", "info")
    return redirect(url_for("trips.dashboard"))
