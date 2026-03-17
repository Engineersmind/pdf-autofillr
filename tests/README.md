# Tests

Root-level tests cover cross-module and end-to-end flows.
Module-level unit tests live inside each module.

## Structure

```
tests/
├── integration/          # HTTP API tests (requires running server)
│   └── test_mapper_api.py
└── e2e/                  # Full SDK end-to-end tests
    └── test_mapper_sdk.py
```

## Module tests (existing, passing)

```bash
# Mapper module — 169 tests
cd modules/mapper
venv/bin/python -m pytest tests/ --override-ini="addopts=" -q

# Mapper SDK — 101 tests
cd modules/mapper/sdk
venv/bin/python -m pytest tests/ -q
```

## Integration tests (not yet implemented)

```bash
# Start server first
cd modules/mapper && python api_server.py

# Then run
pytest tests/integration/ -v
```

## E2E tests (not yet implemented)

```bash
# Requires: pip install pdf-autofiller-mapper[embedded], Java 17+, config.ini
pytest tests/e2e/ -v
```
