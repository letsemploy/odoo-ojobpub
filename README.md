# oJobPub for Odoo

Odoo modules that publish job openings as an open
[oJobPub](https://www.letsemploy.org) feed.

| Module | Description |
|---|---|
| [website_hr_recruitment_ojobpub](website_hr_recruitment_ojobpub/) | Serves the published jobs of an Odoo website at `/.well-known/ojobpub.json`. |

## Branches

One branch per Odoo version, each listed separately in the Odoo Apps Store:

| Branch | Odoo | Apps Store |
|---|---|---|
| `18.0` | 18.0 | [18.0](https://apps.odoo.com/apps/modules/18.0/website_hr_recruitment_ojobpub) |
| `19.0` | 19.0 | [19.0](https://apps.odoo.com/apps/modules/19.0/website_hr_recruitment_ojobpub) |
| `20.0` | 20.0 | [20.0](https://apps.odoo.com/apps/modules/20.0/website_hr_recruitment_ojobpub) |

Fixes go into the lowest affected branch first and are then forward-ported
with `git cherry-pick`: `18.0` → `19.0` → `20.0`. The branches differ only
where Odoo itself changed (e.g. `hr.contract.type` became `hr.employee.type`
in 20.0), so most commits apply cleanly.

## Development

```bash
uvx pre-commit run --all-files   # ruff, pylint-odoo, xml/json/yaml checks
```

The Odoo tests run in GitHub Actions with the
[OCA CI image](https://github.com/OCA/oca-ci) (see `.github/workflows/test.yml`).
To run them locally, see the module README.

### Upgrade tests

- `tests/test_migration.py` tests each migration script on its own: it
  rebuilds the previous version's tables inside the test transaction, runs
  the script and checks the result. Runs with the normal tests.
- `.github/workflows/upgrade.yml` (branch `19.0`) upgrades a real 18.0
  database to 19.0 with [OpenUpgrade](https://github.com/OCA/OpenUpgrade) and
  checks the migrated data and the feed. It runs when migration code changes,
  or by hand from the Actions tab.
- 19.0 → 20.0 has no end-to-end test yet, because OpenUpgrade 20.0 does not cover
  the HR modules yet.

## Releasing

1. Bump `version` in `website_hr_recruitment_ojobpub/__manifest__.py`
   (`<branch>.x.y.z`, e.g. `18.0.1.0.1`) and merge to the version branch.
2. Tag the commit with the same version and push the tag:
   `git tag 18.0.1.0.1 && git push origin 18.0.1.0.1`.
   The release workflow runs the tests and attaches a zip to a GitHub release.
3. The Odoo Apps Store picks up the new version from the version branch.

## License

LGPL-3.0-or-later, see [LICENSE](LICENSE).
