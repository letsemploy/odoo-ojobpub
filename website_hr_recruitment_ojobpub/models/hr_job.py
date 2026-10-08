import re

import lxml.html

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import is_html_empty

from ..const import (
    EXPERIENCE_LEVELS,
    JOB_TYPES,
    MAX_CATEGORY,
    MAX_DESCRIPTION,
    MAX_TAGS,
    MAX_TITLE,
    SALARY_INTERVALS,
    WORK_TYPES,
)


def _truncate(text, limit):
    """Cut ``text`` to ``limit`` characters, preferably at a word boundary."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    space = cut.rfind(" ")
    if space > limit * 0.6:
        cut = cut[:space]
    return cut.rstrip(" ,;:.-") + "…"


_BLOCK_TAGS = (
    "p",
    "div",
    "section",
    "article",
    "header",
    "footer",
    "blockquote",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "table",
    "tr",
)


def _html_to_text(html):
    """Plain text without markup artefacts: paragraphs and list items keep
    their line breaks, inline formatting (<b>, <a>, ...) is dropped."""
    if is_html_empty(html):
        return ""
    root = lxml.html.fragment_fromstring(str(html), create_parent="div")
    for element in root.iter("script", "style"):
        element.drop_tree()
    for element in root.iter("br"):
        element.tail = "\n" + (element.tail or "")
    for element in root.iter(*_BLOCK_TAGS):
        if element.tag == "li":
            element.text = "- " + (element.text or "")
        element.tail = "\n" + (element.tail or "")
    text = root.text_content()
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class HrJob(models.Model):
    _inherit = "hr.job"

    ojobpub_exclude = fields.Boolean(
        string="Exclude from oJobPub",
        help="Do not list this job in the oJobPub feed, even when it is published.",
    )
    ojobpub_job_type = fields.Selection(
        JOB_TYPES,
        string="Job Type",
        compute="_compute_ojobpub_job_type",
        store=True,
        readonly=False,
        help="Defaults from the oJobPub job type of the employee type.",
    )
    ojobpub_work_type = fields.Selection(
        WORK_TYPES,
        string="Work Type",
        compute="_compute_ojobpub_work_type",
        store=True,
        readonly=False,
        help="Defaults to 'Remote' when the job has no job location, otherwise 'On-site'.",
    )
    ojobpub_experience_level = fields.Selection(EXPERIENCE_LEVELS, string="Experience Level")
    ojobpub_workload_min = fields.Integer(string="Workload from (%)")
    ojobpub_workload_max = fields.Integer(string="Workload to (%)")
    ojobpub_salary_min = fields.Monetary(
        string="Salary from", currency_field="ojobpub_salary_currency_id"
    )
    ojobpub_salary_max = fields.Monetary(
        string="Salary to", currency_field="ojobpub_salary_currency_id"
    )
    ojobpub_salary_currency_id = fields.Many2one(
        "res.currency",
        string="Salary Currency",
        default=lambda self: self.env.company.currency_id,
    )
    ojobpub_salary_interval = fields.Selection(
        SALARY_INTERVALS,
        string="Salary per",
        default="yearly",
    )
    ojobpub_start_date = fields.Date(
        string="Start Date",
        help="First working day of the job (oJobPub startDate).",
    )
    ojobpub_end_date = fields.Date(
        string="End Date",
        help="Last working day of a fixed-term job (oJobPub endDate).",
    )
    ojobpub_apply_before = fields.Date(
        string="Apply Before",
        help="Last day to apply. The job disappears from the oJobPub feed afterwards.",
    )
    ojobpub_tag_ids = fields.Many2many("ojobpub.tag", string="Keywords")
    ojobpub_description = fields.Text(
        string="Feed Summary",
        translate=True,
        help="Plain-text summary for the oJobPub feed (max. 1000 characters). "
        "If empty, the job summary is converted to text and shortened.",
    )

    # ------------------------------------------------------------------
    # Computes and constraints
    # ------------------------------------------------------------------

    @api.depends("employee_type_id.ojobpub_job_type")
    def _compute_ojobpub_job_type(self):
        for job in self:
            job.ojobpub_job_type = (
                job.employee_type_id.ojobpub_job_type or job.ojobpub_job_type or "permanent"
            )

    @api.depends("address_id")
    def _compute_ojobpub_work_type(self):
        for job in self:
            if not job.address_id:
                job.ojobpub_work_type = "remote"
            elif job.ojobpub_work_type in (False, "remote"):
                job.ojobpub_work_type = "on-site"

    @api.constrains("ojobpub_workload_min", "ojobpub_workload_max")
    def _check_ojobpub_workload(self):
        for job in self:
            lo, hi = job.ojobpub_workload_min, job.ojobpub_workload_max
            if not (0 <= lo <= 100 and 0 <= hi <= 100):
                raise ValidationError(self.env._("The workload must be between 0 and 100%."))
            if lo and hi and lo > hi:
                raise ValidationError(
                    self.env._("The minimum workload cannot exceed the maximum workload.")
                )

    @api.constrains("ojobpub_salary_min", "ojobpub_salary_max")
    def _check_ojobpub_salary(self):
        for job in self:
            lo, hi = job.ojobpub_salary_min, job.ojobpub_salary_max
            if lo < 0 or hi < 0:
                raise ValidationError(self.env._("The salary cannot be negative."))
            if lo and hi and lo > hi:
                raise ValidationError(
                    self.env._("The minimum salary cannot exceed the maximum salary.")
                )

    @api.constrains("ojobpub_tag_ids")
    def _check_ojobpub_tags(self):
        for job in self:
            if len(job.ojobpub_tag_ids) > MAX_TAGS:
                raise ValidationError(
                    self.env._("oJobPub allows at most %(max)s keywords per job.", max=MAX_TAGS)
                )

    @api.constrains("ojobpub_description")
    def _check_ojobpub_description(self):
        for job in self:
            if job.ojobpub_description and len(job.ojobpub_description) > MAX_DESCRIPTION:
                raise ValidationError(
                    self.env._(
                        "The feed summary is limited to %(max)s characters.",
                        max=MAX_DESCRIPTION,
                    )
                )

    # ------------------------------------------------------------------
    # Feed serialisation
    # ------------------------------------------------------------------

    def _ojobpub_is_listable(self, today):
        self.ensure_one()
        return not self.ojobpub_exclude and (
            not self.ojobpub_apply_before or self.ojobpub_apply_before >= today
        )

    def _ojobpub_text_signature(self):
        """Texts that differ between languages once a job has been translated."""
        self.ensure_one()
        return (self.name, self.description, self.ojobpub_description)

    def _ojobpub_description_text(self):
        self.ensure_one()
        text = self.ojobpub_description or _html_to_text(self.description)
        return _truncate(text, MAX_DESCRIPTION)

    def _ojobpub_location(self):
        self.ensure_one()
        partner = self.address_id or self.company_id.partner_id or self.env.company.partner_id
        return self.env["website"]._ojobpub_partner_location(partner)

    def _ojobpub_entry(self, language, job_url):
        """Return one oJobPub ``job`` object for this job.

        ``language`` is the ISO 639-1 code of the entry; ``self`` must already
        carry the matching Odoo language in its context.
        """
        self.ensure_one()
        # Odoo 20: published_date is a Datetime of website.published.mixin
        published = fields.Date.to_date(self.published_date or self.create_date)
        entry = {
            "title": _truncate(self.name, MAX_TITLE),
            "language": language,
            "publishedAt": fields.Date.to_string(published),
            "jobType": self.ojobpub_job_type or "permanent",
            "locations": [self._ojobpub_location()],
            "url": job_url,
            "referenceId": str(self.id),
        }
        description = self._ojobpub_description_text()
        if description:
            entry["description"] = description
        if self.department_id:
            entry["category"] = _truncate(self.department_id.name, MAX_CATEGORY)
        if self.ojobpub_apply_before:
            entry["applyBefore"] = fields.Date.to_string(self.ojobpub_apply_before)
        if self.ojobpub_start_date:
            entry["startDate"] = fields.Date.to_string(self.ojobpub_start_date)
        if self.ojobpub_end_date:
            entry["endDate"] = fields.Date.to_string(self.ojobpub_end_date)
        if self.ojobpub_work_type:
            entry["workType"] = self.ojobpub_work_type
        if self.ojobpub_experience_level:
            entry["experienceLevel"] = self.ojobpub_experience_level
        if self.ojobpub_workload_min or self.ojobpub_workload_max:
            entry["workLoad"] = {
                "minPercentage": self.ojobpub_workload_min or self.ojobpub_workload_max,
                "maxPercentage": self.ojobpub_workload_max or self.ojobpub_workload_min,
            }
        if self.ojobpub_salary_min or self.ojobpub_salary_max:
            salary = {"interval": self.ojobpub_salary_interval or "yearly"}
            if self.ojobpub_salary_min:
                salary["min"] = self.ojobpub_salary_min
            if self.ojobpub_salary_max:
                salary["max"] = self.ojobpub_salary_max
            if self.ojobpub_salary_currency_id:
                salary["currency"] = self.ojobpub_salary_currency_id.name
            entry["salary"] = salary
        if self.ojobpub_tag_ids:
            entry["tags"] = list(dict.fromkeys(self.ojobpub_tag_ids.mapped("name")))
        return entry
