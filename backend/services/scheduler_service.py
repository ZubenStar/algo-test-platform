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
                from services.db_session import safe_commit
                from services.test_run_service import TestRunService
                from tasks.celery_tasks import trigger_full_test_run

                service = SvnService()
                has_update, revision = service.check_update()

                if has_update and revision:
                    run = TestRunService.create_run('auto', revision.id)

                    # 标记已触发
                    revision.triggered_run = True
                    safe_commit()

                    # 异步执行
                    trigger_full_test_run.delay(run.id)

                    print(f"[Scheduler] SVN update detected: r{revision.revision}, triggered test run #{run.id}")

            except Exception as e:
                print(f"[Scheduler] SVN check error: {e}")

    scheduler.start()
    print(f"[Scheduler] Started, SVN check every {interval} minutes")
