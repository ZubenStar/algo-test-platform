from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class RunStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'


class ResultStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    PASSED = 'passed'
    FAILED = 'failed'
    ERROR = 'error'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # admin / user
    is_active_user = db.Column(db.Boolean, default=True)
    force_change_password = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'is_active': self.is_active_user,
            'force_change_password': self.force_change_password,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }


class Algorithm(db.Model):
    __tablename__ = 'algorithms'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(200))
    script_path = db.Column(db.String(500))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'script_path': self.script_path,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Core(db.Model):
    __tablename__ = 'cores'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(200))
    arch = db.Column(db.String(50))
    sim_cmd_template = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'arch': self.arch,
            'sim_cmd_template': self.sim_cmd_template,
            'is_active': self.is_active,
        }


class SvnRevision(db.Model):
    __tablename__ = 'svn_revisions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    revision = db.Column(db.String(50), nullable=False, index=True)
    author = db.Column(db.String(100))
    message = db.Column(db.Text)
    commit_time = db.Column(db.DateTime)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    triggered_run = db.Column(db.Boolean, default=False)

    test_runs = db.relationship('TestRun', backref='svn_revision', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'revision': self.revision,
            'author': self.author,
            'message': self.message,
            'commit_time': self.commit_time.isoformat() if self.commit_time else None,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'triggered_run': self.triggered_run,
        }


class TestRun(db.Model):
    __tablename__ = 'test_runs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    svn_revision_id = db.Column(db.Integer, db.ForeignKey('svn_revisions.id'), nullable=True, index=True)
    status = db.Column(db.String(20), default=RunStatus.PENDING)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    failed_tasks = db.Column(db.Integer, default=0)
    triggered_by = db.Column(db.String(50), default='auto')  # auto/manual

    results = db.relationship('TestResult', backref='test_run', lazy='dynamic')
    reports = db.relationship('ConsistencyReport', backref='test_run', lazy='dynamic')

    @property
    def progress(self):
        if self.total_tasks == 0:
            return 0
        return round(self.completed_tasks / self.total_tasks * 100, 1)

    def to_dict(self):
        return {
            'id': self.id,
            'svn_revision_id': self.svn_revision_id,
            'svn_revision': self.svn_revision.to_dict() if self.svn_revision else None,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'progress': self.progress,
            'triggered_by': self.triggered_by,
        }


class TestResult(db.Model):
    __tablename__ = 'test_results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    test_run_id = db.Column(db.Integer, db.ForeignKey('test_runs.id'), nullable=False, index=True)
    algorithm_id = db.Column(db.Integer, db.ForeignKey('algorithms.id'), nullable=False, index=True)
    core_id = db.Column(db.Integer, db.ForeignKey('cores.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default=ResultStatus.PENDING)
    output_file = db.Column(db.String(500))
    result_data = db.Column(db.JSON)
    pass_count = db.Column(db.Integer, default=0)
    fail_count = db.Column(db.Integer, default=0)
    total_count = db.Column(db.Integer, default=0)
    execution_time = db.Column(db.Float)
    log_file = db.Column(db.String(500))
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    algorithm = db.relationship('Algorithm', backref='test_results')
    core = db.relationship('Core', backref='test_results')

    __table_args__ = (
        db.UniqueConstraint('test_run_id', 'algorithm_id', 'core_id', name='uk_run_algo_core'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'test_run_id': self.test_run_id,
            'algorithm': self.algorithm.to_dict() if self.algorithm else None,
            'core': self.core.to_dict() if self.core else None,
            'status': self.status,
            'result_data': self.result_data,
            'pass_count': self.pass_count,
            'fail_count': self.fail_count,
            'total_count': self.total_count,
            'execution_time': self.execution_time,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
        }


class ConsistencyReport(db.Model):
    __tablename__ = 'consistency_reports'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    test_run_id = db.Column(db.Integer, db.ForeignKey('test_runs.id'), nullable=False, index=True)
    algorithm_id = db.Column(db.Integer, db.ForeignKey('algorithms.id'), nullable=False, index=True)
    is_consistent = db.Column(db.Boolean)
    reference_core_id = db.Column(db.Integer, db.ForeignKey('cores.id'), nullable=True)
    details = db.Column(db.JSON)
    max_diff = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    algorithm = db.relationship('Algorithm', backref='consistency_reports')
    reference_core = db.relationship('Core', foreign_keys=[reference_core_id])

    def to_dict(self):
        return {
            'id': self.id,
            'test_run_id': self.test_run_id,
            'algorithm': self.algorithm.to_dict() if self.algorithm else None,
            'is_consistent': self.is_consistent,
            'reference_core': self.reference_core.to_dict() if self.reference_core else None,
            'details': self.details,
            'max_diff': self.max_diff,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False, default='info')
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    target_type = db.Column(db.String(80), nullable=False, index=True)
    target_id = db.Column(db.String(80))
    detail = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref='audit_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'detail': self.detail,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
