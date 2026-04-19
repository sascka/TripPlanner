import secrets
from datetime import date, datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    trips = db.relationship("Trip", back_populates="owner", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
        }


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    destination = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    budget = db.Column(db.Integer, default=0, nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    share_token = db.Column(db.String(48), unique=True, index=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    owner = db.relationship("User", back_populates="trips")
    checklist_items = db.relationship(
        "ChecklistItem",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="ChecklistItem.created_at.asc()",
    )
    notes = db.relationship(
        "Note",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="Note.created_at.desc()",
    )
    documents = db.relationship(
        "Document",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="Document.uploaded_at.desc()",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.share_token:
            self.share_token = secrets.token_urlsafe(24)

    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1

    @property
    def is_upcoming(self):
        return self.start_date >= date.today()

    @property
    def completed_items_count(self):
        return sum(1 for item in self.checklist_items if item.is_done)

    @property
    def progress_percent(self):
        if not self.checklist_items:
            return 0
        return round(self.completed_items_count / len(self.checklist_items) * 100)

    def to_dict(self, include_private=False, include_children=False):
        data = {
            "id": self.id,
            "title": self.title,
            "destination": self.destination,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "duration_days": self.duration_days,
            "budget": self.budget,
            "description": self.description,
            "progress_percent": self.progress_percent,
            "notes_count": len(self.notes),
            "documents_count": len(self.documents),
        }
        if include_private:
            data["share_token"] = self.share_token
        if include_children:
            data["checklist"] = [item.to_dict() for item in self.checklist_items]
            data["notes"] = [note.to_dict() for note in self.notes]
            data["documents"] = [document.to_dict() for document in self.documents]
        return data


class ChecklistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    trip_id = db.Column(db.Integer, db.ForeignKey("trip.id"), nullable=False)
    trip = db.relationship("Trip", back_populates="checklist_items")

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "is_done": self.is_done,
            "created_at": self.created_at.isoformat(),
        }


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    trip_id = db.Column(db.Integer, db.ForeignKey("trip.id"), nullable=False)
    trip = db.relationship("Trip", back_populates="notes")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    trip_id = db.Column(db.Integer, db.ForeignKey("trip.id"), nullable=False)
    trip = db.relationship("Trip", back_populates="documents")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "original_name": self.original_name,
            "file_type": self.file_type,
            "uploaded_at": self.uploaded_at.isoformat(),
        }
