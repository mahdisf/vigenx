# Security Policy

## Supported versions

ViGenX is pre-1.0. Security fixes are applied to the latest `master` branch.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting or security advisory flow for
[`mahdisf/vigenx`](https://github.com/mahdisf/vigenx/security/advisories/new).
Do not include credentials, private media, tokens, or exploit details in a public
issue.

Include the affected commit, environment, minimal reproduction, impact, and any
known mitigation. Allow maintainers a reasonable remediation window before
public disclosure.

## Deployment boundary

The Flask application is a trusted local tool by default. It exposes a local file
picker and can start compute-heavy media jobs. It has no production authentication
or multi-tenant isolation. Keep `flask_host = "127.0.0.1"`; do not expose the app
to a LAN or the public internet without adding an authenticated reverse proxy,
CSRF protection, path sandboxing, rate limits, and process isolation.

Generated workflows are validated against a registered block allow-list. This is
not a content-rights guarantee. Review every rights manifest before publishing.
