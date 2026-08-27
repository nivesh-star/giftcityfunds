"""HTTP route handlers, grouped by concern into three Flask Blueprints:

- routes.auth   authentication: login / signup / logout, and the
                @login_required guard other blueprints import.
- routes.pages  server-rendered HTML pages (dashboard, fund pages, FAQs).
- routes.api    the JSON REST API consumed by the frontend's own JavaScript.

Each view function stays thin: read the request, delegate real logic to
services/, return a response. app.py wires these three blueprints onto the
Flask app -- nothing here talks to Flask's app object directly.
"""
