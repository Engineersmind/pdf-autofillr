## Ticket
<!-- Link to the ticket: https://github.com/orgs/Engineersmind/projects/XX/PDFAUTO-NNN -->
PDFAUTO-

## What Changed
<!-- Concise description of what this PR does -->

## Why
<!-- Motivation — what problem does this solve or what requirement does it fulfil? -->

## How to Test
1. 
2. 

## Type of Change
- [ ] `feat` — new feature
- [ ] `fix` — bug fix
- [ ] `refactor` — code change with no behaviour change
- [ ] `test` — adding or updating tests
- [ ] `docs` — documentation only
- [ ] `chore` / `ci` — tooling, config, CI/CD

## Module(s) Affected
- [ ] mapper
- [ ] rag-pdf-fillr
- [ ] doc-upload
- [ ] sdk
- [ ] terraform / infra
- [ ] other: ___

## Screenshots / Logs
<!-- If the change affects Lambda responses or S3 output, paste a relevant log excerpt -->

## Checklist
- [ ] Tests added or updated
- [ ] Existing tests still pass (`pytest tests/`)
- [ ] No new hardcoded bucket names, paths, or secrets (use PathResolver / env vars)
- [ ] S3 saves use correct bucket (RAG predictions → `PathResolver.remote_final_predictions`)
- [ ] Terraform changes reviewed (if any)
- [ ] `CLAUDE.md` updated if architecture/patterns changed
