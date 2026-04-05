import csv
import io
import json
from datetime import datetime
from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict
from peewee import chunked, fn
from app.database import db
from app.models import Event

events_bp = Blueprint("events", __name__)

_CREATE_FIELDS = {'url_id', 'user_id', 'event_type', 'details'}


def event_to_dict(e):
    d = model_to_dict(e, recurse=False)
    if isinstance(d.get('details'), str):
        try:
            d['details'] = json.loads(d['details'])
        except (json.JSONDecodeError, TypeError):
            pass
    if d.get('timestamp') is not None and not isinstance(d['timestamp'], str):
        d['timestamp'] = d['timestamp'].isoformat()
    return d


def _apply_filters(query):
    raw_url_id = request.args.get('url_id')
    if raw_url_id is not None:
        try:
            url_id = int(raw_url_id)
        except (TypeError, ValueError):
            return None, (jsonify({"error": "url_id must be an integer"}), 400)
        query = query.where(Event.url_id == url_id)
    raw_user_id = request.args.get('user_id')
    if raw_user_id is not None:
        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError):
            return None, (jsonify({"error": "user_id must be an integer"}), 400)
        query = query.where(Event.user_id == user_id)
    if event_type := request.args.get('event_type'):
        query = query.where(Event.event_type == event_type)
    return query, None


@events_bp.route("/events", methods=["GET"])
def list_events():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    query, err = _apply_filters(Event.select())
    if err:
        return err
    return jsonify([event_to_dict(e) for e in query.paginate(page, per_page)])


@events_bp.route("/events/summary", methods=["GET"])
def events_summary():
    query, err = _apply_filters(Event.select())
    if err:
        return err
    rows = (
        query.select(Event.event_type, fn.COUNT(Event.id).alias('count'))
        .group_by(Event.event_type)
        .tuples()
    )
    by_type = {row[0]: row[1] for row in rows}
    return jsonify({"total": sum(by_type.values()), "by_type": by_type})


@events_bp.route("/events/<int:id>", methods=["GET"])
def get_event(id):
    try:
        return jsonify(event_to_dict(Event.get_by_id(id)))
    except Event.DoesNotExist:
        return jsonify({"error": "Event not found"}), 404


@events_bp.route("/events", methods=["POST"])
def create_event():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid data"}), 400
    unknown_fields = set(data.keys()) - _CREATE_FIELDS
    if unknown_fields:
        return jsonify({"error": "Invalid data"}), 400
    if data.get('url_id') is None:
        return jsonify({"error": "url_id required"}), 400
    if not isinstance(data.get('url_id'), int) or isinstance(data.get('url_id'), bool):
        return jsonify({"error": "url_id must be an integer"}), 400
    if not Event.url_id.rel_model.select().where(Event.url_id.rel_model.id == data['url_id']).exists():
        return jsonify({"error": "invalid url_id"}), 404
    if not isinstance(data.get('event_type'), str) or not data.get('event_type').strip():
        return jsonify({"error": "event_type required"}), 400
    if data.get('user_id') is not None and (not isinstance(data.get('user_id'), int) or isinstance(data.get('user_id'), bool)):
        return jsonify({"error": "user_id must be an integer"}), 400
    if data.get('user_id') is not None and not Event.user_id.rel_model.select().where(Event.user_id.rel_model.id == data['user_id']).exists():
        return jsonify({"error": "invalid user_id"}), 404
    if data.get('details') is not None and not isinstance(data['details'], dict):
        return jsonify({"error": "details must be an object"}), 400
    try:
        event = Event.create(
            url_id=data['url_id'],
            user_id=data.get('user_id'),
            event_type=data['event_type'],
            timestamp=datetime.now(),
            details=json.dumps(data['details']) if data.get('details') is not None else None,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(event_to_dict(event)), 201


@events_bp.route("/events/bulk", methods=["POST"])
def bulk_upload_events():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    reader = csv.DictReader(io.StringIO(request.files['file'].read().decode('utf-8')))
    rows = [
        {
            'id': int(r['id']),
            'url_id': int(r['url_id']),
            'user_id': int(r['user_id']),
            'event_type': r['event_type'],
            'timestamp': r['timestamp'],
            'details': r['details'],
        }
        for r in reader
    ]
    with db.atomic():
        for batch in chunked(rows, 1000):
            Event.insert_many(batch).execute()
    return jsonify({"count": len(rows)}), 201
