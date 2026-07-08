def safe_commit(session=None):
    """Commit a SQLAlchemy session, rolling back before re-raising failures."""
    if session is None:
        from models import db
        session = db.session

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
