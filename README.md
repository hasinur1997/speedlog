# Speedlog

A macOS menu-bar app (Python + PySide6) that passively tracks internet speed,
records same-speed time segments to SQLite, shows a filterable paginated report
table, and exports PDF reports.

## Requirements

- Python 3.11+
- macOS (Linux/Windows support planned)

## Setup

```sh
# 1. Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt        # runtime
pip install -r requirements-dev.txt    # tests, lint, packaging
```

## Run

```sh
python -m speedlog.main
```

## Test & lint

```sh
pytest -q
ruff check .
black --check .
```

## Project docs

Start with [CLAUDE.md](CLAUDE.md) and the documents under [docs/](docs/):
architecture, code standards, workflow rules, and the ticket board
(`docs/progress-tracker.md`).
