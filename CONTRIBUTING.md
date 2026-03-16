# Contributing

Thank you for your interest in contributing to PDF Autofillr.

---

## Getting started

1. Fork the repository and create a branch from `main`.
2. Set up the mapper module locally:

```bash
cd modules/mapper
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config.ini.example config.ini
```

3. Make your changes.
4. Run tests before submitting:

```bash
venv/bin/python -m pytest tests/ --override-ini="addopts=" -q
```

5. Open a pull request against `main`.

---

## What to contribute

- Bug fixes
- New LLM provider support (via `litellm`)
- New storage backends (AWS, Azure, GCP improvements)
- New entrypoints (Lambda, Azure Function, GCP)
- Documentation improvements
- Test coverage improvements

---

## Pull request checklist

- [ ] Tests pass (`169 passed`)
- [ ] New behaviour is covered by a test
- [ ] `config.ini.example` updated if new config keys are added
- [ ] PR description explains *why*, not just *what*

---

## Code style

- Python 3.10+
- No external linter enforced — just keep it consistent with the surrounding code.
- Keep functions small and focused.

---

## Reporting bugs

Open a [GitHub issue](https://github.com/Engineersmind/pdf-autofillr/issues) with:
- What you did
- What you expected
- What happened (include the full traceback)
- Your Python version and OS

---

## Questions

Open a [GitHub Discussion](https://github.com/Engineersmind/pdf-autofillr/discussions) for questions, ideas, or general feedback.
