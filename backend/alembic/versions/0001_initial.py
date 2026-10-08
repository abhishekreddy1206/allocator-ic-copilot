"""Initial relational schema; frozen SQL follows in this revision."""
from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    from pathlib import Path
    sql = Path(__file__).with_name('0001_schema.sql').read_text()
    op.get_bind().exec_driver_sql(sql)


def downgrade():
    for name in ['memo_claims', 'memos', 'evidence', 'evaluations', 'factor_exposures', 'metric_snapshots', 'runs', 'mandates', 'macro_observations', 'factor_returns', 'benchmark_returns', 'data_quality_issues', 'monthly_returns', 'funds', 'uploads']:
        op.drop_table(name)
