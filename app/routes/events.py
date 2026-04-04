import csv
import io
from datetime import datetime
from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict
from peewee import chunked
from app.database import db
from app.models import Event

events_bp = Blueprint("events", __name__)

@events_bp.route("/events", methods=["GET"])
def list_events():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    events = Event.select().paginate(page, per_page)
    return jsonify([model_to_dict(e) for e in events])

@events_bp.route("/events/<int:id>", methods=["GET"])
def get_event(id):
    try:
        event = Event.get_by_id(id)
        return jsonify(model_to_dict(event))
    except Event.DoesNotExist:
        return jsonify({"error": "Event not found"}), 404

@events_bp.route("/events", methods=["POST"])
def create_event():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    event = Event.create(
        url_id=data.get('url_id'),
        user_id=data.get('user_id'),
        event_type=data.get('event_type'),
        timestamp=datetime.now(),
        details=data.get('details')
    )
    return jsonify(model_to_dict(event)), 201

@events_bp.route("/events/bulk", methods=["POST"])
def bulk_upload_events():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    content = file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for row in reader:
        rows.append({
            'id': int(row['id']),
            'url_id': int(row['url_id']),
            'user_id': int(row['user_id']),
            'event_type': row['event_type'],
            'timestamp': row['timestamp'],
            'details': row['details']
        })
    with db.atomic():
        for batch in chunked(rows, 100):
            Event.insert_many(batch).execute()
    return jsonify({"count": len(rows)}), 201
