from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..const import MAX_TAG_LENGTH


class OjobpubTag(models.Model):
    _name = "ojobpub.tag"
    _description = "oJobPub Keyword"
    _order = "name"

    name = fields.Char(required=True, size=MAX_TAG_LENGTH)
    color = fields.Integer()

    # Case-insensitive, like the check in _check_name, which gives the nicer
    # message; the index is the guarantee.
    _name_uniq = models.UniqueIndex("(lower(name))", "This keyword already exists.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if isinstance(vals.get("name"), str):
                vals["name"] = vals["name"].strip()
        return super().create(vals_list)

    def write(self, vals):
        if isinstance(vals.get("name"), str):
            vals = dict(vals, name=vals["name"].strip())
        return super().write(vals)

    @api.constrains("name")
    def _check_name(self):
        for tag in self:
            name = tag.name or ""
            if not name or len(name) > MAX_TAG_LENGTH:
                raise ValidationError(
                    self.env._(
                        "oJobPub keywords must have between 1 and %(max)s characters.",
                        max=MAX_TAG_LENGTH,
                    )
                )
            # oJobPub tags must be unique per job; "Python" and "python" would
            # be two different keywords in Odoo but look like duplicates.
            candidates = self.search([("id", "!=", tag.id), ("name", "=ilike", name)])
            if any(other.lower() == name.lower() for other in candidates.mapped("name")):
                raise ValidationError(
                    self.env._("The keyword “%(name)s” already exists.", name=name)
                )
