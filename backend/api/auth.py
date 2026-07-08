from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf

from extensions import csrf, limiter
from models import User
from services.db_session import safe_commit


auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
@csrf.exempt
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': '用户名或密码错误'}), 401

    if not user.is_active_user:
        return jsonify({'error': '账号已被禁用'}), 403

    login_user(user, remember=True)
    user.last_login = datetime.utcnow()
    safe_commit()

    response = jsonify({
        'message': '登录成功',
        'user': user.to_dict(),
        'force_change_password': user.force_change_password,
    })
    response.set_cookie('csrf_token', generate_csrf(), httponly=False, samesite='Lax')
    return response


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    response = jsonify({'message': '已注销'})
    response.delete_cookie('csrf_token')
    return response


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_me():
    return jsonify({'user': current_user.to_dict()})


@auth_bp.route('/password', methods=['PUT'])
@login_required
def change_password():
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'error': '旧密码和新密码不能为空'}), 400

    if not current_user.check_password(old_password):
        return jsonify({'error': '旧密码错误'}), 400

    if len(new_password) < 6:
        return jsonify({'error': '新密码至少6位'}), 400

    current_user.set_password(new_password)
    current_user.force_change_password = False
    safe_commit()

    return jsonify({'message': '密码修改成功'})
