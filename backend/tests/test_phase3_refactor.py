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


class Phase3RefactorTests(unittest.TestCase):
    def test_status_enums_exist_and_model_defaults_use_them(self):
        from models import ResultStatus, RunStatus, TestResult, TestRun

        self.assertEqual(RunStatus.RUNNING, 'running')
        self.assertEqual(ResultStatus.PENDING, 'pending')
        self.assertEqual(TestRun.__table__.columns['status'].default.arg, RunStatus.PENDING)
        self.assertEqual(TestResult.__table__.columns['status'].default.arg, ResultStatus.PENDING)

    def test_test_run_service_is_extracted_and_used_by_triggers(self):
        service = BACKEND_DIR / 'services/test_run_service.py'
        tasks = (BACKEND_DIR / 'api/tasks.py').read_text()
        scheduler = (BACKEND_DIR / 'services/scheduler_service.py').read_text()

        self.assertTrue(service.exists(), service)
        service_source = service.read_text()
        self.assertIn('class TestRunService', service_source)
        self.assertIn('def create_run(triggered_by, svn_revision_id=None)', service_source)
        self.assertIn("TestRunService.create_run('manual'", tasks)
        self.assertIn("TestRunService.create_run('auto'", scheduler)

    def test_auth_routes_live_in_auth_blueprint_not_app_factory(self):
        app_source = (BACKEND_DIR / 'app.py').read_text()
        auth = BACKEND_DIR / 'api/auth.py'

        self.assertTrue(auth.exists(), auth)
        auth_source = auth.read_text()
        self.assertIn("auth_bp = Blueprint('auth'", auth_source)
        self.assertIn("@auth_bp.route('/login'", auth_source)
        self.assertIn("app.register_blueprint(auth_bp)", app_source)
        self.assertNotIn("@app.route('/api/auth/login'", app_source)
        self.assertNotIn('def change_password():', app_source)

    def test_app_registers_common_json_error_handlers(self):
        app_source = (BACKEND_DIR / 'app.py').read_text()

        self.assertIn('@app.errorhandler(400)', app_source)
        self.assertIn('@app.errorhandler(404)', app_source)
        self.assertIn('@app.errorhandler(500)', app_source)
        self.assertIn('return jsonify(error=str(error)), code', app_source)


if __name__ == '__main__':
    unittest.main()
