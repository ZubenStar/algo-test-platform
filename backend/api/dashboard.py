from flask import Blueprint, jsonify, request
from flask_login import login_required
from models import Algorithm, Core, ResultStatus, RunStatus, SvnRevision, TestResult, TestRun, db
from sqlalchemy import case, func
from sqlalchemy.orm import joinedload

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('', methods=['GET'])
@login_required
def get_dashboard():
    algo_count = Algorithm.query.filter_by(is_active=True).count()
    core_count = Core.query.filter_by(is_active=True).count()

    # 最近一次测试运行
    latest_run = TestRun.query.options(
        joinedload(TestRun.svn_revision)
    ).order_by(TestRun.id.desc()).first()
    latest_run_dict = latest_run.to_dict() if latest_run else None

    # 最近一次 SVN revision
    latest_svn = SvnRevision.query.order_by(SvnRevision.id.desc()).first()
    latest_svn_dict = latest_svn.to_dict() if latest_svn else None

    # 最近一次测试的通过率
    pass_rate = None
    if latest_run and latest_run.total_tasks > 0:
        passed = TestResult.query.filter_by(
            test_run_id=latest_run.id, status=ResultStatus.PASSED
        ).count()
        pass_rate = round(passed / latest_run.total_tasks * 100, 1)

    return jsonify({
        'algo_count': algo_count,
        'core_count': core_count,
        'latest_run': latest_run_dict,
        'latest_svn': latest_svn_dict,
        'pass_rate': pass_rate,
    })


@dashboard_bp.route('/matrix/<int:run_id>', methods=['GET'])
@login_required
def get_matrix(run_id):
    """获取算法×核的矩阵数据"""
    results = TestResult.query.options(
        joinedload(TestResult.algorithm),
        joinedload(TestResult.core),
    ).filter_by(test_run_id=run_id).all()

    matrix = {}
    for r in results:
        algo_name = r.algorithm.display_name or r.algorithm.name
        core_name = r.core.display_name or r.core.name
        if algo_name not in matrix:
            matrix[algo_name] = {}
        matrix[algo_name][core_name] = {
            'status': r.status,
            'pass_count': r.pass_count,
            'fail_count': r.fail_count,
            'total_count': r.total_count,
        }

    # 获取所有算法和核的名称
    algorithms = [r.algorithm.display_name or r.algorithm.name for r in results]
    cores = [r.core.display_name or r.core.name for r in results]
    algorithms = list(dict.fromkeys(algorithms))  # 去重保序
    cores = list(dict.fromkeys(cores))

    return jsonify({
        'matrix': matrix,
        'algorithms': algorithms,
        'cores': cores,
    })


@dashboard_bp.route('/trend', methods=['GET'])
@login_required
def get_trend():
    """获取最近 N 次测试的通过率趋势"""
    limit = request.args.get('limit', 10, type=int)
    runs = TestRun.query.options(
        joinedload(TestRun.svn_revision)
    ).filter_by(status=RunStatus.COMPLETED).order_by(TestRun.id.desc()).limit(limit).all()
    runs.reverse()
    run_ids = [run.id for run in runs]
    passed_stats = {}
    if run_ids:
        passed_stats = dict(db.session.query(
            TestResult.test_run_id,
            func.sum(case((TestResult.status == ResultStatus.PASSED, 1), else_=0)),
        ).filter(
            TestResult.test_run_id.in_(run_ids)
        ).group_by(TestResult.test_run_id).all())

    trend = []
    for run in runs:
        total = run.total_tasks
        passed = int(passed_stats.get(run.id) or 0)
        rate = round(passed / total * 100, 1) if total > 0 else 0
        trend.append({
            'run_id': run.id,
            'svn_revision': run.svn_revision.revision if run.svn_revision else '-',
            'pass_rate': rate,
            'total': total,
            'passed': passed,
            'failed': run.failed_tasks,
            'started_at': run.started_at.isoformat() if run.started_at else None,
        })

    return jsonify({'trend': trend})
