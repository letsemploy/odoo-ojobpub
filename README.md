# oJobPub for Odoo

Odoo modules that publish job openings as an open
[oJobPub](https://www.letsemploy.org) feed.

| Module | Description |
|---|---|
| [website_hr_recruitment_ojobpub](website_hr_recruitment_ojobpub/) | Serves the published jobs of an Odoo website at `/.well-known/ojobpub.json`. |

Branches follow the Odoo version (`18.0`). The module is also listed in the
[Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/website_hr_recruitment_ojobpub).

## Development

```bash
uvx pre-commit run --all-files   # ruff, pylint-odoo, xml/json/yaml checks
```

The Odoo tests run in GitHub Actions with the
[OCA CI image](https://github.com/OCA/oca-ci) (see `.github/workflows/test.yml`).
To run them locally, see the module README.

## Releasing

1. Bump `version` in `website_hr_recruitment_ojobpub/__manifest__.py`
   (`18.0.x.y.z`) and merge to `18.0`.
2. Tag the commit with the same version and push the tag:
   `git tag 18.0.1.0.1 && git push origin 18.0.1.0.1`.
   The release workflow runs the tests and attaches a zip to a GitHub release.
3. The Odoo Apps Store picks up the new version from the `18.0` branch.

## License

LGPL-3.0-or-later, see [LICENSE](LICENSE).
