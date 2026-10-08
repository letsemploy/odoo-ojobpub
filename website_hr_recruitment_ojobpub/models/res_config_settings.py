from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ojobpub_enabled = fields.Boolean(related="website_id.ojobpub_enabled", readonly=False)
    ojobpub_language_mode = fields.Selection(
        related="website_id.ojobpub_language_mode", readonly=False
    )
