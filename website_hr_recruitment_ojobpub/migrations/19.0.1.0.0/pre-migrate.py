"""Upgrade from 18.0.

- Odoo 19 removed the mission dates ``hr.job.date_from`` / ``date_to``, which
  the 18.0 module published as ``startDate`` / ``endDate``. Copy them into the
  module's own fields while the old columns still exist (Odoo drops columns of
  removed fields only at the end of the upgrade).
- The 18.0 SQL constraint ``unique(name)`` on ``ojobpub_tag`` has the same
  database name as the 19.0 index ``unique(lower(name))``. Odoo keeps an
  existing index of that name, so drop the old one to get the new one.
"""

import logging

from odoo.tools import SQL
from odoo.tools.sql import column_exists, create_column, table_exists

_logger = logging.getLogger(__name__)

COLUMNS = {"date_from": "ojobpub_start_date", "date_to": "ojobpub_end_date"}
TAG_CONSTRAINT = "ojobpub_tag_name_uniq"


def migrate(cr, version):
    _copy_mission_dates(cr)
    _drop_case_sensitive_tag_constraint(cr)


def _copy_mission_dates(cr):
    for old, new in COLUMNS.items():
        if not column_exists(cr, "hr_job", old):
            continue
        if not column_exists(cr, "hr_job", new):
            create_column(cr, "hr_job", new, "date")
        cr.execute(
            SQL(
                "UPDATE hr_job SET %(new)s = %(old)s WHERE %(new)s IS NULL AND %(old)s IS NOT NULL",
                new=SQL.identifier(new),
                old=SQL.identifier(old),
            )
        )
        _logger.info("oJobPub: copied %s jobs' %s to %s", cr.rowcount, old, new)


def _drop_case_sensitive_tag_constraint(cr):
    if not table_exists(cr, "ojobpub_tag"):
        return
    cr.execute(
        "SELECT 1 FROM pg_constraint WHERE conname = %s AND conrelid = 'ojobpub_tag'::regclass",
        [TAG_CONSTRAINT],
    )
    if not cr.rowcount:
        return
    cr.execute(SQL("ALTER TABLE ojobpub_tag DROP CONSTRAINT %s", SQL.identifier(TAG_CONSTRAINT)))
    # The 18.0 module refused such duplicates, but data may come from imports;
    # the new index cannot be created while they exist.
    cr.execute("""
        SELECT string_agg(name, ', ') FROM ojobpub_tag
         GROUP BY lower(name) HAVING count(*) > 1
    """)
    duplicates = [row[0] for row in cr.fetchall()]
    if duplicates:
        _logger.warning(
            "oJobPub: merge these keywords that differ only in case, otherwise the "
            "unique index on ojobpub_tag cannot be created: %s",
            "; ".join(duplicates),
        )
