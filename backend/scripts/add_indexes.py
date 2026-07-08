#!/usr/bin/env python3
"""Add Phase 2 foreign-key indexes to existing databases."""

import os
import sys

from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db


INDEX_STATEMENTS = [
    'CREATE INDEX IF NOT EXISTS idx_test_runs_svn_revision_id ON test_runs (svn_revision_id)',
    'CREATE INDEX IF NOT EXISTS idx_test_results_test_run_id ON test_results (test_run_id)',
    'CREATE INDEX IF NOT EXISTS idx_test_results_algorithm_id ON test_results (algorithm_id)',
    'CREATE INDEX IF NOT EXISTS idx_test_results_core_id ON test_results (core_id)',
    'CREATE INDEX IF NOT EXISTS idx_consistency_reports_test_run_id ON consistency_reports (test_run_id)',
    'CREATE INDEX IF NOT EXISTS idx_consistency_reports_algorithm_id ON consistency_reports (algorithm_id)',
]


def add_indexes():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as connection:
            for statement in INDEX_STATEMENTS:
                connection.execute(text(statement))
                print(f'[OK] {statement}')


if __name__ == '__main__':
    add_indexes()
