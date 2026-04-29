# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

Only the latest version on the `main` branch is actively maintained for security updates.

## Reporting a Vulnerability

We take the security of RAGEve seriously. If you believe you have found a security vulnerability, please report it to us privately so we can investigate and address it before public disclosure.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please report vulnerabilities via email:

```
security@bazzi24.github.io
```

(Replace with your actual email or create a security@yourdomain.com alias)

### What to Include

Please include as much of the following information as possible:

- **Description** - Clear description of the vulnerability
- **Steps to reproduce** - Detailed steps, including any sample code or payloads
- **Impact** - What an attacker could achieve (data exposure, DoS, RCE, etc.)
- **Affected versions** - Which version(s) you tested
- **Environment** - OS, Python version, deployment setup if relevant
- **Recommendations** - (Optional) Suggested fixes

### Response Timeline

We aim to respond to security reports within **5 business days** with:

- Initial assessment and triage
- Expected timeline for a fix or mitigation
- Regular updates on progress

### Disclosure Policy

- We follow **responsible disclosure** - we ask that you keep vulnerability details confidential until a fix is released
- We will credit you in the security advisory (with your permission)
- We will publish a security advisory on GitHub once a fix is available
- We may request a CVE identifier for significant vulnerabilities

## Security Considerations for RAGEve

Since RAGEve is a **local-first** application designed to run on your own infrastructure, many security responsibilities fall on the deployer:

### For Deployers

1. **Network Security**
   - Use HTTPS/TLS in production (configure behind a reverse proxy like nginx)
   - Restrict API access to trusted networks when possible
   - Enable authentication (`API_KEY` environment variable) for production deployments

2. **Authentication & Authorization**
   - The current version has optional API key authentication
   - Multi-tenancy is supported but user management is basic
   - Ensure MySQL and Qdrant are not exposed to the public internet

3. **Data Protection**
   - RAGEve stores documents, embeddings, and conversation history locally
   - Encrypt sensitive data at rest (MySQL tablespace, Qdrant persistence, file uploads)
   - Regularly backup your data
   - Consider encryption for `DATA_ROOT` directory

4. **Dependency Security**
   - Keep dependencies updated: `uv sync --update`
   - Review dependencies in `pyproject.toml` regularly
   - We use Dependabot for automated security updates (Python dependencies)
   - Monitor Ollama and Qdrant for security advisories

5. **Input Validation**
   - File uploads are processed by multiple libraries (pdf2image, unstructured, etc.)
   - We validate file types and sizes, but be cautious with untrusted documents
   - Consider deploying in a sandboxed environment for highly sensitive data

6. **Resource Limits**
   - Configure appropriate rate limits (`RATE_LIMIT_PER_MINUTE`)
   - Monitor disk space for `DATA_ROOT` (uploads, embeddings, chunks)
   - Set memory limits for Ollama to prevent DoS via large documents

### Known Limitations

- **No built-in user authentication** in the current version (API key only)
- **Single-tenant by default** - multi-tenancy exists but requires manual setup
- **No audit logging** - consider enabling MySQL general log or audit plugin for compliance
- **File processing sandbox** - Document parsing libraries may have vulnerabilities; ensure they're updated

## Security Features

RAGEve includes several security-conscious design choices:

- **Local-first**: No cloud dependencies, no data leaves your infrastructure
- **Optional authentication**: Simple API key support for basic protection
- **Rate limiting**: Per-IP rate limiting when `API_KEY` is enabled
- **Request ID tracing**: All requests include `X-Request-ID` for audit trails
- **CORS configurability**: Restrict origins via `CORS_ORIGINS`
- **No hardcoded secrets**: All credentials come from environment variables
- **SQL injection protection**: Peewee ORM with parameterized queries
- **File upload validation**: Type checking and size limits

## Security Updates

Security fixes will be:

- Released as GitHub security advisories
- Tagged with security patch version numbers (e.g., `v1.2.3-security.1`)
- Announced in the repository's security advisory section
- Backported to the latest stable branch when applicable

## Third-Party Components

RAGEve relies on the following external components. You are responsible for securing them:

| Component | Purpose | Security Notes |
|-----------|---------|----------------|
| **Ollama** | LLM + embeddings | Run locally, configure access controls, keep updated |
| **Qdrant** | Vector database | Enable authentication, use TLS, restrict network access |
| **MySQL** | Metadata storage | Use strong passwords, restrict network, enable SSL if remote |
| **FastAPI** | Web framework | Run behind reverse proxy with proper CORS and HTTPS |
| **Python dependencies** | Various | Updated via Dependabot; monitor CVEs |

## Security Audit

We welcome security audits and responsible disclosure. If you're a security researcher:

- We do **not** operate a bug bounty program at this time
- We will acknowledge your contribution (if desired) in the security advisory
- We appreciate well-written reports with proof-of-concept code

## Questions?

For non-security issues, please use GitHub Issues. For security matters, email is the preferred channel to ensure confidentiality.

---

*Last updated: 2026-04-29*
