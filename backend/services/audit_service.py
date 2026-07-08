from functools import wraps

from flask import request
from flask_login import current_user

from models import AuditLog, db
from services.db_session import safe_commit


def audit_log(action, target_type):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            status_code = _status_code(response)
            if status_code < 400 and current_user.is_authenticated:
                log = AuditLog(
                    user_id=current_user.id,
                    action=action,
                    target_type=target_type,
                    target_id=str(_target_id(kwargs)),
                    detail=request.get_json(silent=True) or {},
                )
                db.session.add(log)
                safe_commit()
            return response
        return wrapper
    return decorator


def _status_code(response):
    if isinstance(response, tuple) and len(response) > 1:
        return response[1]
    return getattr(response, 'status_code', 200)


def _target_id(kwargs):
    for key in ('user_id', 'algo_id', 'core_id', 'run_id'):
        if key in kwargs:
            return kwargs[key]
    return ''
