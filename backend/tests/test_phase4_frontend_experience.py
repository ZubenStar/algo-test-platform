import os
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
FRONTEND_DIR = REPO_DIR / 'frontend/src'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('MYSQL_PASSWORD', 'test-mysql-password')
os.environ.setdefault('ADMIN_PASSWORD', 'test-admin-password')


class Phase4FrontendExperienceTests(unittest.TestCase):
    def test_dashboard_chart_lifecycle_disposes_resize_handler(self):
        source = (FRONTEND_DIR / 'views/Dashboard.vue').read_text()

        self.assertIn('const chartInstance = ref(null)', source)
        self.assertIn('const resizeTrendChart', source)
        self.assertIn('onUnmounted(() =>', source)
        self.assertIn('window.removeEventListener', source)
        self.assertIn('chartInstance.value.dispose()', source)

    def test_page_state_component_exists_and_is_used(self):
        component = FRONTEND_DIR / 'components/PageState.vue'
        dashboard = (FRONTEND_DIR / 'views/Dashboard.vue').read_text()
        svn = (FRONTEND_DIR / 'views/SvnMonitor.vue').read_text()
        consistency = (FRONTEND_DIR / 'views/ConsistencyReport.vue').read_text()

        self.assertTrue(component.exists(), component)
        component_source = component.read_text()
        self.assertIn('v-loading="true"', component_source)
        self.assertIn('<el-empty', component_source)
        self.assertIn('<PageState', dashboard)
        self.assertIn('<PageState', svn)
        self.assertIn('<PageState', consistency)

    def test_notification_model_api_and_frontend_bell_are_wired(self):
        from models import Notification

        self.assertEqual(Notification.__tablename__, 'notifications')

        app_source = (BACKEND_DIR / 'app.py').read_text()
        notifications_api = BACKEND_DIR / 'api/notifications.py'
        bell = FRONTEND_DIR / 'components/NotificationBell.vue'
        app_vue = (FRONTEND_DIR / 'App.vue').read_text()

        self.assertTrue(notifications_api.exists(), notifications_api)
        self.assertTrue(bell.exists(), bell)
        self.assertIn('/stream', notifications_api.read_text())
        self.assertIn('app.register_blueprint(notifications_bp', app_source)
        self.assertIn('new EventSource', app_vue)
        self.assertIn('<NotificationBell', app_vue)

    def test_audit_log_model_decorator_api_and_admin_route_are_wired(self):
        from models import AuditLog

        self.assertEqual(AuditLog.__tablename__, 'audit_logs')

        audit_service = BACKEND_DIR / 'services/audit_service.py'
        audit_api = BACKEND_DIR / 'api/audit.py'
        users_source = (BACKEND_DIR / 'api/users.py').read_text()
        config_source = (BACKEND_DIR / 'api/config_manage.py').read_text()
        tasks_source = (BACKEND_DIR / 'api/tasks.py').read_text()
        router_source = (FRONTEND_DIR / 'router/index.js').read_text()

        self.assertTrue(audit_service.exists(), audit_service)
        self.assertTrue(audit_api.exists(), audit_api)
        self.assertIn('def audit_log(action, target_type)', audit_service.read_text())
        self.assertIn('@audit_log', users_source)
        self.assertIn('@audit_log', config_source)
        self.assertIn('@audit_log', tasks_source)
        self.assertIn("path: '/audit'", router_source)


if __name__ == '__main__':
    unittest.main()
