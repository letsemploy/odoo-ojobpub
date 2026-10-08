"""Constants mirroring the oJobPub v1 JSON Schema (letsemploy/schema, v1/ojobpub.json)."""

OJOBPUB_VERSION = "1.0"
WELL_KNOWN_PATH = "/.well-known/ojobpub.json"

JOB_TYPES = [
    ("permanent", "Permanent"),
    ("contract", "Contract"),
    ("internship", "Internship"),
    ("apprenticeship", "Apprenticeship"),
    ("temporary", "Temporary"),
    ("volunteer", "Volunteer"),
    ("freelance", "Freelance"),
]

EXPERIENCE_LEVELS = [
    ("junior", "Junior"),
    ("mid", "Mid"),
    ("senior", "Senior"),
    ("lead", "Lead"),
    ("manager", "Manager"),
    ("director", "Director"),
    ("executive", "Executive"),
]

WORK_TYPES = [
    ("on-site", "On-site"),
    ("hybrid", "Hybrid"),
    ("remote", "Remote"),
]

SALARY_INTERVALS = [
    ("hourly", "Hourly"),
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("yearly", "Yearly"),
]

LANGUAGE_MODES = [
    ("default", "Website default language only"),
    ("translated", "Default language and translated jobs"),
    ("all", "All website languages"),
]

# Schema limits
MAX_TITLE = 255
MAX_DESCRIPTION = 1000
MAX_CATEGORY = 255
MAX_EMPLOYER_NAME = 255
MAX_TAG_LENGTH = 28
MAX_TAGS = 16
