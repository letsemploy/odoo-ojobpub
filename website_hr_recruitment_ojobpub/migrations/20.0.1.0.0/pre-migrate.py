"""Keep the oJobPub job type of employment types when upgrading from 19.0.

Odoo 20 replaced ``hr.contract.type`` by ``hr.employee.type``. When the
upgrade renamed the table, the column came along and nothing is to do.
Otherwise copy the values from the old table, matching types by their English
name (their ids may differ).
"""

import logging

from odoo.tools.sql import column_exists, create_column, table_exists

_logger = logging.getLogger(__name__)

COLUMN = "ojobpub_job_type"


def migrate(cr, version):
    if column_exists(cr, "hr_employee_type", COLUMN):
        return
    if not (
        table_exists(cr, "hr_employee_type")
        and table_exists(cr, "hr_contract_type")
        and column_exists(cr, "hr_contract_type", COLUMN)
    ):
        return
    create_column(cr, "hr_employee_type", COLUMN, "varchar")
    cr.execute("""
        UPDATE hr_employee_type e
           SET ojobpub_job_type = c.ojobpub_job_type
          FROM hr_contract_type c
         WHERE c.ojobpub_job_type IS NOT NULL
           AND e.name->>'en_US' = c.name->>'en_US'
    """)
    _logger.info("oJobPub: copied the job type of %s employee types", cr.rowcount)
