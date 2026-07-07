from apscheduler.schedulers.background import BackgroundScheduler


scheduler = BackgroundScheduler()


def init_scheduler(app):
    """初始化定时任务调度器"""
    interval = app.config.get('SVN_CHECK_INTERVAL_MINUTES', 30)

    @scheduler.scheduled_job('interval', minutes=interval, id='svn_check')
    def check_svn_periodically():
        with app.app_context():
            try:
                from services.svn_service import SvnService
                from tasks.celery_tasks import trigger_full_test_run
                from models import db, TestRun, Algorithm, Core

                service = SvnService()
                has_update, revision = service.check_update()

                if has_update and revision:
                    # 创建测试运行
                    run = TestRun(
                        svn_revision_id=revision.id,
                        status='pending',
                        triggered_by='auto',
                    )
                    algorithms = Algorithm.query.filter_by(is_active=True).all()
                    cores = Core.query.filter_by(is_active=True).all()
                    run.total_tasks = len(algorithms) * len(cores)

                    db.session.add(run)
                    db.session.commit()

                    # 创建测试结果记录
                    from models import TestResult
                    from datetime import datetime
                    run.started_at = datetime.utcnow()
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

                    # 标记已触发
                    revision.triggered_run = True
                    db.session.commit()

                    # 异步执行
                    trigger_full_test_run.delay(run.id)

                    print(f"[Scheduler] SVN update detected: r{revision.revision}, triggered test run #{run.id}")

            except Exception as e:
                print(f"[Scheduler] SVN check error: {e}")

    scheduler.start()
    print(f"[Scheduler] Started, SVN check every {interval} minutes")
