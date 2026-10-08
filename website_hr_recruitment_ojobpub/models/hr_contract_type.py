from odoo import fields, models

from ..const import JOB_TYPES


class HrContractType(models.Model):
    _inherit = "hr.contract.type"

    ojobpub_job_type = fields.Selection(
        JOB_TYPES,
        string="oJobPub Job Type",
        help="Default oJobPub job type for job positions with this employment type.",
    )
