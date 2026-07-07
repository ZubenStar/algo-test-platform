from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from decorators import admin_required
from models import db, TestRun, TestResult, Algorithm, Core, SvnRevision
from datetime import datetime

tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('/trigger', methods=['POST'])
@login_required
@admin_required
def trigger_run():
    """手动触发一轮完整测试"""
    from tasks.celery_tasks import trigger_full_test_run

    # 创建一个虚拟的 SVN revision 记录（手动触发）
    latest_svn = SvnRevision.query.order_by(SvnRevision.id.desc()).first()

    run = TestRun(
        svn_revision_id=latest_svn.id if latest_svn else None,
        status='pending',
        triggered_by='manual',
        started_at=datetime.utcnow(),
    )

    algorithms = Algorithm.query.filter_by(is_active=True).all()
    cores = Core.query.filter_by(is_active=True).all()
    run.total_tasks = len(algorithms) * len(cores)

    db.session.add(run)
    db.session.commit()

    # 创建所有测试结果记录
    for algo in algorithms:
        for core in cores:
            result = TestResult(
                test_run_id=run.id,
                algorithm_id=algo.id,
                core_id=core.id,
                status='pending',
            )
            db.session.add(result)
    db.session.commit()

    # 异步触发 Celery 任务
    trigger_full_test_run.delay(run.id)

    return jsonify({
        'message': '测试任务已触发',
        'run': run.to_dict(),
    })


@tasks_bp.route('/running', methods=['GET'])
@login_required
def get_running():
    runs = TestRun.query.filter(
        TestRun.status.in_(['pending', 'running'])
    ).order_by(TestRun.id.desc()).all()
    return jsonify({'runs': [r.to_dict() for r in runs]})


@tasks_bp.route('/retry/<int:run_id>', methods=['POST'])
@login_required
@admin_required
def retry_failed(run_id):
    """重试失败的任务"""
    from tasks.celery_tasks import run_single_test

    run = TestRun.query.get_or_404(run_id)
    failed_results = TestResult.query.filter_by(
        test_run_id=run_id, status='failed'
    ).all()

    for r in failed_results:
        r.status = 'pending'
        r.error_message = None
    db.session.commit()

    run.status = 'running'
    run.failed_tasks = 0
    db.session.commit()

    for r in failed_results:
        run_single_test.delay(run_id, r.algorithm_id, r.core_id)

    return jsonify({
        'message': f'已重新提交 {len(failed_results)} 个失败任务',
    })
