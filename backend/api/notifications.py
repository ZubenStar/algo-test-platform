import json
import time

import redis
from flask import Blueprint, Response, current_app, jsonify, stream_with_context
from flask_login import current_user, login_required

from models import Notification
from services.db_session import safe_commit
from services.notification_service import NOTIFICATION_CHANNEL


notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('', methods=['GET'])
@login_required
def list_notifications():
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.id.desc()).limit(30).all()
    unread_count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False,
    ).count()
    return jsonify({
        'notifications': [item.to_dict() for item in notifications],
        'unread_count': unread_count,
    })


@notifications_bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id,
    ).first_or_404()
    notification.is_read = True
    safe_commit()
    return jsonify({'message': '已读'})


@notifications_bp.route('/stream', methods=['GET'])
@login_required
def stream():
    return Response(stream_with_context(_event_stream()), mimetype='text/event-stream')


def _event_stream():
    yield ': connected\n\n'
    try:
        client = redis.from_url(current_app.config['REDIS_URL'])
        pubsub = client.pubsub()
        pubsub.subscribe(NOTIFICATION_CHANNEL)
        while True:
            message = pubsub.get_message(timeout=25)
            if message and message['type'] == 'message':
                data = message['data'].decode('utf-8')
                yield f'data: {data}\n\n'
            else:
                yield ': ping\n\n'
    except redis.RedisError:
        payload = json.dumps({'type': 'error', 'message': 'notification stream unavailable'})
        yield f'data: {payload}\n\n'
        time.sleep(1)
