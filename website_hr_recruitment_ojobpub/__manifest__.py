# Copyright 2026 Let's Employ
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    "name": "oJobPub – Open Job Feed for Job Boards",
    "summary": "Publish your open jobs as an open oJobPub feed at "
    "/.well-known/ojobpub.json for job boards and search engines",
    "version": "18.0.1.0.0",
    "category": "Human Resources/Recruitment",
    "website": "https://www.letsemploy.org",
    "author": "Let's Employ",
    "maintainer": "Let's Employ",
    "support": "info@letsemploy.org",
    "license": "LGPL-3",
    "depends": ["website_hr_recruitment"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_job_views.xml",
        "views/hr_contract_type_views.xml",
        "views/ojobpub_tag_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "post_init_hook": "post_init_hook",
}
