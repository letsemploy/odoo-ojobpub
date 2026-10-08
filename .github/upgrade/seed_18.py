# Test data for the 18.0 -> 19.0 upgrade test (.github/workflows/upgrade.yml).
# Runs with `odoo shell` on the 18.0 database, which rolls back unless we commit.
from datetime import date

website = env.ref("website.default_website")
website.ojobpub_enabled = True
website.company_id.partner_id.write({"city": "Solothurn", "country_id": env.ref("base.ch").id})

job = env["hr.job"].create(
    {
        "name": "oJobPub upgrade test",
        "website_published": True,
        "contract_type_id": env.ref("hr.contract_type_temporary").id,
        # Odoo 18 mission dates; 19.0 moves them to ojobpub_start/end_date
        "date_from": date(2027, 1, 1),
        "date_to": date(2027, 6, 30),
        "ojobpub_workload_min": 80,
        "ojobpub_workload_max": 100,
        "ojobpub_experience_level": "senior",
        "ojobpub_tag_ids": [(0, 0, {"name": "Python"}), (0, 0, {"name": "upgrade"})],
    }
)
assert job.ojobpub_job_type == "temporary", job.ojobpub_job_type
env.cr.commit()
print(f"oJobPub upgrade test: created job {job.id}")
