import json
import os
from datetime import timedelta
from pathlib import Path

from odoo import fields
from odoo.modules.module import load_script

SCHEMA_PATH = Path(__file__).parent / "data" / "ojobpub.schema.json"
MIGRATIONS_PATH = Path(__file__).parent.parent / "migrations"

try:
    import jsonschema
except ImportError:  # pragma: no cover - test-only dependency
    jsonschema = None


def validate_against_schema(test, payload):
    """Validate ``payload`` against the official oJobPub v1 schema."""
    if jsonschema is None:
        message = "jsonschema not installed (pip install 'jsonschema[format]')"
        if os.environ.get("OJOBPUB_REQUIRE_JSONSCHEMA"):
            test.fail(message)
        test.skipTest(message)
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    test.assertFalse(
        errors,
        "\n".join(f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors),
    )


def load_migration(version, stage="pre"):
    """Load a migration script the way Odoo's upgrade does."""
    name = f"{stage}-migrate"
    return load_script(
        str(MIGRATIONS_PATH / version / f"{name}.py"),
        f"odoo.upgrade.website_hr_recruitment_ojobpub.{version}.{name}",
    )


class OjobpubTestMixin:
    @classmethod
    def setup_ojobpub_data(cls):
        env = cls.env
        today = fields.Date.today()
        cls.website = env.ref("base.default_website")
        cls.website.write({"ojobpub_enabled": True, "ojobpub_language_mode": "default"})

        swiss = env.ref("base.ch")
        cls.company = cls.website.company_id
        cls.company.partner_id.write(
            {
                "city": "Solothurn",
                "country_id": swiss.id,
                "industry_id": env["res.partner.industry"].create({"name": "Software"}).id,
            }
        )
        cls.chf = env.ref("base.CHF")
        cls.chf.active = True
        cls.office = env["res.partner"].create(
            {
                "name": "Office Olten",
                "city": "Olten",
                "country_id": swiss.id,
                "is_company": True,
            }
        )
        cls.department = env["hr.department"].create({"name": "Engineering"})
        cls.employee_type_permanent = env["hr.employee.type"].create(
            {
                "name": "Unbefristet",
                "ojobpub_job_type": "permanent",
            }
        )
        cls.tags = env["ojobpub.tag"].create([{"name": "python"}, {"name": "odoo"}])

        Job = env["hr.job"]
        # Demo data has published jobs; the tests expect only their own.
        Job.search([("is_published", "=", True)]).is_published = False
        cls.job_full = Job.create(
            {
                "name": "Odoo Developer",
                "website_published": True,
                "address_id": cls.office.id,
                "department_id": cls.department.id,
                "employee_type_id": cls.employee_type_permanent.id,
                "description": "<p>Build <b>Odoo</b> modules.</p>"
                + "<p>Lorem ipsum dolor sit amet. </p>" * 60,
                "ojobpub_experience_level": "mid",
                "ojobpub_workload_min": 80,
                "ojobpub_workload_max": 100,
                "ojobpub_salary_min": 90000,
                "ojobpub_salary_max": 110000,
                "ojobpub_salary_currency_id": cls.chf.id,
                "ojobpub_salary_interval": "yearly",
                "ojobpub_apply_before": today + timedelta(days=30),
                "ojobpub_tag_ids": [(6, 0, cls.tags.ids)],
                "ojobpub_start_date": today + timedelta(days=60),
            }
        )
        # Odoo defaults the job location to the one of the last created job;
        # "Remote" means an explicitly empty location.
        cls.job_remote = Job.create(
            {
                "name": "Remote Support Engineer",
                "website_published": True,
                "address_id": False,
            }
        )
        cls.job_unpublished = Job.create({"name": "Draft Job", "website_published": False})
        cls.job_excluded = Job.create(
            {
                "name": "Internal Only",
                "website_published": True,
                "ojobpub_exclude": True,
            }
        )
        cls.job_expired = Job.create(
            {
                "name": "Expired Job",
                "website_published": True,
                "ojobpub_apply_before": today - timedelta(days=1),
            }
        )
        cls.other_website = env["website"].create(
            {
                "name": "Other Website",
                "domain": "https://other.example.com",
            }
        )
        cls.job_other_website = Job.create(
            {
                "name": "Other Website Job",
                "website_published": True,
                "website_id": cls.other_website.id,
            }
        )
