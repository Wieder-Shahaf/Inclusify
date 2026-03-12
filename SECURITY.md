# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of Inclusify seriously. If you discover a security vulnerability, please follow these steps:

### 1. Do Not Open a Public Issue

Please **do not** report security vulnerabilities through public GitHub issues.

### 2. Contact Us Privately

Email security concerns to: **security@inclusify.org** (or use GitHub Security Advisories)

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### 3. Response Timeline

- **24 hours**: Initial acknowledgment
- **72 hours**: Preliminary assessment
- **7 days**: Detailed response with fix timeline

### 4. Disclosure Policy

- We follow **coordinated disclosure**
- Security fixes will be released as soon as possible
- Public disclosure only after fix is deployed
- We will credit reporters (unless anonymity is requested)

## Security Measures

### Data Protection
- Private mode: No text storage when enabled
- Database encryption at rest
- TLS/SSL for all API communication
- Regular security audits

### Authentication & Authorization
- API key authentication for external services
- Role-based access control (RBAC) for admin features
- Session management with secure cookies

### Input Validation
- Pydantic validation on all API endpoints
- File upload size limits (10MB default)
- Content-type verification
- SQL injection prevention (parameterized queries)

### Infrastructure
- Azure security best practices
- Regular dependency updates
- Automated vulnerability scanning (Dependabot)
- Environment variable isolation

## Known Security Considerations

### Private Mode
When private mode is enabled, text is **never** stored in the database. However:
- Text is temporarily held in memory during processing
- Logs may contain excerpts (ensure proper log sanitization in production)

### File Uploads
- Only PDF and DOCX files are accepted
- File size limited to prevent DoS
- Files are scanned for malware (planned for Phase 7)

## Security Updates

Security patches will be released as:
- **Critical**: Immediate patch release
- **High**: Within 7 days
- **Medium**: Next minor version
- **Low**: Next major version

Subscribe to [GitHub Security Advisories](https://github.com/yourusername/inclusify/security/advisories) to receive notifications.

## Best Practices for Contributors

- Never commit secrets, API keys, or credentials
- Use `.env` files for sensitive configuration (gitignored)
- Run security linters before committing:
  - `npm audit` (frontend)
  - `pip-audit` (backend)
- Review dependencies for known vulnerabilities
- Follow OWASP Top 10 guidelines

## Security Checklist for Deployment

- [ ] Environment variables properly configured
- [ ] Database credentials rotated
- [ ] TLS/SSL certificates valid
- [ ] CORS origins restricted to production domains
- [ ] Rate limiting enabled
- [ ] Logging configured (without sensitive data)
- [ ] Backup strategy in place
- [ ] Incident response plan documented

---

Thank you for helping keep Inclusify secure!
