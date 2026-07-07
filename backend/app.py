import os
from datetime import datetime
from flask import Flask, jsonify, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS

from config import config_map
from models import db, User


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    # Init extensions
    db.init_app(app)
    CORS(app, supports_credentials=True)

    # Login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({'error': '未登录，请先登录'}), 401

    # ---- Auth Routes ----
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({'error': '用户名或密码错误'}), 401

        if not user.is_active_user:
            return jsonify({'error': '账号已被禁用'}), 403

        login_user(user, remember=True)
        user.last_login = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': '登录成功',
            'user': user.to_dict(),
            'force_change_password': user.force_change_password,
        })

    @app.route('/api/auth/logout', methods=['POST'])
    @login_required
    def logout():
        logout_user()
        return jsonify({'message': '已注销'})

    @app.route('/api/auth/me', methods=['GET'])
    @login_required
    def get_me():
        return jsonify({'user': current_user.to_dict()})

    @app.route('/api/auth/password', methods=['PUT'])
    @login_required
    def change_password():
        data = request.get_json()
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')

        if not old_password or not new_password:
            return jsonify({'error': '旧密码和新密码不能为空'}), 400

        if not current_user.check_password(old_password):
            return jsonify({'error': '旧密码错误'}), 400

        if len(new_password) < 6:
            return jsonify({'error': '新密码至少6位'}), 400

        current_user.set_password(new_password)
        current_user.force_change_password = False
        db.session.commit()

        return jsonify({'message': '密码修改成功'})

    # Register blueprints
    from api.users import users_bp
    from api.dashboard import dashboard_bp
    from api.results import results_bp
    from api.consistency import consistency_bp
    from api.svn import svn_bp
    from api.tasks import tasks_bp
    from api.config_manage import config_bp

    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(results_bp, url_prefix='/api/results')
    app.register_blueprint(consistency_bp, url_prefix='/api/consistency')
    app.register_blueprint(svn_bp, url_prefix='/api/svn')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
    app.register_blueprint(config_bp, url_prefix='/api/config')

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
