from odoo.tests import HttpCase, tagged

from .common import OjobpubTestMixin, validate_against_schema

FEED = "/.well-known/ojobpub.json"


@tagged("post_install", "-at_install")
class TestOjobpubFeedHttp(OjobpubTestMixin, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setup_ojobpub_data()

    def _get_feed(self):
        response = self.url_open(FEED)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["Content-Type"].startswith("application/json"))
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")
        return response.json()

    def _references(self, payload):
        return {int(job["referenceId"]) for job in payload["jobs"]}

    def test_feed_is_valid_ojobpub(self):
        payload = self._get_feed()
        validate_against_schema(self, payload)
        self.assertEqual(payload["version"], "1.0")
        self.assertTrue(payload["lastUpdated"].endswith("Z"))

    def test_only_listable_jobs(self):
        payload = self._get_feed()
        self.assertEqual(
            self._references(payload),
            {self.job_full.id, self.job_remote.id},
            "unpublished, excluded, expired and other-website jobs must not be listed",
        )

    def test_feed_does_not_depend_on_user(self):
        """Logged-in recruiters can read all jobs; the feed must not leak them."""
        public = self._references(self._get_feed())
        self.authenticate("admin", "admin")
        self.assertEqual(self._references(self._get_feed()), public)

    def test_employer(self):
        employer = self._get_feed()["employer"]
        self.assertEqual(employer["name"], self.company.name)
        self.assertEqual(employer["location"], {"city": "Solothurn", "country": "CH"})
        self.assertEqual(employer["industry"], "Software")
        self.assertTrue(employer["url"].startswith("http"))

    def test_job_mapping(self):
        jobs = {int(j["referenceId"]): j for j in self._get_feed()["jobs"]}
        full = jobs[self.job_full.id]
        self.assertEqual(full["title"], "Odoo Developer")
        self.assertEqual(full["language"], "en")
        self.assertEqual(full["jobType"], "permanent")
        self.assertEqual(full["workType"], "on-site")
        self.assertEqual(full["experienceLevel"], "mid")
        self.assertEqual(full["category"], "Engineering")
        self.assertEqual(full["locations"], [{"city": "Olten", "country": "CH"}])
        self.assertEqual(full["workLoad"], {"minPercentage": 80, "maxPercentage": 100})
        self.assertEqual(
            full["salary"],
            {
                "min": 90000.0,
                "max": 110000.0,
                "currency": "CHF",
                "interval": "yearly",
            },
        )
        self.assertEqual(full["tags"], ["odoo", "python"])
        self.assertIn("startDate", full)
        self.assertIn("applyBefore", full)
        self.assertRegex(full["url"], rf"^https?://[^/]+/jobs/odoo-developer-{self.job_full.id}$")
        self.assertLessEqual(len(full["description"]), 1000)
        self.assertTrue(full["description"].startswith("Build Odoo modules."))
        self.assertNotIn("<", full["description"])

        remote = jobs[self.job_remote.id]
        self.assertEqual(remote["workType"], "remote")
        self.assertEqual(remote["locations"], [{"city": "Solothurn", "country": "CH"}])
        self.assertNotIn("salary", remote)
        self.assertNotIn("description", remote)

    def test_job_url_resolves(self):
        full = next(
            j for j in self._get_feed()["jobs"] if j["referenceId"] == str(self.job_full.id)
        )
        path = full["url"].split("/", 3)[3]
        self.assertEqual(self.url_open("/" + path).status_code, 200)

    def test_disabled_feed_returns_404(self):
        self.website.ojobpub_enabled = False
        self.assertEqual(self.url_open(FEED).status_code, 404)
