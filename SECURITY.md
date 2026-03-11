# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**We take security seriously.** If you discover a security vulnerability, please follow responsible disclosure:

### 🔒 Private Reporting (Recommended)

**Use GitHub Security Advisories** for responsible disclosure:

1. Go to: https://github.com/Engineersmind/pdf-autofillr/security/advisories/new
2. Click **"Report a vulnerability"**
3. Fill in the details (severity, description, proof of concept)
4. Submit privately - we'll review within 48 hours

**Why use this?**
- ✅ Private until fixed
- ✅ Automated CVE assignment
- ✅ Coordinated disclosure timeline
- ✅ Credit in advisory when published

### 📧 Email Reporting (Alternative)

If you prefer email or can't use GitHub:
- **Email:** Support@pdffillr.ai
- **Subject:** `[SECURITY] Vulnerability Report - <brief description>`
- **Include:**
  - Description of the vulnerability
  - Steps to reproduce
  - Potential impact
  - Suggested fix (if any)

### ⏱️ Response Timeline

We aim to:
- **Acknowledge:** Within 48 hours
- **Initial assessment:** Within 5 business days
- **Fix timeline:** Depends on severity (see below)
- **Public disclosure:** After fix is released + 30 days (coordinated with you)

### 🎯 Severity & Response Time

| Severity | Impact | Response Target |
|----------|--------|----------------|
| **Critical** | Remote code execution, data breach | 24-72 hours |
| **High** | Authentication bypass, privilege escalation | 5-7 days |
| **Medium** | Information disclosure, DoS | 14-30 days |
| **Low** | Minor issues, edge cases | 30-60 days |

## Security Scope

### ✅ In Scope

We welcome reports about:
- **Authentication/Authorization issues**
- **Data leakage** (sensitive info in logs, responses, etc.)
- **Injection vulnerabilities** (SQL, Command, LLM prompt injection)
- **Path traversal** (file system access outside intended directories)
- **Insecure dependencies** (with proof of exploitability)
- **API security** (rate limiting, input validation, etc.)
- **Cryptographic weaknesses**
- **Docker/deployment security issues**

### ❌ Out of Scope

Please don't report:
- **Social engineering** (phishing, etc.)
- **Denial of Service** attacks requiring significant resources
- **Issues in dependencies** without proof of exploitability in our context
- **Theoretical issues** without proof of concept
- **Best practice violations** without security impact
- **Issues in discontinued/unsupported versions**

## Bug Bounty Program

**We currently do NOT have a paid bug bounty program.** This is an open-source project maintained by volunteers.

However, we offer:
- ✅ **Public recognition** in CHANGELOG and security advisory (if you want)
- ✅ **Contributor credit** in repository
- ✅ **Fast response** and transparent communication
- ✅ **Collaboration** on fixes if you're interested

## Disclosure Policy

We follow **coordinated disclosure**:

1. **Report received** → We acknowledge and assess
2. **Fix developed** → We work on patch (may invite you to collaborate)
3. **Fix deployed** → We release patched version
4. **30-day grace period** → Users have time to update
5. **Public disclosure** → We publish security advisory with credit to reporter

**Exception:** If the vulnerability is actively being exploited in the wild, we may fast-track public disclosure.

## Security Best Practices for Users

### For Production Deployments

1. **API Keys:** Never commit API keys to git
   ```bash
   # Use environment variables
   export OPENAI_API_KEY=your-key-here
   export ANTHROPIC_API_KEY=your-key-here
   ```

2. **Input Validation:** Sanitize user inputs before processing
   ```python
   # Don't trust user-provided file paths
   # Always validate and sanitize
   ```

3. **Network Security:** 
   - Use HTTPS for all API endpoints
   - Configure firewalls to restrict access
   - Use VPCs for cloud deployments

4. **Docker Security:**
   ```bash
   # Don't run as root
   # Use read-only file systems where possible
   # Scan images for vulnerabilities
   docker scan pdf-autofillr-mapper:latest
   ```

5. **Dependency Updates:**
   ```bash
   # Regularly update dependencies
   pip install --upgrade -r requirements.txt
   
   # Check for vulnerabilities
   pip-audit
   ```

### For Local Development

1. **Virtual environments:** Always use venv/conda to isolate dependencies
2. **Secrets management:** Use `.env` files (never commit them!)
3. **Code scanning:** Use tools like `bandit` for Python security checks
   ```bash
   pip install bandit
   bandit -r modules/mapper/src/
   ```

## Security Advisories

All published security advisories are available at:
https://github.com/Engineersmind/pdf-autofillr/security/advisories

## Questions?

For general security questions (not vulnerability reports):
- **Discussions:** https://github.com/Engineersmind/pdf-autofillr/discussions
- **Email:** Support@pdffillr.ai

---

**Thank you for helping keep PDF Autofillr secure!** 🔒