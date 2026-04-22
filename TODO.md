# Project To-Do List

**Last Updated:** 2026-04-22  
**Branch strategy reference:** [BRANCHING.md](BRANCHING.md)

---

## Phase 0 — Immediate (Security) ✅

- [x] Moved Postman credential files to `archives/` (gitignored, never committed)
- [x] Added `archives/`, `*.postman_environment.json`, `*.postman_collection.json` to `.gitignore`
- [x] Added internal files to `.gitignore`: `CLAUDE.md`, `z_useful_cmds.sh`, `prod_file_dir_structure.txt`, `REFACTORING_SUMMARY.md`, `TERRAFORM_COMPLETE_IaC_PLAN.md`
- [x] Confirmed `terraform.tfvars` is not tracked (only `.example` is)
- [x] Scan for any other accidental secrets: `git grep -i "password\|api_key\|secret" -- "*.json" "*.yaml" "*.env"` — only env var name references found (no values)

---

## Phase 1 — Branch Setup

### Create `dev` from `experiment-001`

- [x] Renamed `experiment-001` → `dev` locally
- [x] Pushed `dev` to remote
- [x] Deleted `experiment-001` remote branch
- [x] Fixed upstream tracking: `dev` → `origin/dev`
- [ ] On GitHub: set `dev` as default branch for the team
- [ ] On GitHub: set branch protection on `main` — require PR + 1 approval + passing tests

### `prod` branch (create when `dev` is stable)

- [ ] Create `prod` from a stable `main` commit: `git checkout -b prod main`
- [ ] Set branch protection: require PR + 1 approval + all status checks pass + no direct commits
- [ ] Store `terraform.tfvars` values as GitHub Actions secrets (never in repo)
- [ ] Tag first release: `git tag v1.0.0 && git push origin v1.0.0`

---

## Phase 2 — `dev` Branch Tasks

Things missing on `dev` (experiment-001) that need to be added.

### Bring from `main`

- [x] Brought full `benchmarks/` structure (6 domains: financial, government, hr, insurance, legal, medical)
- [x] Brought `.github/workflows/` — updated triggers for `dev`/`prod`, fixed paths, renamed `publish-sdk.yml` → `publish-pypi.yml` with tag-based routing for all 3 packages

### Clean up personal/internal files

- [x] Added to `.gitignore`: `CLAUDE.md`, `z_useful_cmds.sh`, `prod_file_dir_structure.txt`, `REFACTORING_SUMMARY.md`, `TERRAFORM_COMPLETE_IaC_PLAN.md`

### Structural

- [x] `sdks/python/pyproject.toml` created — authoritative build config
- [x] `BRANCHING.md` and `TODO.md` committed to `dev`
- [x] Restored `modules/rag-pdf-fillr/` name (reverted rename, git history preserved)
- [x] Moved `modules/pdf_autofillr/` → `packages/pdf_autofillr/` (meta-package, not a module)
- [x] Removed `modules/mapper/sdk/` — superseded by `sdks/python/`
- [x] Archived `modules/rag-pdf-fillr/.env` → `archives/`
- [ ] Review `GETTING_STARTED.md`, `ARCHITECTURE.md`, `COMMANDS.md` — update to reflect 4 modules and new paths

---

## Phase 3 — `main` Branch Tasks

`main` is behind `dev` in structure. Needs to be brought up to match.

### Bring from `dev`

- [ ] Add `modules/doc_upload/` — new module, not on `main` at all
- [ ] Add `modules/pdf_autofillr/` — orchestrator module, not on `main`
- [ ] Rename `modules/rag-pdf-fillr/` → `modules/rag/` (matches `dev`)
- [ ] Update `modules/mapper/` to match `dev` structure:
  - Rename `adapters/` → `adapter_src/`
  - Update `src/` → `src/pdf_autofillr_mapper/` (properly namespaced)
  - Add `deploy/terraform/` (aws, azure, gcp templates — no tfvars)
  - Remove legacy `sdk/` folder (contents already in `sdks/python/`)
  - Remove `api_server.py` (replaced by `entrypoints/`)
  - Remove `config.ini`, `config.ini.example` (replaced by env-based config)
- [ ] Bring `packages/core/` from `dev`
- [ ] Bring `packages/plugins/` from `dev`
- [ ] Bring `sdks/python/` from `dev` (currently `main` has no Python SDK in sdks/)
- [ ] Update `sdks/` — add `openapi/orchestrator.yaml` (exists on `dev`, not on `main`)
- [ ] Bring `deployment/docker/` from `dev`
- [ ] Bring `BRANCHING.md` and `TODO.md` to `main`

### Verify after sync

- [ ] No secrets in any committed file on `main`
- [ ] All `.env.example` templates present and accurate
- [ ] All `terraform.tfvars.example` templates present
- [x] `modules/mapper/sdk/` deleted (done on `dev`, apply same on `main`)

---

## Phase 4 — PyPI Packages

### Standardize structure across all 3 packages

Every package must follow this layout:
```
<package>/
├── pyproject.toml         ← only build config (no setup.py)
├── <pkg_name>/
│   └── __init__.py        ← __version__ matches pyproject.toml
├── tests/
├── examples/
├── CHANGELOG.md
└── README.md
```

#### `sdks/python/` — `pdf-autofiller` (v1.0.0) ✅
- [x] `pyproject.toml` created
- [x] Removed redundant `setup.py` and `requirements.txt`
- [x] `tests/` with basic coverage
- [x] `CHANGELOG.md` added
- [x] `__version__` matches `pyproject.toml`

#### `packages/core/` — `pdf-autofiller-core` (v1.0.0) ✅
- [x] `pyproject.toml` exists
- [x] Removed redundant `setup.py`, `requirements.txt`, `SETUP_COMPLETE.md`
- [x] `examples/` added (implement_storage.py, implement_handler.py)
- [x] `tests/` added
- [x] `CHANGELOG.md` added

#### `packages/plugins/` — `pdf-autofiller-plugins` (v0.1.0) ✅
- [x] `pyproject.toml` exists
- [x] Removed redundant `setup.py`, `requirements.txt`, `SETUP_COMPLETE.md`
- [x] `tests/` added
- [x] `CHANGELOG.md` added

### CI/CD for publishing

- [x] `publish-pypi.yml` written with tag-based routing (sdk-v*, core-v*, plugins-v*)
- [ ] Set up PyPI Trusted Publishing (OIDC) — no API token needed
  - Go to: https://pypi.org/manage/account/publishing/
  - Owner: Engineersmind | Repo: pdf-autofillr | Workflow: publish-pypi.yml | Env: pypi
- [ ] Create `pypi` environment in GitHub repo settings → Environments → New environment → name: `pypi`
- [ ] Test publish to TestPyPI before first real release:
  ```bash
  cd sdks/python && pip install build twine
  python -m build && twine upload --repository testpypi dist/*
  ```

---

## Phase 5 — Refactoring

### Mapper module
- [ ] **Token limiting** — add per-operation and per-session token caps for Phase 1 (semantic mapper) and header extraction, fetched from user profile via backend API (see discussion in conversation)
- [ ] **Notification key consistency** — verify all stage notifications use consistent key names matching `pipeline_completed` output (extract, map, embed, fill stages) ← partially done
- [x] **`notifier.py` status.value fix** — fixed and committed on dev
- [ ] **Requirements consolidation** — mapper has 5 requirements files; document when to use which or consolidate with extras in `pyproject.toml`
- [x] **Remove `api_server.py`** from mapper — done (synced from dev to main)
- [x] **Rename `adapters/` → `adapter_src/`** — done (synced from dev to main)

### Module structure consistency
- [ ] All modules should follow the same folder layout as `modules/mapper/`:
  - `entrypoints/` — Lambda + FastAPI handlers
  - `src/<module_name>/` — namespaced source code
  - `tests/`
  - `deploy/terraform/` (where applicable)
  - `pyproject.toml`
  - `.env.example`
- [x] `modules/chatbot/` — removed legacy api_server.py, API_SERVER.md, MANIFEST.in, SETUP_GUIDE.md
- [ ] `modules/rag-pdf-fillr/` — verify structure
- [ ] `modules/doc_upload/` — verify structure
- [ ] `modules/pdf_autofillr/` (in packages/) — verify orchestrator is wired up correctly

### RAG module
- [ ] Verify `ragpdf_data/` (test data + metrics that exists on `main`) is either migrated to `benchmarks/` or preserved on `dev`

### SDK + OpenAPI
- [ ] `sdks/typescript/` — currently only a `package.json` on `main` and a `README.md` on `dev` — needs actual implementation or a clear placeholder
- [ ] All 4 OpenAPI specs — verify they are up to date with current API surface (mapper, rag, chatbot, orchestrator)
- [ ] `sdks/generate.sh` — verify it still works with updated OpenAPI specs

### CI/CD
- [x] Updated `mapper-tests.yml` to use new `src/pdf_autofillr_mapper/` path
- [x] Updated `sdk-tests.yml` to point to `sdks/python/`
- [x] Added `dev`/`prod` trigger branches to all workflows
- [x] Added `module-tests.yml` — chatbot, doc_upload, rag-pdf-fillr jobs with Python matrix + coverage

---

## Phase 6 — New Features (Deferred — after setup complete)

- [ ] Token limiting per user (Phase 1 + header extraction)
- [ ] TypeScript SDK implementation
- [ ] Multi-cloud deployment docs (Azure, GCP)
- [ ] Benchmarks run against new mapper version

---

## Quick Reference — Key Commands

```bash
# Create dev from experiment-001
git checkout experiment-001
git branch -m experiment-001 dev
git push origin dev

# Bring benchmarks from main to dev
git checkout main -- benchmarks/

# Bring workflows from main to dev
git checkout main -- .github/

# Check for accidentally tracked secrets
git ls-files | grep -E "tfvars|\.env$|postman"

# Check nothing sensitive is staged
git diff --cached | grep -i "password\|api_key\|secret"

# Tag a PyPI release (run on main)
git tag sdk/v1.0.1
git push origin sdk/v1.0.1
```
