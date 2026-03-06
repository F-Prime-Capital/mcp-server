# Repository Guidelines

## Project Structure & Module Organization
This repository is a Python package using a `src/` layout.
- `src/fprime_mcp/`: application code.
- `src/fprime_mcp/main.py`: FastAPI app entrypoint.
- `src/fprime_mcp/auth/`: OIDC/Entra ID auth config and routes.
- `src/fprime_mcp/tools/`: MCP tool implementations (for example, therapeutics tooling).
- `tests/`: test suite (currently auth flow tests).
- `docs/`: operational docs such as Azure setup.
- Root config: `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.env.example`.

## Build, Test, and Development Commands
Use Python 3.11+.
- `pip install -e .`: install package in editable mode.
- `pip install -e .[dev]`: install development dependencies.
- `uvicorn fprime_mcp.main:app --reload --port 8000`: run local server.
- `pytest`: run all tests.
- `pytest --cov=src/fprime_mcp --cov-report=term-missing`: run tests with coverage.
- `ruff check .`: lint code.
- `ruff format .`: format code.
- `mypy src`: run strict type checking.

## Coding Style & Naming Conventions
- Follow PEP 8 with project tooling as source of truth.
- Line length: 100 (configured in `pyproject.toml`).
- Use type hints for all new/changed Python code; `mypy` strict mode is enabled.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Keep FastAPI route handlers small; move reusable logic to focused helper functions/modules.

## Testing Guidelines
- Framework: `pytest` with `pytest-asyncio` (`asyncio_mode = auto`).
- Place tests under `tests/` and name files `test_*.py`.
- Prefer small, focused tests around auth flows, API responses, and tool behavior.
- Add regression tests for bug fixes before/with implementation when practical.

## Commit & Pull Request Guidelines
Git history is informal and imperative; use clearer, scoped commit messages going forward.
- Recommended format: `<area>: <imperative summary>` (example: `auth: validate callback state`).
- Keep commits focused and reviewable.
- PRs should include: purpose, key changes, test evidence (`pytest`, lint/type checks), config/env changes, and screenshots or sample responses for endpoint behavior when relevant.

## Security & Configuration Tips
- Never commit secrets; use `.env.example` as the template.
- Store Entra/AWS credentials via secure secret management (see `README.md` and `docs/azure-setup.md`).
- Validate auth-related changes manually via `/auth/login` and corresponding callback flow.
