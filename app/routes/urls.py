import csv
import io
import random
import string
from datetime import datetime
from flask import Blueprint, jsonify, request, redirect
import structlog
from playhouse.shortcuts import model_to_dict
from peewee import chunked, fn, JOIN
from peewee import DataError, IntegrityError
from app.database import db
from app.models import Url
from app.models.event import Event
from app.routes.metrics import urls_created_total, redirects_total

log = structlog.get_logger(__name__)
urls_bp = Blueprint("urls", __name__)

_SORT_FIELDS = {
    'id': Url.id,
    'created_at': Url.created_at,
    'updated_at': Url.updated_at,
    'short_code': Url.short_code,
    'original_url': Url.original_url,
}


def generate_short_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def url_to_dict(url):
    d = model_to_dict(url, recurse=False)
    d['click_count'] = Event.select().where(
        (Event.url_id == url.id) & (Event.event_type == 'click')
    ).count()
    return d


def _get_url_or_404(id):
    try:
        return Url.get_by_id(id), None
    except Url.DoesNotExist:
        return None, (jsonify({"error": "URL not found"}), 404)


@urls_bp.route("/urls", methods=["GET"])
def list_urls():
    page      = request.args.get('page', 1, type=int)
    per_page  = request.args.get('per_page', 50, type=int)
    sort_by   = request.args.get('sort_by', 'id')
    order     = request.args.get('order', 'asc')

    query = Url.select()
    if user_id := request.args.get('user_id', type=int):
        query = query.where(Url.user_id == user_id)
    if (is_active := request.args.get('is_active')) is not None:
        query = query.where(Url.is_active == (is_active.lower() == 'true'))
    if short_code := request.args.get('short_code'):
        query = query.where(Url.short_code == short_code)

    sort_field = _SORT_FIELDS.get(sort_by, Url.id)
    query = query.order_by(sort_field.desc() if order == 'desc' else sort_field.asc())
    return jsonify([url_to_dict(u) for u in query.paginate(page, per_page)])


@urls_bp.route("/urls/top", methods=["GET"])
def top_urls():
    n = request.args.get('n', 10, type=int)
    results = (
        Url.select(Url, fn.COUNT(Event.id).alias('click_count'))
        .join(Event, JOIN.LEFT_OUTER, on=(Event.url_id == Url.id) & (Event.event_type == 'click'))
        .group_by(Url.id)
        .order_by(fn.COUNT(Event.id).desc())
        .limit(n)
    )
    out = [{**model_to_dict(u, recurse=False), 'click_count': getattr(u, 'click_count', 0)} for u in results]
    return jsonify(out)


@urls_bp.route("/urls/<int:id>/stats", methods=["GET"])
def get_url_stats(id):
    url, err = _get_url_or_404(id)
    if err:
        return err
    events = Event.select().where(Event.url_id == id)
    clicks = events.where(Event.event_type == 'click')
    last_click = clicks.order_by(Event.timestamp.desc()).first()
    return jsonify({
        "url_id": id,
        "short_code": url.short_code,
        "click_count": clicks.count(),
        "unique_users": events.where(Event.user_id.is_null(False)).select(Event.user_id).distinct().count(),
        "last_clicked_at": last_click.timestamp.isoformat() if last_click else None,
    })


@urls_bp.route("/urls/<int:id>", methods=["GET"])
def get_url(id):
    url, err = _get_url_or_404(id)
    return err or jsonify(url_to_dict(url))


@urls_bp.route("/urls/<short_code>", methods=["GET"])
def get_url_by_short_code(short_code):
    try:
        return jsonify(url_to_dict(Url.get(Url.short_code == short_code)))
    except Url.DoesNotExist:
        return jsonify({"error": "URL not found"}), 404


@urls_bp.route("/urls", methods=["POST"])
def create_url():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid data"}), 400
    if not data.get('original_url'):
        return jsonify({"error": "original_url required"}), 400

    user_id = data.get('user_id')
    if user_id is None:
        return jsonify({"error": "user_id required"}), 400
    if not isinstance(user_id, int):
        return jsonify({"error": "user_id must be an integer"}), 400
    if not Url.user_id.rel_model.select().where(Url.user_id.rel_model.id == user_id).exists():
        return jsonify({"error": "User not found"}), 404

    original_url = data['original_url']
    if not isinstance(original_url, str) or not (original_url.startswith('http://') or original_url.startswith('https://')):
        return jsonify({"error": "original_url must be a valid URL"}), 400
    if data.get('title') is not None and not isinstance(data.get('title'), str):
        return jsonify({"error": "title must be a string"}), 400
    if 'is_active' in data and not isinstance(data['is_active'], bool):
        return jsonify({"error": "is_active must be a boolean"}), 400
    if explicit_code := data.get('short_code'):
        if not isinstance(explicit_code, str) or not explicit_code:
            return jsonify({"error": "short_code must be a non-empty string"}), 400
        if len(explicit_code) > 10:
            return jsonify({"error": "short_code must be <= 10 chars"}), 400
        if Url.select().where(Url.short_code == explicit_code).exists():
            return jsonify({"error": "short_code already exists"}), 409
        short_code = explicit_code
    else:
        short_code = generate_short_code()
        while Url.select().where(Url.short_code == short_code).exists():
            short_code = generate_short_code()
    try:
        url = Url.create(
            user_id=user_id,
            short_code=short_code,
            original_url=data['original_url'],
            title=data.get('title'),
            is_active=data.get('is_active', True),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    except (DataError, IntegrityError, ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400
    urls_created_total.inc()
    return jsonify(url_to_dict(url)), 201


@urls_bp.route("/urls/<int:id>", methods=["PUT"])
def update_url(id):
    url, err = _get_url_or_404(id)
    if err:
        return err
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid data"}), 400
    if 'original_url' in data:
        if not isinstance(data['original_url'], str) or not (data['original_url'].startswith('http://') or data['original_url'].startswith('https://')):
            return jsonify({"error": "original_url must be a valid URL"}), 400
    if 'title' in data and data['title'] is not None and not isinstance(data['title'], str):
        return jsonify({"error": "title must be a string"}), 400
    if 'is_active' in data and not isinstance(data['is_active'], bool):
        return jsonify({"error": "is_active must be a boolean"}), 400
    for field in ('original_url', 'title', 'is_active'):
        if field in data:
            setattr(url, field, data[field])
    url.updated_at = datetime.now()
    try:
        url.save()
    except (DataError, IntegrityError, ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(url_to_dict(url))


@urls_bp.route("/urls/<int:id>", methods=["DELETE"])
def delete_url(id):
    deleted = Url.delete().where(Url.id == id).execute()
    return (jsonify({"message": "Deleted"}), 200) if deleted else (jsonify({"error": "URL not found"}), 404)


@urls_bp.route("/urls/bulk", methods=["POST"])
def bulk_upload_urls():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    reader = csv.DictReader(io.StringIO(request.files['file'].read().decode('utf-8')))
    rows = [
        {
            'id': int(r['id']),
            'user_id': int(r['user_id']),
            'short_code': r['short_code'],
            'original_url': r['original_url'],
            'title': r['title'],
            'is_active': r['is_active'] == 'TRUE',
            'created_at': r['created_at'],
            'updated_at': r['updated_at'],
        }
        for r in reader
    ]
    with db.atomic():
        for batch in chunked(rows, 1000):
            Url.insert_many(batch).execute()
    try:
        db.execute_sql("SELECT setval(pg_get_serial_sequence('urls', 'id'), MAX(id)) FROM urls")
    except Exception:
        pass
    return jsonify({"count": len(rows)}), 201


@urls_bp.route("/<short_code>", methods=["GET"])
def redirect_url(short_code):
    try:
        url = Url.get(Url.short_code == short_code)
        if not url.is_active:
            return jsonify({"error": "URL is inactive"}), 410
        with db.atomic():
            Event.create(
                url_id=url.id,
                user_id=None,
                event_type="click",
                timestamp=datetime.now(),
                details=None,
            )
            redirects_total.inc()
        return redirect(url.original_url, code=302)
    except Url.DoesNotExist:
        log.warning("redirect.not_found", short_code=short_code)
        return jsonify({"error": "URL not found"}), 404
