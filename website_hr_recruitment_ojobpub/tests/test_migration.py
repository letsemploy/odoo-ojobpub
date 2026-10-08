"""Tests of the migration scripts.

Each test rebuilds the database state of the previous Odoo version inside the
test transaction (PostgreSQL DDL is transactional, so everything is rolled
back), runs the script and checks the result. End-to-end upgrades are tested
by .github/workflows/upgrade.yml.
"""

from odoo.tests import TransactionCase, tagged
from odoo.tools.sql import column_exists

from .common import load_migration


@tagged("post_install", "-at_install")
class TestMigration19(TransactionCase):
    """18.0 -> 19.0: hr.job.date_from/date_to -> ojobpub_start_date/end_date."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.migration = load_migration("19.0.1.0.0")
        Job = cls.env["hr.job"]
        cls.job_dated = Job.create({"name": "Job with mission dates"})
        cls.job_kept = Job.create({"name": "Job with own start date"})
        cls.job_undated = Job.create({"name": "Job without dates"})

    def _add_odoo18_columns(self):
        self.env.flush_all()
        self.env.cr.execute("ALTER TABLE hr_job ADD COLUMN date_from date, ADD COLUMN date_to date")
        self.env.cr.execute(
            "UPDATE hr_job SET date_from = '2027-01-01', date_to = '2027-06-30' WHERE id IN %s",
            [(self.job_dated.id, self.job_kept.id)],
        )
        self.job_kept.ojobpub_start_date = "2027-02-01"
        self.env.flush_all()

    def _migrate(self):
        self.migration.migrate(self.env.cr, "18.0.1.0.0")
        self.env.invalidate_all()

    def test_copies_mission_dates(self):
        self._add_odoo18_columns()
        self._migrate()
        self.assertEqual(str(self.job_dated.ojobpub_start_date), "2027-01-01")
        self.assertEqual(str(self.job_dated.ojobpub_end_date), "2027-06-30")
        self.assertEqual(
            str(self.job_kept.ojobpub_start_date), "2027-02-01", "existing values are kept"
        )
        self.assertEqual(str(self.job_kept.ojobpub_end_date), "2027-06-30")
        self.assertFalse(self.job_undated.ojobpub_start_date)

    def test_runs_twice(self):
        self._add_odoo18_columns()
        self._migrate()
        self._migrate()
        self.assertEqual(str(self.job_dated.ojobpub_start_date), "2027-01-01")

    def test_creates_missing_columns(self):
        """Pre-migration runs before the ORM creates the new columns."""
        self._add_odoo18_columns()
        self.env.cr.execute(
            "ALTER TABLE hr_job DROP COLUMN ojobpub_start_date, DROP COLUMN ojobpub_end_date"
        )
        self._migrate()
        self.assertTrue(column_exists(self.env.cr, "hr_job", "ojobpub_start_date"))
        self.env.cr.execute(
            "SELECT ojobpub_start_date::text, ojobpub_end_date::text FROM hr_job WHERE id = %s",
            [self.job_dated.id],
        )
        self.assertEqual(self.env.cr.fetchone(), ("2027-01-01", "2027-06-30"))

    def test_without_old_columns(self):
        """Fresh 19.0 databases have no mission dates; nothing happens."""
        self.assertFalse(column_exists(self.env.cr, "hr_job", "date_from"))
        self._migrate()
        self.assertFalse(self.job_dated.ojobpub_start_date)
