from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from .common import OjobpubTestMixin, validate_against_schema


@tagged("post_install", "-at_install")
class TestOjobpubFields(OjobpubTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setup_ojobpub_data()
        cls.lang_de = cls.env["res.lang"]._activate_lang("de_CH")
        cls.website.language_ids |= cls.lang_de
        cls.job_full.with_context(lang="de_CH").name = "Odoo-Entwickler/in"

    def _feed(self, mode):
        self.website.ojobpub_language_mode = mode
        payload = self.website._ojobpub_feed()
        validate_against_schema(self, payload)
        return payload

    def _entries(self, payload):
        return sorted((int(j["referenceId"]), j["language"]) for j in payload["jobs"])

    # ------------------------------------------------------------------
    # Languages
    # ------------------------------------------------------------------

    def test_language_mode_default(self):
        self.assertEqual(
            self._entries(self._feed("default")),
            sorted([(self.job_full.id, "en"), (self.job_remote.id, "en")]),
        )

    def test_language_mode_translated(self):
        payload = self._feed("translated")
        self.assertEqual(
            self._entries(payload),
            sorted(
                [(self.job_full.id, "en"), (self.job_full.id, "de"), (self.job_remote.id, "en")]
            ),
            "only the translated job gets a German entry",
        )
        german = next(j for j in payload["jobs"] if j["language"] == "de")
        self.assertEqual(german["title"], "Odoo-Entwickler/in")
        self.assertIn(f"/{self.lang_de.url_code}/jobs/", german["url"])

    def test_language_mode_all(self):
        self.assertEqual(len(self._feed("all")["jobs"]), 4)

    def test_language_without_iso_639_1_is_skipped(self):
        """oJobPub needs two-letter codes; Kabyle (kab_DZ) has none."""
        self.website.language_ids |= self.env["res.lang"]._activate_lang("kab_DZ")
        languages = {job["language"] for job in self._feed("all")["jobs"]}
        self.assertEqual(languages, {"en", "de"})

    # ------------------------------------------------------------------
    # Defaults and constraints
    # ------------------------------------------------------------------

    def test_install_hook_maps_standard_employee_types(self):
        self.assertEqual(self.env.ref("hr.contract_type_student").ojobpub_job_type, "internship")
        self.assertEqual(self.env.ref("hr.contract_type_interim").ojobpub_job_type, "temporary")
        self.assertEqual(self.env.ref("hr.contract_type_intern").ojobpub_job_type, "internship")
        self.assertEqual(self.env.ref("hr.contract_type_seasonal").ojobpub_job_type, "temporary")
        self.assertFalse(self.env.ref("hr.contract_type_employee").ojobpub_job_type)

    def test_job_type_from_employee_type(self):
        apprenticeship = self.env["hr.employee.type"].create(
            {
                "name": "Lehrstelle",
                "ojobpub_job_type": "apprenticeship",
            }
        )
        self.job_remote.employee_type_id = apprenticeship
        self.assertEqual(self.job_remote.ojobpub_job_type, "apprenticeship")

    def test_work_type_follows_address(self):
        self.assertEqual(self.job_remote.ojobpub_work_type, "remote")
        self.job_remote.address_id = self.office
        self.assertEqual(self.job_remote.ojobpub_work_type, "on-site")
        self.job_remote.ojobpub_work_type = "hybrid"
        self.job_remote.address_id = self.company.partner_id
        self.assertEqual(
            self.job_remote.ojobpub_work_type, "hybrid", "a manual hybrid choice is kept"
        )

    def test_workload_constraint(self):
        with self.assertRaises(ValidationError):
            self.job_remote.ojobpub_workload_max = 120
        with self.assertRaises(ValidationError):
            self.job_remote.write({"ojobpub_workload_min": 90, "ojobpub_workload_max": 60})

    def test_salary_constraint(self):
        with self.assertRaises(ValidationError):
            self.job_remote.write({"ojobpub_salary_min": 100, "ojobpub_salary_max": 50})

    def test_tag_constraints(self):
        tags = self.env["ojobpub.tag"].create([{"name": f"tag{i}"} for i in range(17)])
        with self.assertRaises(ValidationError):
            self.job_remote.ojobpub_tag_ids = tags
        with self.assertRaises(ValidationError):
            self.env["ojobpub.tag"].create({"name": "   "})
        with self.assertRaises(ValidationError):
            self.env["ojobpub.tag"].create({"name": "Python"})
        self.assertEqual(self.env["ojobpub.tag"].create({"name": " django "}).name, "django")

    def test_description_constraint_and_override(self):
        with self.assertRaises(ValidationError):
            self.job_remote.ojobpub_description = "x" * 1001
        self.job_remote.ojobpub_description = "Short summary."
        entry = next(
            j for j in self._feed("default")["jobs"] if j["referenceId"] == str(self.job_remote.id)
        )
        self.assertEqual(entry["description"], "Short summary.")

    def test_html_to_text(self):
        from ..models.hr_job import _html_to_text, _truncate

        html = (
            "<h2>Your tasks</h2><p>Build <b>Odoo</b> modules.<br/>Review code.</p>"
            "<ul><li>Python</li><li>PostgreSQL &amp; SQL</li></ul><script>x()</script>"
        )
        self.assertEqual(
            _html_to_text(html),
            "Your tasks\nBuild Odoo modules.\nReview code.\n- Python\n- PostgreSQL & SQL",
        )
        self.assertEqual(_html_to_text("<p><br></p>"), "")
        truncated = _truncate("word " * 300, 1000)
        self.assertLessEqual(len(truncated), 1000)
        self.assertTrue(truncated.endswith("word…"))

    def _age_write_dates(self):
        self.env.flush_all()
        self.env.cr.execute("UPDATE hr_job SET write_date = write_date - interval '10 days'")
        self.env.cr.execute("UPDATE res_company SET write_date = write_date - interval '10 days'")
        self.env.invalidate_all()

    def test_expiry_bumps_last_updated(self):
        """A job whose Apply Before date passes leaves the feed without any write."""
        today = fields.Date.context_today(self.website)
        self.env.cr.execute(
            "UPDATE hr_job SET ojobpub_apply_before = NULL WHERE ojobpub_apply_before < %s",
            [today],
        )
        self._age_write_dates()
        stale = self.website._ojobpub_feed()["lastUpdated"]
        self.env.cr.execute(
            "UPDATE hr_job SET ojobpub_apply_before = %s WHERE id = %s",
            [today - timedelta(days=1), self.job_full.id],
        )
        self.env.invalidate_all()
        payload = self.website._ojobpub_feed()
        self.assertNotIn(str(self.job_full.id), [j["referenceId"] for j in payload["jobs"]])
        self.assertLess(stale, payload["lastUpdated"])
        self.assertEqual(payload["lastUpdated"], f"{today.isoformat()}T00:00:00Z")

    def test_unpublish_bumps_last_updated(self):
        before = self.website._ojobpub_feed()["lastUpdated"]
        self.env.cr.execute(
            "UPDATE hr_job SET write_date = write_date - interval '1 day' WHERE id IN %s",
            [tuple(self.env["hr.job"].search([]).ids)],
        )
        self.env.cr.execute("UPDATE res_company SET write_date = write_date - interval '1 day'")
        self.env.invalidate_all()
        stale = self.website._ojobpub_feed()["lastUpdated"]
        self.job_full.website_published = False
        self.env.flush_all()
        self.env.invalidate_all()
        after = self.website._ojobpub_feed()["lastUpdated"]
        self.assertLess(stale, after)
        self.assertLessEqual(before, after)
