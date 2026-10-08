"""Keep the start and end dates of jobs when upgrading from 18.0.

Odoo 19 removed the mission dates ``hr.job.date_from`` / ``date_to``, which
the 18.0 module published as ``startDate`` / ``endDate``. Copy them into the
module's own fields while the old columns still exist (Odoo drops columns of
removed fields only at the end of the upgrade).
"""

import logging

from odoo.tools import SQL
from odoo.tools.sql import column_exists, create_column

_logger = logging.getLogger(__name__)

COLUMNS = {"date_from": "ojobpub_start_date", "date_to": "ojobpub_end_date"}


def migrate(cr, version):
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
