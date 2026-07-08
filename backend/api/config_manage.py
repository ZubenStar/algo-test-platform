from flask import Blueprint, jsonify, request
from flask_login import login_required
from decorators import admin_required
from models import db, Algorithm, Core
from services.audit_service import audit_log
from services.db_session import safe_commit

config_bp = Blueprint('config', __name__)


# ---- Algorithms ----
@config_bp.route('/algorithms', methods=['GET'])
@login_required
def list_algorithms():
    algos = Algorithm.query.order_by(Algorithm.id).all()
    return jsonify({'algorithms': [a.to_dict() for a in algos]})


@config_bp.route('/algorithms', methods=['POST'])
@login_required
@admin_required
@audit_log('create', 'algorithm')
def create_algorithm():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '算法名称不能为空'}), 400

    if Algorithm.query.filter_by(name=name).first():
        return jsonify({'error': f'算法 {name} 已存在'}), 409

    algo = Algorithm(
        name=name,
        display_name=data.get('display_name', name),
        script_path=data.get('script_path', ''),
        description=data.get('description', ''),
    )
    db.session.add(algo)
    safe_commit()
    return jsonify({'message': '创建成功', 'algorithm': algo.to_dict()}), 201


@config_bp.route('/algorithms/<int:algo_id>', methods=['PUT'])
@login_required
@admin_required
@audit_log('update', 'algorithm')
def update_algorithm(algo_id):
    algo = Algorithm.query.get_or_404(algo_id)
    data = request.get_json()

    if 'display_name' in data:
        algo.display_name = data['display_name']
    if 'script_path' in data:
        algo.script_path = data['script_path']
    if 'description' in data:
        algo.description = data['description']
    if 'is_active' in data:
        algo.is_active = data['is_active']

    safe_commit()
    return jsonify({'message': '更新成功', 'algorithm': algo.to_dict()})


@config_bp.route('/algorithms/<int:algo_id>', methods=['DELETE'])
@login_required
@admin_required
@audit_log('delete', 'algorithm')
def delete_algorithm(algo_id):
    algo = Algorithm.query.get_or_404(algo_id)
    db.session.delete(algo)
    safe_commit()
    return jsonify({'message': '已删除'})


# ---- Cores ----
@config_bp.route('/cores', methods=['GET'])
@login_required
def list_cores():
    cores = Core.query.order_by(Core.id).all()
    return jsonify({'cores': [c.to_dict() for c in cores]})


@config_bp.route('/cores', methods=['POST'])
@login_required
@admin_required
@audit_log('create', 'core')
def create_core():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '核名称不能为空'}), 400

    if Core.query.filter_by(name=name).first():
        return jsonify({'error': f'核 {name} 已存在'}), 409

    core = Core(
        name=name,
        display_name=data.get('display_name', name),
        arch=data.get('arch', ''),
        sim_cmd_template=data.get('sim_cmd_template', ''),
    )
    db.session.add(core)
    safe_commit()
    return jsonify({'message': '创建成功', 'core': core.to_dict()}), 201


@config_bp.route('/cores/<int:core_id>', methods=['PUT'])
@login_required
@admin_required
@audit_log('update', 'core')
def update_core(core_id):
    core = Core.query.get_or_404(core_id)
    data = request.get_json()

    if 'display_name' in data:
        core.display_name = data['display_name']
    if 'arch' in data:
        core.arch = data['arch']
    if 'sim_cmd_template' in data:
        core.sim_cmd_template = data['sim_cmd_template']
    if 'is_active' in data:
        core.is_active = data['is_active']

    safe_commit()
    return jsonify({'message': '更新成功', 'core': core.to_dict()})


@config_bp.route('/cores/<int:core_id>', methods=['DELETE'])
@login_required
@admin_required
@audit_log('delete', 'core')
def delete_core(core_id):
    core = Core.query.get_or_404(core_id)
    db.session.delete(core)
    safe_commit()
    return jsonify({'message': '已删除'})
