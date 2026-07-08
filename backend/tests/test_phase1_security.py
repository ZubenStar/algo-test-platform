import importlib
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class Phase1SecurityTests(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault('SECRET_KEY', 'test-secret-key')
        os.environ.setdefault('MYSQL_PASSWORD', 'test-mysql-password')
        os.environ.setdefault('ADMIN_PASSWORD', 'test-admin-password')

    def test_simulator_build_command_returns_argv_and_rejects_shell_metacharacters(self):
        from models import Algorithm, Core
        from services.simulator_service import SimulatorService

        service = SimulatorService.__new__(SimulatorService)
        algorithm = Algorithm(script_path='/opt/tests/run_algo.py')
        core = Core(sim_cmd_template='python {script} --core m55')

        self.assertEqual(
            service._build_command(algorithm, core),
            ['python', '/opt/tests/run_algo.py', '--core', 'm55'],
        )

        algorithm.script_path = '/opt/tests/run_algo.py;touch/tmp/pwned'
        with self.assertRaises(ValueError):
            service._build_command(algorithm, core)

    def test_svn_service_uses_argv_without_shell(self):
        from services.svn_service import SvnService

        completed = SimpleNamespace(returncode=0, stdout='<log></log>', stderr='')
        with patch('services.svn_service.subprocess.run', return_value=completed) as run:
            self.assertEqual(SvnService('svn://example/repo;touch/tmp/pwned').get_log_since('42'), [])

        args, kwargs = run.call_args
        self.assertEqual(args[0], ['svn', 'log', '-r', '42:HEAD', '--xml', '-l', '50', 'svn://example/repo;touch/tmp/pwned'])
        self.assertIs(kwargs.get('shell'), False)

    def test_reset_password_requires_explicit_new_password(self):
        import api.users as users

        class FakeUser:
            username = 'alice'
            force_change_password = False

            def set_password(self, password):
                raise AssertionError('set_password should not be called without new_password')

        fake_query = SimpleNamespace(get_or_404=lambda user_id: FakeUser())
        fake_user_model = SimpleNamespace(query=fake_query)
        fake_db = SimpleNamespace(session=SimpleNamespace(commit=lambda: None))

        app = Flask(__name__)
        with patch.object(users, 'User', fake_user_model), patch.object(users, 'db', fake_db):
            with app.test_request_context(json={}):
                response, status = users.reset_password.__wrapped__.__wrapped__(1)

        self.assertEqual(status, 400)
        self.assertEqual(response.get_json()['error'], '新密码不能为空')

    def test_config_requires_security_sensitive_environment_variables(self):
        saved_env = {name: os.environ.get(name) for name in ('SECRET_KEY', 'MYSQL_PASSWORD', 'ADMIN_PASSWORD')}
        saved_module = sys.modules.pop('config', None)
        for name in saved_env:
            os.environ.pop(name, None)

        try:
            with self.assertRaises(RuntimeError):
                importlib.import_module('config')
        finally:
            sys.modules.pop('config', None)
            if saved_module is not None:
                sys.modules['config'] = saved_module
            for name, value in saved_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_app_registers_csrf_and_login_rate_limiting(self):
        app_source = (BACKEND_DIR / 'app.py').read_text()
        auth_source = (BACKEND_DIR / 'api/auth.py').read_text()
        extension_source = (BACKEND_DIR / 'extensions.py').read_text()

        self.assertIn('CSRFProtect', extension_source)
        self.assertIn('csrf.init_app(app)', app_source)
        self.assertIn('generate_csrf', auth_source)
        self.assertIn('Limiter', extension_source)
        self.assertIn("5 per minute", auth_source)

    def test_frontend_sends_csrf_cookie_as_request_header(self):
        api_source = (REPO_DIR / 'frontend/src/api/index.js').read_text()

        self.assertIn('csrf_token', api_source)
        self.assertIn('X-CSRFToken', api_source)
        self.assertIn('api.interceptors.request.use', api_source)


if __name__ == '__main__':
    unittest.main()
