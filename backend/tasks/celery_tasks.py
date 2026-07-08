import os
from celery import Celery, group
from datetime import datetime


# 创建 Celery 实例，从环境变量读取 Redis URL
_redis_url = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
celery_app = Celery('algo_test', broker=_redis_url, backend=_redis_url)


def make_celery(app):
    """从 Flask app 配置 Celery"""
    celery_app.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone='Asia/Shanghai',
        enable_utc=True,
    )

    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
    return celery_app


@celery_app.task(bind=True, max_retries=2)
def trigger_full_test_run(self, test_run_id):
    """触发一轮完整的仿真测试"""
    from models import ResultStatus, RunStatus, TestResult, TestRun
    from services.db_session import safe_commit

    run = TestRun.query.get(test_run_id)
    if not run:
        return {'error': 'Test run not found'}

    run.status = RunStatus.RUNNING
    run.started_at = datetime.utcnow()
    safe_commit()

    # 获取所有待测任务
    pending_results = TestResult.query.filter_by(
        test_run_id=test_run_id, status=ResultStatus.PENDING
    ).all()

    if not pending_results:
        run.status = RunStatus.COMPLETED
        run.finished_at = datetime.utcnow()
        safe_commit()
        return {'message': 'No pending tasks'}

    # 并行提交所有子任务
    subtasks = []
    for r in pending_results:
        subtasks.append(run_single_test.s(test_run_id, r.algorithm_id, r.core_id))

    job = group(subtasks)
    job.apply_async()

    return {'message': f'Submitted {len(subtasks)} tasks'}


@celery_app.task(bind=True, max_retries=1)
def run_single_test(self, test_run_id, algorithm_id, core_id):
    """执行单个算法×核的仿真测试"""
    from models import ResultStatus, TestResult, TestRun
    from services.db_session import safe_commit
    from services.simulator_service import SimulatorService

    try:
        service = SimulatorService()
        result = service.run_algorithm_on_core(test_run_id, algorithm_id, core_id)

        # 更新 test_run 进度
        run = TestRun.query.get(test_run_id)
        if run:
            completed = TestResult.query.filter_by(
                test_run_id=test_run_id
            ).filter(TestResult.status.in_([
                ResultStatus.PASSED,
                ResultStatus.FAILED,
                ResultStatus.ERROR,
            ])).count()

            failed = TestResult.query.filter_by(
                test_run_id=test_run_id, status=ResultStatus.FAILED
            ).count() + TestResult.query.filter_by(
                test_run_id=test_run_id, status=ResultStatus.ERROR
            ).count()

            run.completed_tasks = completed
            run.failed_tasks = failed
            safe_commit()

            # 检查是否全部完成
            if completed >= run.total_tasks:
                _finalize_run(test_run_id)

        return {
            'test_run_id': test_run_id,
            'algorithm_id': algorithm_id,
            'core_id': core_id,
            'status': result.status if result else ResultStatus.ERROR,
        }
    except Exception as exc:
        # 标记为错误
        from models import TestResult
        tr = TestResult.query.filter_by(
            test_run_id=test_run_id,
            algorithm_id=algorithm_id,
            core_id=core_id,
        ).first()
        if tr:
            tr.status = ResultStatus.ERROR
            tr.error_message = str(exc)[:2000]
            tr.finished_at = datetime.utcnow()
            safe_commit()
        raise self.retry(exc=exc, countdown=10)


def _finalize_run(test_run_id):
    """完成一轮测试，触发一致性分析"""
    from models import ResultStatus, RunStatus, TestResult, TestRun, db

    finalized = False
    with db.session.begin():
        run = db.session.query(TestRun).with_for_update().get(test_run_id)
        if not run or run.status != RunStatus.RUNNING:
            return

        completed = TestResult.query.filter_by(
            test_run_id=test_run_id
        ).filter(TestResult.status.in_([
            ResultStatus.PASSED,
            ResultStatus.FAILED,
            ResultStatus.ERROR,
        ])).count()
        failed = TestResult.query.filter_by(
            test_run_id=test_run_id, status=ResultStatus.FAILED
        ).count() + TestResult.query.filter_by(
            test_run_id=test_run_id, status=ResultStatus.ERROR
        ).count()

        run.completed_tasks = completed
        run.failed_tasks = failed
        if completed < run.total_tasks:
            return

        run.status = RunStatus.COMPLETED
        run.finished_at = datetime.utcnow()
        finalized = True

    if finalized:
        _generate_consistency_report(test_run_id)


def _generate_consistency_report(test_run_id):
    """Generate consistency reports after run finalization is committed."""
    from models import Algorithm, ResultStatus, TestResult
    from services.consistency_service import ConsistencyService
    from services.notification_service import NotificationService

    run_id = test_run_id
    if not run_id:
        return

    consistency_service = ConsistencyService()
    algorithms = Algorithm.query.filter_by(is_active=True).all()

    for algo in algorithms:
        # 检查该算法是否已有结果
        has_results = TestResult.query.filter_by(
            test_run_id=run_id,
            algorithm_id=algo.id,
        ).filter(TestResult.status.in_([ResultStatus.PASSED, ResultStatus.FAILED])).first()

        if has_results:
            consistency_service.compare_across_cores(run_id, algo.id)

    NotificationService.create_for_all(f'Run #{run_id} 完成', 'run_completed')
    print(f"[Task] Test run #{run_id} completed, consistency reports generated")
