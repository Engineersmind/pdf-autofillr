# Branch Strategy & Maintenance Guide

**Last Updated:** 2026-04-22  
**Owner:** Raghava Mahanthi

---

## Branch Roles

| Branch | Purpose | Audience | Direct Commits |
|--------|---------|----------|---------------|
| `main` | Stable open-source release — all code, no secrets | Public / Contributors | No — PR only |
| `dev` | Active development — full stack, work in progress | Team | No — PR only |
| `prod` | Production deployment snapshot — promoted from `dev` | Deployment / Ops | No — PR only |
| `feature/pdfauto-XXX` | Individual feature work | Developer | Yes |

> The difference between branches is **stability state and secrets**, not which code is visible.
> All source code (modules, SDKs, benchmarks, infra templates) is open for contribution.
> Only actual secret values are excluded from all branches.

---

## Merge Flow

```
feature/pdfauto-XXX
        │
        ▼  PR → reviewed by team
       dev   ──────────── active development, all modules, work in progress
        │
        ▼  PR → all tests pass, stable
       main  ──────────── stable release, open-source, contributor-facing
        │
        ▼  tag vX.Y.Z pushed → triggers deploy pipeline
       prod  ──────────── production deployment, protected
```

**Rules:**
- Features always branch from `dev`, never from `main` or `prod`
- Every PR to `main` requires passing tests + no secrets in diff
- Every PR to `prod` requires full test suite + `terraform plan` review
- `prod` is never directly committed to — only promoted from `main` via tag

---

## Full Folder Structure (same across all branches)

```
pdf-autofillr/
├── .github/
│   └── workflows/
│       ├── mapper-tests.yml         ← runs on dev + prod PRs
│       ├── sdk-tests.yml            ← runs on all branches
│       └── publish-pypi.yml         ← triggers on version tags (see PyPI section)
│
├── benchmarks/
│   ├── datasets/
│   │   ├── financial/
│   │   ├── government/
│   │   ├── hr/
│   │   ├── insurance/
│   │   ├── legal/
│   │   └── medical/               ← each has: pdfs/, ground_truth/, schema_keys/
│   ├── metrics/
│   ├── models/
│   └── tasks/
│
├── deployment/
│   └── docker/
│       └── mapper/
│           ├── Dockerfile
│           ├── docker-compose.yml
│           └── .env.example
│
├── docs/
├── examples/
│
├── modules/
│   ├── chatbot/
│   ├── doc_upload/
│   ├── mapper/
│   │   ├── adapter_src/
│   │   ├── entrypoints/
│   │   ├── src/pdf_autofillr_mapper/
│   │   ├── deploy/terraform/
│   │   │   ├── aws/               ← templates committed, tfvars never committed
│   │   │   ├── azure/
│   │   │   └── gcp/
│   │   ├── tests/
│   │   └── Dockerfile
│   ├── pdf_autofillr/             ← orchestrator
│   └── rag/
│
├── packages/
│   ├── core/                      ← PyPI: pdf-autofiller-core
│   └── plugins/                   ← PyPI: pdf-autofiller-plugins
│
├── scripts/
│
├── sdks/
│   ├── python/                    ← PyPI: pdf-autofiller
│   ├── typescript/                ← npm: pdf-autofiller
│   └── openapi/
│       ├── openapi-mapper.yaml
│       ├── openapi-rag.yaml
│       ├── openapi-chatbot.yaml
│       └── openapi-orchestrator.yaml
│
├── tests/
├── .gitignore
├── LICENSE
├── Makefile
├── README.md
├── BRANCHING.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
└── GETTING_STARTED.md
```

---

## What Is NEVER Committed (any branch)

These are gitignored on all branches — they contain real secrets or are personal working files:

```gitignore
# Real secret values — use .example counterparts instead
terraform.tfvars
*.tfvars
!*.tfvars.example
.env
!.env.example
*.env.*
!*.env.example
*.postman_environment.json

# Internal personal files
CLAUDE.md
z_useful_cmds.sh
prod_file_dir_structure.txt
REFACTORING_SUMMARY.md
TERRAFORM_COMPLETE_IaC_PLAN.md

# Build artifacts
venv/
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.terraform/
*.tfstate
*.tfstate.backup
dist/
*.egg-info/
.DS_Store
node_modules/
```

---

## PyPI Packages

Three independently versioned packages are published to PyPI from this repo.

| Package | PyPI Name | Install | Source | Version |
|---------|-----------|---------|--------|---------|
| Python SDK | `pdf-autofiller` | `pip install pdf-autofiller` | `sdks/python/` | 1.0.0 |
| Core library | `pdf-autofiller-core` | `pip install pdf-autofiller-core` | `packages/core/` | 1.0.0 |
| Plugin framework | `pdf-autofiller-plugins` | `pip install pdf-autofiller-plugins` | `packages/plugins/` | 0.1.0 |

### Versioning — Tag-Based Publishing

Each package has its own version tag. CI detects which tag was pushed and publishes only that package:

```
sdk/v1.2.0       → publishes pdf-autofiller to PyPI
core/v1.0.5      → publishes pdf-autofiller-core to PyPI
plugins/v1.1.0   → publishes pdf-autofiller-plugins to PyPI
```

**Never publish to PyPI manually** — only via CI triggered by a version tag on `main`.

### Standard Package Structure (same for all three)

Every PyPI package in this repo follows this exact structure:

```
<package-dir>/
├── pyproject.toml           ← single source of truth for build config
├── <package_name>/
│   ├── __init__.py          ← must define __version__ = "X.Y.Z"
│   └── ...source files...
├── tests/
│   ├── __init__.py
│   └── test_*.py
├── examples/
│   └── *.py
├── CHANGELOG.md             ← version history, updated on every release
└── README.md
```

**No `setup.py`** — `pyproject.toml` is the only build config needed (PEP 517/518).  
**No `requirements.txt`** — dependencies declared in `pyproject.toml` under `[project.dependencies]`.

### Version Sync Rule

Version must match in exactly two places per package:

```
pyproject.toml          → version = "1.0.0"
<package>/__init__.py   → __version__ = "1.0.0"
```

These must always be in sync before tagging a release.

### CHANGELOG Format

Each `CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com) format:

```markdown
# Changelog

## [1.1.0] - 2026-05-01
### Added
- New feature X

## [1.0.0] - 2026-04-22
### Added
- Initial release
```

---

## Terraform Scripts

Terraform templates are committed and open — contributors can deploy their own instances.
Only `terraform.tfvars` (actual values) is never committed.

```
modules/mapper/deploy/terraform/
├── aws/
│   ├── main.tf
│   ├── iam.tf
│   ├── lambda.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── providers.tf
│   └── terraform.tfvars.example    ← committed (template, no real values)
├── azure/
│   └── main.tf
└── gcp/
    └── main.tf
```

For production deployments, `terraform.tfvars` values are injected via GitHub Actions secrets or AWS Secrets Manager — never stored in git.

---

## SDK Placement

Standardized to `sdks/` at root. Not inside `modules/`.

```
sdks/
├── python/             ← pip install pdf-autofiller
├── typescript/         ← npm install pdf-autofiller
└── openapi/            ← OpenAPI specs for all services
```

> `modules/mapper/sdk/` on `main` is legacy — contents merged into `sdks/python/` and old path deleted.

---

## CI/CD Workflows

| Workflow | Trigger | Runs On | Purpose |
|----------|---------|---------|---------|
| `mapper-tests.yml` | PR to `dev` or `prod` | `dev`, `prod` | Mapper unit + integration tests |
| `sdk-tests.yml` | PR to any branch | All | SDK tests across Python + TS |
| `publish-pypi.yml` | Tag `sdk/v*`, `core/v*`, `plugins/v*` on `main` | `main` | Publish to PyPI / npm |

### publish-pypi.yml Logic

```
tag sdk/v*     → build + publish sdks/python/     to PyPI
tag core/v*    → build + publish packages/core/    to PyPI
tag plugins/v* → build + publish packages/plugins/ to PyPI
```

Requires `PYPI_TOKEN` stored as a GitHub Actions secret.

---

## What Makes Each Branch Different

| | `main` | `dev` | `prod` |
|--|--------|-------|--------|
| Code content | Stable, reviewed | Work in progress | Same as last `main` tag |
| Accepts PRs from | `dev` | `feature/*` | `main` (tag-based) |
| Deploys to | Nothing | Nothing | AWS Lambda via Terraform |
| PyPI publishes from | Yes (on tag) | No | No |
| Direct commits | Never | Never | Never |
| Who uses it | Contributors, public | Developers | Ops / CI pipeline |

---

## To-Do: Branch Cleanup Checklist

### Immediate — security
- [ ] Delete `pdf-autofillr-mapper.env.dev.postman_environment.json` — has real credentials
- [ ] Delete `pdf-autofillr-mapper.env.prod.postman_environment.json` — has real credentials
- [ ] Add `*.postman_environment.json` to `.gitignore`
- [ ] Confirm `terraform.tfvars` is gitignored: `git ls-files | grep tfvars`
- [ ] Scan all committed files for secrets: `git grep -i "password\|api_key\|secret" -- "*.json" "*.yaml"`

### `dev` branch — from experiment-001
- [ ] Rename branch: `git branch -m experiment-001 dev`
- [ ] Update `.gitignore` with all rules listed in this file
- [ ] Bring full `benchmarks/` from `main`: `git checkout main -- benchmarks/`
- [ ] Bring `.github/workflows/` from `main`: `git checkout main -- .github/`
- [ ] Remove untracked personal files: `z_useful_cmds.sh`, `prod_file_dir_structure.txt`, `REFACTORING_SUMMARY.md`, `TERRAFORM_COMPLETE_IaC_PLAN.md`
- [ ] Add `CLAUDE.md` to `.gitignore`
- [ ] Consolidate SDK: confirm `sdks/python/` is complete, delete `modules/mapper/sdk/` if redundant

### `main` branch — align structure with dev
- [ ] Bring all 5 `modules/` from `dev` into `main`
- [ ] Bring `packages/core` and `packages/plugins` from `dev` into `main`
- [ ] Bring `modules/mapper/deploy/terraform/` (templates only, no tfvars) from `dev` into `main`
- [ ] Move `modules/mapper/sdk/` contents into `sdks/python/`, delete old path
- [ ] Verify no secrets in any committed file

### PyPI packages — standardize structure
- [ ] `sdks/python/`: `pyproject.toml` created ✅ — add `tests/`, `examples/`, `CHANGELOG.md`
- [ ] `packages/core/`: remove redundant `setup.py` and `requirements.txt`, add `examples/`, `CHANGELOG.md`
- [ ] `packages/plugins/`: remove redundant `setup.py` and `requirements.txt`, add `CHANGELOG.md`
- [ ] All packages: confirm `__version__` in `__init__.py` matches `pyproject.toml`
- [ ] Set up `PYPI_TOKEN` as GitHub Actions secret
- [ ] Write `publish-pypi.yml` workflow with tag-based routing
- [ ] Test publish to TestPyPI before first real release

### `prod` branch — create when ready
- [ ] Create from stable `main`: `git checkout -b prod main`
- [ ] Set branch protection on GitHub: require PR + 1 approval, no direct commits, require status checks
- [ ] Add `terraform.tfvars` values as GitHub Actions secrets
- [ ] Tag initial release: `git tag v1.0.0 && git push origin v1.0.0`
