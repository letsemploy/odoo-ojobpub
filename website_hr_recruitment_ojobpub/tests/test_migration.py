"""Tests of the migration scripts.

Each test rebuilds the database state of the previous Odoo version inside the
test transaction (PostgreSQL DDL is transactional, so everything is rolled
back), runs the script and checks the result. End-to-end upgrades are tested
by .github/workflows/upgrade.yml on the 19.0 branch (18.0 -> 19.0).
"""

from odoo.tests import TransactionCase, tagged
from odoo.tools.sql import column_exists, table_exists

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


@tagged("post_install", "-at_install")
class TestMigration20(TransactionCase):
    """19.0 -> 20.0: hr.contract.type.ojobpub_job_type -> hr.employee.type."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.migration = load_migration("20.0.1.0.0")
        Type = cls.env["hr.employee.type"]
        cls.type_contract = Type.create({"name": "oJobPub contract test"})
        cls.type_other = Type.create({"name": "oJobPub other test"})

    def _migrate(self):
        self.migration.migrate(self.env.cr, "19.0.1.0.0")

    def _job_types(self):
        self.env.cr.execute(
            "SELECT id, ojobpub_job_type FROM hr_employee_type WHERE id IN %s",
            [(self.type_contract.id, self.type_other.id)],
        )
        return dict(self.env.cr.fetchall())

    def _rebuild_odoo19_tables(self):
        """Old hr_contract_type table with the values; new table without them."""
        if table_exists(self.env.cr, "hr_contract_type"):
            self.skipTest("hr_contract_type exists in this database")
        self.env.flush_all()
        self.env.cr.execute("ALTER TABLE hr_employee_type DROP COLUMN ojobpub_job_type")
        self.env.cr.execute("""
            CREATE TABLE hr_contract_type (
                id serial PRIMARY KEY, name jsonb, ojobpub_job_type varchar
            )
        """)
        self.env.cr.execute("""
            INSERT INTO hr_contract_type (name, ojobpub_job_type) VALUES
                ('{"en_US": "oJobPub contract test"}', 'contract'),
                ('{"en_US": "oJobPub no match"}', 'freelance')
        """)

    def test_renamed_table_is_left_alone(self):
        """When the upgrade renamed the table, the column came along."""
        self.type_contract.ojobpub_job_type = "contract"
        self.env.flush_all()
        self._migrate()
        self.assertEqual(self._job_types()[self.type_contract.id], "contract")

    def test_copies_from_old_table_by_name(self):
        self._rebuild_odoo19_tables()
        self._migrate()
        self.assertEqual(
            self._job_types(), {self.type_contract.id: "contract", self.type_other.id: None}
        )

    def test_without_old_table(self):
        if table_exists(self.env.cr, "hr_contract_type"):
            self.skipTest("hr_contract_type exists in this database")
        self.env.flush_all()
        self.env.cr.execute("ALTER TABLE hr_employee_type DROP COLUMN ojobpub_job_type")
        self._migrate()
        self.assertFalse(column_exists(self.env.cr, "hr_employee_type", "ojobpub_job_type"))
