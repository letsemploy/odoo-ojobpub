import logging

_logger = logging.getLogger(__name__)

# Odoo's standard employee types (hr/data/hr_employee_type_data.xml; the XML-IDs
# kept their contract_type_ prefix) -> oJobPub jobType.
# Deliberately not mapped: employee / company_executive, which describe the
# legal status, not the oJobPub job type.
EMPLOYEE_TYPE_MAPPING = {
    "hr.contract_type_interim": "temporary",
    "hr.contract_type_seasonal": "temporary",
    "hr.contract_type_apprenticeship": "apprenticeship",
    "hr.contract_type_intern": "internship",
    "hr.contract_type_thesis": "internship",
    "hr.contract_type_student": "internship",
}


def post_init_hook(env):
    # hr.job.ojobpub_job_type depends on employee_type_id.ojobpub_job_type, so
    # the ORM recomputes the job type of existing jobs on these writes.
    mapped = 0
    for xmlid, job_type in EMPLOYEE_TYPE_MAPPING.items():
        employee_type = env.ref(xmlid, raise_if_not_found=False)
        if employee_type and not employee_type.ojobpub_job_type:
            employee_type.ojobpub_job_type = job_type
            mapped += 1
    _logger.info("oJobPub: mapped %s employee types", mapped)
