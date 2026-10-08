# Checks after the 18.0 -> 19.0 upgrade (.github/workflows/upgrade.yml).
# Runs with `odoo shell`; a failing assert makes the command exit non-zero.
import json

import jsonschema
import psycopg2

from odoo.tools import file_path

module = env["ir.module.module"].search([("name", "=", "website_hr_recruitment_ojobpub")])
assert module.state == "installed", module.state
assert module.latest_version == "19.0.1.0.0", module.latest_version

job = env["hr.job"].search([("name", "=", "oJobPub upgrade test")])
assert len(job) == 1, job
# pre-migration copied the removed mission dates
assert str(job.ojobpub_start_date) == "2027-01-01", job.ojobpub_start_date
assert str(job.ojobpub_end_date) == "2027-06-30", job.ojobpub_end_date
# stored values survived
assert job.ojobpub_job_type == "temporary", job.ojobpub_job_type
assert (job.ojobpub_workload_min, job.ojobpub_workload_max) == (80, 100)
assert job.ojobpub_experience_level == "senior"
assert sorted(job.ojobpub_tag_ids.mapped("name")) == ["Python", "upgrade"]

# 19.0 replaced _sql_constraints by a case-insensitive unique index
try:
    with env.cr.savepoint():
        env.cr.execute("INSERT INTO ojobpub_tag (name) VALUES ('PYTHON')")
except psycopg2.errors.UniqueViolation:
    pass
else:
    raise AssertionError("case-insensitive unique index on ojobpub_tag.name is missing")

# the feed is still valid and carries the migrated dates
website = env.ref("website.default_website")
payload = website._ojobpub_feed()
schema_path = file_path("website_hr_recruitment_ojobpub/tests/data/ojobpub.schema.json")
with open(schema_path) as schema_file:
    schema = json.load(schema_file)
jsonschema.Draft202012Validator(
    schema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
).validate(payload)
entry = next(j for j in payload["jobs"] if j["referenceId"] == str(job.id))
assert (entry["startDate"], entry["endDate"]) == ("2027-01-01", "2027-06-30"), entry
assert entry["jobType"] == "temporary", entry

print("oJobPub upgrade test: all checks passed")
