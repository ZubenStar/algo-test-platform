import os
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('MYSQL_PASSWORD', 'test-mysql-password')
os.environ.setdefault('ADMIN_PASSWORD', 'test-admin-password')


class Phase2StabilityTests(unittest.TestCase):
    def test_safe_commit_rolls_back_and_reraises_on_failure(self):
        try:
            from services.db_session import safe_commit
        except ImportError:
            self.fail('safe_commit helper is missing')

        class FailingSession:
            rolled_back = False

            def commit(self):
                raise RuntimeError('commit failed')

            def rollback(self):
                self.rolled_back = True

        session = FailingSession()
        with self.assertRaises(RuntimeError):
            safe_commit(session)
        self.assertTrue(session.rolled_back)

    def test_phase2_targets_use_safe_commit_instead_of_raw_commit(self):
        targets = [
            BACKEND_DIR / 'api/auth.py',
            BACKEND_DIR / 'api/tasks.py',
            BACKEND_DIR / 'services/scheduler_service.py',
            BACKEND_DIR / 'tasks/celery_tasks.py',
        ]
        needle = 'db.session.' + 'commit()'
        for target in targets:
            source = target.read_text()
            self.assertIn('safe_commit', source, target)
            self.assertNotIn(needle, source, target)

    def test_backend_has_no_raw_session_commits_outside_helper(self):
        allowed = {
            BACKEND_DIR / 'services/db_session.py',
        }
        needle = 'db.session.' + 'commit()'
        offenders = []
        for path in BACKEND_DIR.rglob('*.py'):
            if path in allowed or 'venv' in path.parts:
                continue
            if needle in path.read_text():
                offenders.append(path.relative_to(BACKEND_DIR).as_posix())

        self.assertEqual([], offenders)

    def test_finalize_run_locks_test_run_before_completion_check(self):
        source = (BACKEND_DIR / 'tasks/celery_tasks.py').read_text()

        self.assertIn('with_for_update()', source)
        self.assertIn('run.status !=', source)
        self.assertIn('_generate_consistency_report(test_run_id)', source)

    def test_dashboard_trend_and_matrix_avoid_n_plus_one_queries(self):
        source = (BACKEND_DIR / 'api/dashboard.py').read_text()

        self.assertIn('joinedload(TestResult.algorithm)', source)
        self.assertIn('joinedload(TestResult.core)', source)
        self.assertIn('TestResult.test_run_id.in_(run_ids)', source)
        self.assertIn('group_by(TestResult.test_run_id)', source)

    def test_foreign_key_columns_are_indexed(self):
        from models import ConsistencyReport, TestResult, TestRun

        indexed_columns = [
            TestResult.__table__.columns['test_run_id'],
            TestResult.__table__.columns['algorithm_id'],
            TestResult.__table__.columns['core_id'],
            ConsistencyReport.__table__.columns['test_run_id'],
            ConsistencyReport.__table__.columns['algorithm_id'],
            TestRun.__table__.columns['svn_revision_id'],
        ]

        for column in indexed_columns:
            self.assertTrue(column.index, column)

    def test_add_indexes_migration_script_exists(self):
        migration = BACKEND_DIR / 'scripts/add_indexes.py'
        self.assertTrue(migration.exists(), migration)
        source = migration.read_text()

        self.assertIn('CREATE INDEX IF NOT EXISTS', source)
        self.assertIn('idx_test_results_test_run_id', source)
        self.assertIn('idx_consistency_reports_algorithm_id', source)


if __name__ == '__main__':
    unittest.main()
