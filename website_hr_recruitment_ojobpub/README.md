# oJobPub Job Feed for Odoo 20

Publishes the jobs of an Odoo website as an [oJobPub](https://www.letsemploy.org)
feed at `https://<your-domain>/.well-known/ojobpub.json`. Job boards and search
engines read the feed directly from the employer's website; registering the
domain once at [SourceTracker](https://sources.letsemploy.org/sources/new) gets
the jobs into the free daily export and API of Let's Employ.

- Odoo 20.0 (Community and Enterprise), depends on `website_hr_recruitment`
- [oJobPub schema v1](https://github.com/letsemploy/schema) (`"version": "1.0"`)
- License: LGPL-3

## Installation

1. Copy `website_hr_recruitment_ojobpub` into an addons path.
2. Update the apps list and install **oJobPub – Open Job Feed for Job Boards**.
3. Open `https://<your-domain>/.well-known/ojobpub.json`.
4. Register the domain at <https://sources.letsemploy.org/sources/new>.

The install hook pre-fills the oJobPub job type of Odoo's standard employee
types (Interim, Occasional / Seasonal, Apprenticeship, Intern, Thesis, Student).
Odoo 20 has no standard *Permanent* type; jobs without a mapped employee type
default to `permanent`. Other employee types can be mapped under
*Recruitment → Configuration → Employee Types*.

## Configuration

*Website → Configuration → Settings → Job Feed*

| Setting | Meaning |
|---|---|
| Publish oJobPub Feed | Serve the feed for this website (otherwise 404). |
| oJobPub Languages | *Default language only*: one entry per job. *Translated* (default): an additional entry per website language in which the title, summary or feed summary is translated. *All*: one entry per job and website language. |

Per job: *Recruitment → Job Position → tab oJobPub*.

## Which jobs are listed

A job is in the feed of website *W* when all of these hold:

- it is published (`is_published`)
- `website_id` is empty or *W*, and `company_id` is empty or the company of *W*
- *Exclude from oJobPub* is not set
- *Apply Before* is empty or today or later

The selection does not depend on the requesting user; logged-in recruiters get
the same feed as anonymous visitors.

## Field mapping

| oJobPub | Odoo |
|---|---|
| `employer.name` | Company name |
| `employer.location` | Company address (city, country) |
| `employer.industry` | Industry of the company's contact |
| `employer.url` | Website base URL (website domain or `web.base.url`) |
| `title` | Job position name (translated) |
| `language` | ISO 639-1 part of the Odoo language (`de_CH` → `de`); languages without a two-letter code (e.g. Kabyle) are not listed |
| `publishedAt` | `published_date` (set by Odoo on publish), fallback creation date |
| `jobType` | *Job Type*, defaults from the employee type's oJobPub job type, fallback `permanent` |
| `locations` | Job location (`address_id`), fallback company address |
| `url` | `/jobs/<slug>` with language prefix for non-default languages |
| `referenceId` | Job ID (same for all languages of a job) |
| `description` | *Feed Summary*, else the job summary converted to plain text (left out while it is still Odoo's sample text), max. 1000 characters |
| `category` | Department |
| `applyBefore` | *Apply Before* |
| `startDate` / `endDate` | *Start Date* / *End Date* |
| `workType` | *Work Type*, defaults to `remote` without a job location, else `on-site` |
| `experienceLevel` | *Experience Level* |
| `workLoad` | *Workload from/to (%)* |
| `salary` | *Salary from/to*, currency, interval |
| `tags` | *Keywords* (max. 16, max. 28 characters each) |

Optional values are omitted when empty.

## Things to know

- **Translations of the job summary.** `description` is an `html_translate`
  field: Odoo translates it sentence by sentence. Translate it with the
  translation dialog (or the website editor), not by saving different HTML in
  another language, which overwrites all languages.
- **Job location default.** Odoo pre-fills the job location of a new job with
  the location of the last created job. "Remote" in Odoo means an explicitly
  empty job location.
- **`publishedAt`** is Odoo's `published_date`, which Odoo resets to today when
  a job is unpublished and published again.
- **`lastUpdated`** is the newest change on any job of the website (including
  unpublished and archived ones) or on the company, so that removals are
  visible to consumers too. A job that leaves the feed because its *Apply
  Before* date has passed counts from midnight (UTC) of the following day.
- The feed is sent with `Cache-Control: public, max-age=900` and
  `Access-Control-Allow-Origin: *`.
- **Odoo Online (SaaS)** does not allow custom Python modules. There, a bridge
  service can read the jobs through the external API and Odoo's website
  redirects can point `/.well-known/ojobpub.json` to it.

## Tests

```bash
./odoo-bin -d test -i website_hr_recruitment_ojobpub \
  --test-enable --test-tags /website_hr_recruitment_ojobpub --stop-after-init
```

Schema validation in the tests uses the official schema in `tests/data/`
(CC0) and needs `jsonschema` (`pip install "jsonschema[format]"`). Without it,
the validation tests are skipped, unless `OJOBPUB_REQUIRE_JSONSCHEMA=1` is set
(as in CI), which makes them fail.
