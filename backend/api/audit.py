from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy.orm import joinedload

from decorators import admin_required
from models import AuditLog


audit_bp = Blueprint('audit', __name__)


@audit_bp.route('', methods=['GET'])
@login_required
@admin_required
def list_audit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    query = AuditLog.query.options(joinedload(AuditLog.user)).order_by(AuditLog.id.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'logs': [item.to_dict() for item in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    })
