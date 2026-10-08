import logging
from datetime import datetime, time, timedelta, timezone

from odoo import fields, models

from ..const import LANGUAGE_MODES, MAX_EMPLOYER_NAME, OJOBPUB_VERSION

_logger = logging.getLogger(__name__)


def _iso_639_1(lang):
    """Two-letter ISO 639-1 code of a ``res.lang`` (``de_CH`` -> ``de``), or
    ``None`` for languages without one (e.g. ``kab_DZ``)."""
    code = lang.code.split("_")[0].split("@")[0].lower()
    return code if len(code) == 2 and code.isalpha() else None


class Website(models.Model):
    _inherit = "website"

    ojobpub_enabled = fields.Boolean(
        string="Publish oJobPub Feed",
        default=True,
        help="Serve the published jobs of this website at /.well-known/ojobpub.json",
    )
    ojobpub_language_mode = fields.Selection(
        LANGUAGE_MODES,
        string="oJobPub Languages",
        default="translated",
        required=True,
        help="Default language only: one entry per job.\n"
        "Translated: an additional entry per website language in which the "
        "job title or summary has been translated.\n"
        "All: one entry per job and website language, even if untranslated.",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ojobpub_partner_location(self, partner):
        """oJobPub ``location`` object; keys are omitted when unknown."""
        location = {}
        if partner.city:
            location["city"] = partner.city
        code = (partner.country_id.code or "").upper()
        if len(code) == 2:
            location["country"] = code
        return location

    def _ojobpub_website_domain(self):
        self.ensure_one()
        return [
            ("website_id", "in", [False, self.id]),
            ("company_id", "in", [False, self.company_id.id]),
        ]

    def _ojobpub_jobs(self):
        """Published jobs of this website, as superuser.

        The explicit domain is the security boundary: it must not depend on
        the requesting user, since logged-in HR officers can read every job.
        """
        self.ensure_one()
        return (
            self.env["hr.job"]
            .sudo()
            .search(
                [("is_published", "=", True), *self._ojobpub_website_domain()],
                order="sequence, id",
            )
        )

    def _ojobpub_last_updated(self, today):
        """Newest change of the feed content.

        Takes the newest write on any job of this website, including
        unpublished and archived ones, so that removing a job also bumps the
        timestamp. Jobs whose *Apply Before* date has passed leave the feed
        without a write; the start of the day after that date counts for them.
        """
        self.ensure_one()
        Job = self.env["hr.job"].sudo().with_context(active_test=False)
        domain = self._ojobpub_website_domain()
        stamps = [
            Job.search(domain, order="write_date desc", limit=1).write_date,
            self.company_id.sudo().write_date,
        ]
        expired = Job.search(
            [*domain, ("ojobpub_apply_before", "<", today)],
            order="ojobpub_apply_before desc",
            limit=1,
        ).ojobpub_apply_before
        if expired:
            stamps.append(
                min(
                    datetime.combine(expired + timedelta(days=1), time.min),
                    fields.Datetime.now(),
                )
            )
        stamps = [d for d in stamps if d]
        latest = max(stamps) if stamps else fields.Datetime.now()
        return latest.replace(microsecond=0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    def _ojobpub_languages(self):
        """Languages to emit, default language first.

        oJobPub requires a two-letter ISO 639-1 code; languages without one
        are left out rather than making the whole feed invalid.
        """
        self.ensure_one()
        default = self.default_lang_id
        languages = default
        if self.ojobpub_language_mode != "default":
            languages |= self.language_ids - default
        unsupported = languages.filtered(lambda lang: not _iso_639_1(lang))
        if unsupported:
            _logger.debug(
                "oJobPub: no ISO 639-1 code for %s, these languages are not listed",
                ", ".join(unsupported.mapped("code")),
            )
        return languages - unsupported

    def _ojobpub_job_url(self, job, lang):
        """Absolute job URL in ``lang``; mirrors Odoo's frontend lang prefixing."""
        self.ensure_one()
        path = f"/jobs/{self.env['ir.http']._slug(job.with_context(lang=lang.code))}"
        if lang != self.default_lang_id:
            path = f"/{lang.url_code}{path}"
        return self.get_base_url().rstrip("/") + path

    # ------------------------------------------------------------------
    # Feed
    # ------------------------------------------------------------------

    def _ojobpub_feed(self):
        """Build the oJobPub document (a ``dict``) for this website."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        company = self.company_id.sudo()
        partner = company.partner_id
        default_lang = self.default_lang_id
        languages = self._ojobpub_languages()

        employer = {
            "name": (company.name or self.name)[:MAX_EMPLOYER_NAME],
            "location": self._ojobpub_partner_location(partner),
            "url": self.get_base_url(),
        }
        industry = partner.with_context(lang=default_lang.code).industry_id.name
        if industry:
            employer["industry"] = industry[:MAX_EMPLOYER_NAME]

        entries = []
        for job in self._ojobpub_jobs():
            if not job._ojobpub_is_listable(today):
                continue
            reference = job.with_context(lang=default_lang.code)._ojobpub_text_signature()
            for lang in languages:
                job_lang = job.with_context(lang=lang.code)
                if (
                    lang != default_lang
                    and self.ojobpub_language_mode == "translated"
                    and job_lang._ojobpub_text_signature() == reference
                ):
                    continue
                entries.append(
                    job_lang._ojobpub_entry(
                        _iso_639_1(lang),
                        self._ojobpub_job_url(job, lang),
                    )
                )

        return {
            "version": OJOBPUB_VERSION,
            "lastUpdated": self._ojobpub_last_updated(today),
            "employer": employer,
            "jobs": entries,
        }
