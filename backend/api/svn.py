from flask import Blueprint, jsonify
from flask_login import login_required
from decorators import admin_required
from models import db, SvnRevision

svn_bp = Blueprint('svn', __name__)


@svn_bp.route('/status', methods=['GET'])
@login_required
def get_status():
    latest = SvnRevision.query.order_by(SvnRevision.id.desc()).first()
    return jsonify({
        'latest_revision': latest.to_dict() if latest else None,
    })


@svn_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    revisions = SvnRevision.query.order_by(
        SvnRevision.id.desc()
    ).limit(50).all()
    return jsonify({
        'revisions': [r.to_dict() for r in revisions],
    })


@svn_bp.route('/check', methods=['POST'])
@login_required
@admin_required
def manual_check():
    from services.svn_service import SvnService
    service = SvnService()
    has_update, revision = service.check_update()
    return jsonify({
        'has_update': has_update,
        'revision': revision.to_dict() if revision else None,
    })
