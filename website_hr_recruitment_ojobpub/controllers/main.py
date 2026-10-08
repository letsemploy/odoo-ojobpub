import json

from odoo import http
from odoo.http import request

from ..const import WELL_KNOWN_PATH


class OjobpubController(http.Controller):
    @http.route(
        WELL_KNOWN_PATH,
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        multilang=False,
        methods=["GET"],
    )
    def ojobpub_feed(self, **kwargs):
        website = request.env.website  # Odoo 20: request.website was removed
        if not website.ojobpub_enabled:
            raise request.not_found()

        body = json.dumps(website._ojobpub_feed(), ensure_ascii=False, indent=2)
        return request.make_response(
            body,
            headers=[
                ("Content-Type", "application/json; charset=utf-8"),
                ("Cache-Control", "public, max-age=900"),
                ("Access-Control-Allow-Origin", "*"),
                ("X-Content-Type-Options", "nosniff"),
            ],
        )
