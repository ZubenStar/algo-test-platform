from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, User
from decorators import admin_required

users_bp = Blueprint('users', __name__)


@users_bp.route('', methods=['GET'])
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({'users': [u.to_dict() for u in users]})


@users_bp.route('', methods=['POST'])
@login_required
@admin_required
def create_user():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'user')

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400

    if len(password) < 6:
        return jsonify({'error': '密码至少6位'}), 400

    if role not in ('admin', 'user'):
        return jsonify({'error': '角色只能是 admin 或 user'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': f'用户名 {username} 已存在'}), 409

    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': '用户创建成功', 'user': user.to_dict()}), 201


@users_bp.route('/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if 'role' in data:
        if data['role'] not in ('admin', 'user'):
            return jsonify({'error': '角色只能是 admin 或 user'}), 400
        # 不能修改自己的角色
        if user.id == current_user.id:
            return jsonify({'error': '不能修改自己的角色'}), 400
        user.role = data['role']

    if 'is_active' in data:
        if user.id == current_user.id:
            return jsonify({'error': '不能禁用自己的账号'}), 400
        user.is_active_user = data['is_active']

    if 'username' in data:
        new_name = data['username'].strip()
        if new_name and new_name != user.username:
            if User.query.filter_by(username=new_name).first():
                return jsonify({'error': f'用户名 {new_name} 已存在'}), 409
            user.username = new_name

    db.session.commit()
    return jsonify({'message': '更新成功', 'user': user.to_dict()})


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        return jsonify({'error': '不能删除自己'}), 400

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': '用户已删除'})


@users_bp.route('/<int:user_id>/reset-password', methods=['PUT'])
@login_required
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    new_password = data.get('new_password', 'admin123')

    if len(new_password) < 6:
        return jsonify({'error': '密码至少6位'}), 400

    user.set_password(new_password)
    user.force_change_password = True
    db.session.commit()

    return jsonify({'message': f'用户 {user.username} 密码已重置'})
