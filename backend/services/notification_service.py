import json

import redis
from flask import current_app

from models import Notification, User, db
from services.db_session import safe_commit


NOTIFICATION_CHANNEL = 'notifications'


class NotificationService:
    @staticmethod
    def create_for_all(message, notification_type='info'):
        users = User.query.filter_by(is_active_user=True).all()
        notifications = [
            Notification(user_id=user.id, type=notification_type, message=message)
            for user in users
        ]
        db.session.add_all(notifications)
        safe_commit()
        NotificationService.publish({
            'type': notification_type,
            'message': message,
        })
        return notifications

    @staticmethod
    def publish(payload):
        try:
            client = redis.from_url(current_app.config['REDIS_URL'])
            client.publish(NOTIFICATION_CHANNEL, json.dumps(payload, ensure_ascii=False))
        except redis.RedisError:
            current_app.logger.warning('Notification publish failed', exc_info=True)
