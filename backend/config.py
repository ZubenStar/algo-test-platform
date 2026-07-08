import os


def required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f'{name} must be set')
    return value


class Config:
    SECRET_KEY = required_env('SECRET_KEY')

    # MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = required_env('MYSQL_PASSWORD')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'algo_test')
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis / Celery
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    RATELIMIT_STORAGE_URI = REDIS_URL

    # SVN
    SVN_REPO_URL = os.environ.get('SVN_REPO_URL', 'svn://your-server/repo')
    SVN_LOCAL_PATH = os.environ.get('SVN_LOCAL_PATH', '/home/user/svn_repo')
    SVN_CHECK_INTERVAL_MINUTES = int(os.environ.get('SVN_CHECK_INTERVAL', 30))

    # Simulation
    SIM_SCRIPTS_DIR = os.environ.get('SIM_SCRIPTS_DIR', '/home/user/svn_repo/tests')
    SIM_OUTPUT_DIR = os.environ.get('SIM_OUTPUT_DIR', '/home/user/sim_output')
    SIM_TIMEOUT_SECONDS = int(os.environ.get('SIM_TIMEOUT', 600))

    # Consistency
    CONSISTENCY_THRESHOLD = float(os.environ.get('CONSISTENCY_THRESHOLD', 1e-6))

    # Default admin
    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_PASSWORD = required_env('ADMIN_PASSWORD')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
