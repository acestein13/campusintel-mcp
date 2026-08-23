# Security policy

## Supported versions

Security fixes are applied to the latest release on `main`.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's private
**Report a vulnerability** flow under the repository's Security tab. Include reproduction steps,
the affected version, and the potential impact. You can expect an acknowledgement within seven
days.

## Secret handling

CampusIntel reads provider credentials only from environment variables. It never returns key
values from tools, logs them, or stores them in its cache keys. Do not commit `.env` files or place
credentials directly in MCP configuration files that will be shared.

