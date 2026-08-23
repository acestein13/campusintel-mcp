# Contributing

Thanks for improving CampusIntel.

## Development setup

```bash
git clone https://github.com/acestein13/campusintel-mcp.git
cd campusintel-mcp
uv sync --all-extras --dev
```

Copy `.env.example` to `.env` only when you need live-provider testing. The automated suite uses
mock transports and does not require secrets.

## Before opening a pull request

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest --cov
```

Keep provider response parsing inside `clients/`, cross-source decisions inside `service.py`, and
MCP-facing validation inside `server.py`. New output fields must preserve source provenance and
must not silently convert missing values into zero.

