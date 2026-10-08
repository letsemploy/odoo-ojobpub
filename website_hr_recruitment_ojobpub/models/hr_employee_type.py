from odoo import fields, models

from ..const import JOB_TYPES


class HrEmployeeType(models.Model):
    _inherit = "hr.employee.type"

    ojobpub_job_type = fields.Selection(
        JOB_TYPES,
        string="oJobPub Job Type",
        help="Default oJobPub job type for job positions with this employee type.",
    )
