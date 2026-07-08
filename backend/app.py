import os
from flask import Flask, jsonify
from flask_login import LoginManager
from flask_cors import CORS

from config import config_map
from models import db, User
from extensions import csrf, limiter


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    # Init extensions
    db.init_app(app)
    CORS(app, supports_credentials=True)
    csrf.init_app(app)
    limiter.init_app(app)

    # Login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({'error': '未登录，请先登录'}), 401

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({'error': '登录尝试过于频繁，请稍后再试'}), 429

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(500)
    def handle_error(error):
        code = error.code if hasattr(error, 'code') else 500
        return jsonify(error=str(error)), code

    # Register blueprints
    from api.auth import auth_bp
    from api.users import users_bp
    from api.dashboard import dashboard_bp
    from api.results import results_bp
    from api.consistency import consistency_bp
    from api.svn import svn_bp
    from api.tasks import tasks_bp
    from api.config_manage import config_bp
    from api.notifications import notifications_bp
    from api.audit import audit_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(results_bp, url_prefix='/api/results')
    app.register_blueprint(consistency_bp, url_prefix='/api/consistency')
    app.register_blueprint(svn_bp, url_prefix='/api/svn')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
    app.register_blueprint(config_bp, url_prefix='/api/config')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(audit_bp, url_prefix='/api/audit')

    # Health check
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok'})

    return app


# 供 Celery 使用
app = create_app()
celery_app = None
try:
    from tasks.celery_tasks import make_celery
    celery_app = make_celery(app)
except Exception as e:
    print(f"[Warning] Celery init skipped: {e}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
