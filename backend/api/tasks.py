from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from decorators import admin_required
from models import ResultStatus, RunStatus, TestRun, TestResult
from services.audit_service import audit_log
from services.db_session import safe_commit
from services.test_run_service import TestRunService

tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('/trigger', methods=['POST'])
@login_required
@admin_required
@audit_log('trigger', 'test_run')
def trigger_run():
    """手动触发一轮完整测试"""
    from tasks.celery_tasks import trigger_full_test_run

    run = TestRunService.create_run('manual')

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
        TestRun.status.in_([RunStatus.PENDING, RunStatus.RUNNING])
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
        test_run_id=run_id, status=ResultStatus.FAILED
    ).all()

    for r in failed_results:
        r.status = ResultStatus.PENDING
        r.error_message = None
    safe_commit()

    run.status = RunStatus.RUNNING
    run.failed_tasks = 0
    safe_commit()

    for r in failed_results:
        run_single_test.delay(run_id, r.algorithm_id, r.core_id)

    return jsonify({
        'message': f'已重新提交 {len(failed_results)} 个失败任务',
    })
