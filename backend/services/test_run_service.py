from datetime import datetime

from models import Algorithm, Core, ResultStatus, RunStatus, TestResult, TestRun, db
from services.db_session import safe_commit


class TestRunService:
    @staticmethod
    def create_run(triggered_by, svn_revision_id=None):
        """Create a TestRun and pending TestResult rows for all active pairs."""
        algorithms = Algorithm.query.filter_by(is_active=True).all()
        cores = Core.query.filter_by(is_active=True).all()
        run = TestRun(
            triggered_by=triggered_by,
            svn_revision_id=svn_revision_id,
            total_tasks=len(algorithms) * len(cores),
            status=RunStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.flush()

        results = [
            TestResult(
                test_run_id=run.id,
                algorithm_id=algorithm.id,
                core_id=core.id,
                status=ResultStatus.PENDING,
            )
            for algorithm in algorithms
            for core in cores
        ]
        db.session.add_all(results)
        safe_commit()
        return run
