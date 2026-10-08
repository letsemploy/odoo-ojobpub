import logging

_logger = logging.getLogger(__name__)

# Odoo's standard employment types (hr/data/hr_data.xml) -> oJobPub jobType.
# Deliberately not mapped:
# - full_time / employee / statutaire: describe workload or legal status, not
#   the oJobPub job type
# - contract_type_part_time: the XML-ID is defined twice in Odoo 18 (Part-Time
#   and Intern), so the record's meaning depends on load order
CONTRACT_TYPE_MAPPING = {
    "hr.contract_type_permanent": "permanent",
    "hr.contract_type_temporary": "temporary",
    "hr.contract_type_seasonal": "temporary",
    "hr.contract_type_apprenticeship": "apprenticeship",
    "hr.contract_type_thesis": "internship",
    "hr.contract_type_student": "internship",
}


def post_init_hook(env):
    # hr.job.ojobpub_job_type depends on contract_type_id.ojobpub_job_type, so
    # the ORM recomputes the job type of existing jobs on these writes.
    mapped = 0
    for xmlid, job_type in CONTRACT_TYPE_MAPPING.items():
        contract_type = env.ref(xmlid, raise_if_not_found=False)
        if contract_type and not contract_type.ojobpub_job_type:
            contract_type.ojobpub_job_type = job_type
            mapped += 1
    _logger.info("oJobPub: mapped %s employment types", mapped)
