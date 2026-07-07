from functools import wraps
from flask import jsonify
from flask_login import current_user


def admin_required(f):
    """要求管理员权限的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': '未登录'}), 401
        if not current_user.is_admin():
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function
