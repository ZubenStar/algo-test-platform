from flask import Blueprint, jsonify, request
from flask_login import login_required
from models import db, ConsistencyReport, TestResult

consistency_bp = Blueprint('consistency', __name__)


@consistency_bp.route('/<int:run_id>', methods=['GET'])
@login_required
def get_report(run_id):
    reports = ConsistencyReport.query.filter_by(test_run_id=run_id).all()
    return jsonify({
        'reports': [r.to_dict() for r in reports],
    })


@consistency_bp.route('/trend/<int:algo_id>', methods=['GET'])
@login_required
def get_trend(algo_id):
    limit = request.args.get('limit', 20, type=int)
    reports = ConsistencyReport.query.filter_by(
        algorithm_id=algo_id
    ).order_by(ConsistencyReport.id.desc()).limit(limit).all()
    reports.reverse()

    trend = []
    for r in reports:
        trend.append({
            'test_run_id': r.test_run_id,
            'is_consistent': r.is_consistent,
            'max_diff': r.max_diff,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        })

    return jsonify({'trend': trend})
