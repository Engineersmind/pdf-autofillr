# Migration Plan: SDKs into Modules

## Decision

Move SDKs **inside each module** so every module is fully self-contained and independently publishable to PyPI.

**Before (current):**
```
sdks/python/            ← one shared package for everything
  pdf_autofiller/
  tests/
  setup.py              ← pip install pdf-autofiller
```

**After (target):**
```
modules/
  mapper/
    sdk/                ← mapper's SDK lives here
      pdf_autofiller_mapper/
      tests/
      pyproject.toml    ← pip install pdf-autofiller-mapper

  chatbot/
    sdk/                ← chatbot's SDK lives here (future)
      pdf_autofiller_chatbot/
      pyproject.toml    ← pip install pdf-autofiller-chatbot

  rag/
    sdk/                ← rag's SDK (future)
      pyproject.toml    ← pip install pdf-autofiller-rag

sdks/
  openapi-mapper.yaml       ← OpenAPI specs stay here (shared reference)
  openapi-chatbot.yaml
  openapi-rag.yaml
  openapi-orchestrator.yaml
  typescript/               ← TypeScript SDK stays here (HTTP-only, one npm package is fine)
  generate.sh
```

**Shared data stays at root:**
```
data/
  samples/              ← sample PDFs, JSONs used across modules
  modules/
    mapper_sample/      ← mapper-specific test data
```

---

## What changes, what stays

| Item | What happens |
|------|-------------|
| `sdks/python/pdf_autofiller/` | Moves to `modules/mapper/sdk/pdf_autofiller_mapper/` |
| `sdks/python/tests/` | Moves to `modules/mapper/sdk/tests/` |
| `sdks/python/examples/` | Moves to `modules/mapper/sdk/examples/` |
| `sdks/python/pyproject.toml` | Replaced by `modules/mapper/sdk/pyproject.toml` (new package name) |
| `sdks/python/setup.py` | Replaced by `modules/mapper/sdk/setup.py` |
| `sdks/python/sdks_mapper_doc.md` | Moves to `modules/mapper/sdk/README.md` |
| `sdks/python/config.json.example` | Moves to `modules/mapper/sdk/config.ini.example` |
| `sdks/python/pdf_autofiller_sdk/` | Deleted — this was an older duplicate client |
| `sdks/python/` | Becomes empty → deleted |
| `sdks/openapi-*.yaml` | Stay in `sdks/` — no change |
| `sdks/typescript/` | Stays in `sdks/` — no change |
| `sdks/generate.sh` | Stays in `sdks/` — no change |
| `data/` | No change |
| `modules/mapper/src/` | No change — server logic untouched |
| `modules/mapper/tests/` | No change — module-level tests untouched |
| Root `Makefile` | Update `install-sdk` target path |
| Root `setup.sh` / `setup.ps1` | Update SDK install path |
| `modules/mapper/sdk/pyproject.toml` | Package name: `pdf-autofiller-mapper` |
| Python package import | `from pdf_autofiller_mapper import PDFMapper` |

---

## Package rename

| | Before | After |
|--|--------|-------|
| PyPI name | `pdf-autofiller` | `pdf-autofiller-mapper` |
| Python import | `from pdf_autofiller import PDFMapper` | `from pdf_autofiller_mapper import PDFMapper` |
| CLI command | `pdf-autofiller` | `pdf-autofiller-mapper` |
| Install (HTTP only) | `pip install pdf-autofiller` | `pip install pdf-autofiller-mapper` |
| Install (embedded) | `pip install pdf-autofiller[embedded]` | `pip install pdf-autofiller-mapper[embedded]` |

---

## Step-by-step migration

### Step 1 — Create the SDK folder structure inside mapper

```
modules/mapper/sdk/
  pdf_autofiller_mapper/    ← renamed from pdf_autofiller
    __init__.py
    mapper.py
    client.py
    result.py
    exceptions.py
    cli.py
    resources/
      __init__.py
      mapper.py
    jars/                   ← Java JARs if bundled
  tests/
    __init__.py
    conftest.py
    test_mapper.py
    test_client.py
    test_result.py
    test_exceptions.py
  examples/
    basic_usage.py
    context_manager.py
    example_with_config.py
  pyproject.toml
  setup.py
  README.md                 ← move sdks_mapper_doc.md here
  config.ini.example        ← copy from modules/mapper/config.ini.example
```

### Step 2 — Copy source files

Copy (do not delete yet — keep old location working during transition):

```bash
# Create structure
mkdir -p modules/mapper/sdk/pdf_autofiller_mapper/resources
mkdir -p modules/mapper/sdk/tests
mkdir -p modules/mapper/sdk/examples

# Copy source
cp sdks/python/pdf_autofiller/__init__.py       modules/mapper/sdk/pdf_autofiller_mapper/
cp sdks/python/pdf_autofiller/mapper.py         modules/mapper/sdk/pdf_autofiller_mapper/
cp sdks/python/pdf_autofiller/client.py         modules/mapper/sdk/pdf_autofiller_mapper/
cp sdks/python/pdf_autofiller/result.py         modules/mapper/sdk/pdf_autofiller_mapper/
cp sdks/python/pdf_autofiller/exceptions.py     modules/mapper/sdk/pdf_autofiller_mapper/
cp sdks/python/pdf_autofiller/cli.py            modules/mapper/sdk/pdf_autofiller_mapper/
cp sdks/python/pdf_autofiller/resources/__init__.py  modules/mapper/sdk/pdf_autofiller_mapper/resources/
cp sdks/python/pdf_autofiller/resources/mapper.py    modules/mapper/sdk/pdf_autofiller_mapper/resources/

# Copy tests
cp sdks/python/tests/__init__.py    modules/mapper/sdk/tests/
cp sdks/python/tests/conftest.py    modules/mapper/sdk/tests/
cp sdks/python/tests/test_*.py      modules/mapper/sdk/tests/

# Copy examples
cp sdks/python/examples/*.py        modules/mapper/sdk/examples/
cp sdks/python/examples/README.md   modules/mapper/sdk/examples/

# Copy config
cp modules/mapper/config.ini.example  modules/mapper/sdk/config.ini.example
```

### Step 3 — Rename the Python package inside the source files

In every file under `modules/mapper/sdk/pdf_autofiller_mapper/`, update internal imports:

```python
# Before
from pdf_autofiller.result import SDKResult
from pdf_autofiller.exceptions import ConfigurationError
from .resources.mapper import MapperResource

# After (only top-level package name changes — relative imports stay as-is)
from pdf_autofiller_mapper.result import SDKResult
from pdf_autofiller_mapper.exceptions import ConfigurationError
```

Also update `__init__.py` so the public API is:
```python
from pdf_autofiller_mapper.mapper import PDFMapper
from pdf_autofiller_mapper.client import PDFMapperClient
```

Update the CLI entry point name in `pyproject.toml`:
```toml
[project.scripts]
pdf-autofiller-mapper = "pdf_autofiller_mapper.cli:main"
```

### Step 4 — Write `modules/mapper/sdk/pyproject.toml`

Copy `sdks/python/pyproject.toml` and change:

```toml
[project]
name = "pdf-autofiller-mapper"          # was "pdf-autofiller"
version = "1.0.0"

[project.scripts]
pdf-autofiller-mapper = "pdf_autofiller_mapper.cli:main"   # was pdf-autofiller

[tool.setuptools.packages.find]
where = ["."]
include = ["pdf_autofiller_mapper*"]    # was pdf_autofiller*

[tool.pytest.ini_options]
testpaths = ["tests"]
```

All extras (`embedded`, `aws`, `azure`, `gcp`, `dev`) carry over unchanged — same dependency lists.

### Step 5 — Update tests to use new import

In `modules/mapper/sdk/tests/`:

```python
# Before
from pdf_autofiller import PDFMapper
from pdf_autofiller.result import SDKResult
from pdf_autofiller.exceptions import ConfigurationError

# After
from pdf_autofiller_mapper import PDFMapper
from pdf_autofiller_mapper.result import SDKResult
from pdf_autofiller_mapper.exceptions import ConfigurationError
```

### Step 6 — Verify SDK tests pass from new location

```bash
cd modules/mapper/sdk
pip install -e ".[dev]"
pytest tests/ -v
# All 101 tests should pass
```

### Step 7 — Update root scripts

`Makefile`:
```makefile
# Before
install-sdk:
    cd sdks/python && pip install -e .

# After
install-sdk:
    cd modules/mapper/sdk && pip install -e .
```

`setup.sh` / `setup.ps1` — update the SDK install block:
```bash
# Before
cd ../../sdks/python && pip install -e . -q

# After
cd ../../modules/mapper/sdk && pip install -e . -q
```

### Step 8 — Delete old SDK location

Only do this after Step 6 confirms tests pass:

```bash
rm -rf sdks/python/
```

`sdks/` then contains only:
```
sdks/
  openapi-mapper.yaml
  openapi-chatbot.yaml
  openapi-rag.yaml
  openapi-orchestrator.yaml
  typescript/
  generate.sh
  README.md
  QUICKSTART.md
```

### Step 9 — Verify end-to-end from scratch

```bash
# Fresh install from new location
pip install -e "modules/mapper/sdk[dev]"

# Test
cd modules/mapper/sdk && pytest tests/ -v

# Module-level tests still pass
cd modules/mapper && venv/bin/python -m pytest tests/ --override-ini="addopts=" -q
```

---

## Future modules (chatbot, rag, orchestrator)

When a new module is ready for an SDK, the pattern is always the same:

```
modules/<name>/
  src/                          ← server logic (no change)
  tests/                        ← module tests (no change)
  Dockerfile                    ← no change
  sdk/
    pdf_autofiller_<name>/
      __init__.py
      client.py                 ← HTTP client only (no embedded mode for chatbot/rag)
      exceptions.py
      result.py                 ← optional, if needed
    tests/
    pyproject.toml              ← name = "pdf-autofiller-<name>"
    README.md
```

PyPI packages produced:
- `pdf-autofiller-mapper`   → `pip install pdf-autofiller-mapper`
- `pdf-autofiller-chatbot`  → `pip install pdf-autofiller-chatbot`
- `pdf-autofiller-rag`      → `pip install pdf-autofiller-rag`

Users who want everything:
```bash
pip install pdf-autofiller-mapper pdf-autofiller-chatbot pdf-autofiller-rag
```

Or a thin meta-package at root level (optional, no code, just deps):
```
packages/
  pdf-autofiller-all/
    pyproject.toml
      dependencies = [
        "pdf-autofiller-mapper",
        "pdf-autofiller-chatbot",
        "pdf-autofiller-rag",
      ]
```
```bash
pip install pdf-autofiller-all   ← installs everything
```

---

## What is shared vs what is per-module

| Item | Shared (root) | Per-module |
|------|--------------|------------|
| Sample PDFs and JSON data | `data/samples/` | — |
| Module-specific test data | — | `data/modules/<name>/` |
| OpenAPI spec | `sdks/openapi-<name>.yaml` | — |
| TypeScript SDK | `sdks/typescript/` | — |
| Python SDK source | — | `modules/<name>/sdk/` |
| Python PyPI package | — | one per module |
| `config.ini` | — | `modules/<name>/config.ini` |
| `Dockerfile` | — | `modules/<name>/Dockerfile` |
| `setup.sh` / `Makefile` | root (orchestrates all) | — |
| Module business logic | — | `modules/<name>/src/` |
| Module tests | — | `modules/<name>/tests/` |

---

## Risk and rollback

- **Risk:** Any existing code that does `from pdf_autofiller import ...` will break after Step 8.
- **Mitigation:** Keep `sdks/python/` in place until Step 6 is verified. Only delete in Step 8.
- **Rollback:** If anything breaks before Step 8, nothing is lost — old code still at `sdks/python/`.
- **No changes to `modules/mapper/src/`** at any point — the server logic is completely untouched.
- **No changes to `modules/mapper/tests/`** — module tests are untouched.

---

## Summary of files touched

```
Created:
  modules/mapper/sdk/                    ← entire new directory

Modified:
  modules/mapper/sdk/pdf_autofiller_mapper/*.py   ← rename imports
  modules/mapper/sdk/tests/test_*.py             ← rename imports
  modules/mapper/sdk/pyproject.toml              ← new package name
  Makefile                                       ← update install-sdk path
  setup.sh                                       ← update SDK path
  setup.ps1                                      ← update SDK path

Deleted (only after tests pass):
  sdks/python/                           ← entire directory removed
```
