from flask import Blueprint, jsonify, request
from flask_login import login_required
from models import db, TestRun, TestResult

results_bp = Blueprint('results', __name__)


@results_bp.route('/runs', methods=['GET'])
@login_required
def list_runs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')

    query = TestRun.query.order_by(TestRun.id.desc())
    if status:
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'runs': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    })


@results_bp.route('/<int:run_id>', methods=['GET'])
@login_required
def get_run_results(run_id):
    run = TestRun.query.get_or_404(run_id)

    algo_id = request.args.get('algorithm_id', type=int)
    core_id = request.args.get('core_id', type=int)
    status = request.args.get('status')

    query = TestResult.query.filter_by(test_run_id=run_id)
    if algo_id:
        query = query.filter_by(algorithm_id=algo_id)
    if core_id:
        query = query.filter_by(core_id=core_id)
    if status:
        query = query.filter_by(status=status)

    results = query.all()
    return jsonify({
        'run': run.to_dict(),
        'results': [r.to_dict() for r in results],
    })


@results_bp.route('/detail/<int:result_id>', methods=['GET'])
@login_required
def get_result_detail(result_id):
    result = TestResult.query.get_or_404(result_id)
    data = result.to_dict()

    # 读取日志文件（如果有）
    log_content = None
    if result.log_file:
        try:
            with open(result.log_file, 'r') as f:
                log_content = f.read()
        except Exception:
            log_content = None
    data['log_content'] = log_content

    return jsonify({'result': data})
